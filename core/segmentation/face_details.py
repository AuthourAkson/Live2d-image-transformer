"""
面部细节检测模块 (Face Detail Detection)
========================================
基于 MediaPipe Face Landmarker (478 点) 检测面部细节，
提取眼睛、眉毛、嘴巴的精确轮廓和状态。

依赖: mediapipe (已含 Face Landmarker task 模型)

API:
    detect_face_details(image_path) -> FaceDetails
        → 返回眼睛开合度、嘴型、眉毛位置等参数
"""

import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# MediaPipe Face Landmarker 模型
FACE_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "face_landmarker_v2_with_blendshapes.task"


@dataclass
class EyeDetail:
    """单眼细节"""
    openness: float = 1.0          # 开合度 (0=闭, 1=全开)
    center: tuple = (0, 0)         # 眼球中心坐标 (x, y)
    inner_corner: tuple = (0, 0)   # 内眼角
    outer_corner: tuple = (0, 0)   # 外眼角
    upper_lid: list = field(default_factory=list)   # 上眼睑点
    lower_lid: list = field(default_factory=list)   # 下眼睑点


@dataclass
class MouthDetail:
    """嘴部细节"""
    openness: float = 0.0          # 纵向开合 (0=闭, 1=全开)
    width: float = 0.0             # 横向开合
    center: tuple = (0, 0)         # 中心坐标
    upper_lip: list = field(default_factory=list)    # 上唇轮廓
    lower_lip: list = field(default_factory=list)    # 下唇轮廓


@dataclass
class EyebrowDetail:
    """眉毛细节"""
    position: float = 0.5          # 相对位置 (0=下, 1=上)
    center: tuple = (0, 0)
    points: list = field(default_factory=list)


@dataclass
class FaceDetails:
    """面部细节综合结果"""
    left_eye: EyeDetail = field(default_factory=EyeDetail)
    right_eye: EyeDetail = field(default_factory=EyeDetail)
    mouth: MouthDetail = field(default_factory=MouthDetail)
    left_eyebrow: EyebrowDetail = field(default_factory=EyebrowDetail)
    right_eyebrow: EyebrowDetail = field(default_factory=EyebrowDetail)
    head_pose: tuple = (0.0, 0.0, 0.0)  # (yaw, pitch, roll)
    nose_tip: tuple = (0, 0)

    def to_dict(self) -> dict:
        return {
            "left_eye_openness": self.left_eye.openness,
            "right_eye_openness": self.right_eye.openness,
            "mouth_openness": self.mouth.openness,
            "mouth_width": self.mouth.width,
            "left_eyebrow_position": self.left_eyebrow.position,
            "right_eyebrow_position": self.right_eyebrow.position,
            "head_pose_yaw": self.head_pose[0],
            "head_pose_pitch": self.head_pose[1],
            "head_pose_roll": self.head_pose[2],
        }


# MediaPipe Face Mesh 关键索引 (精简版)
# 参考: https://github.com/google/mediapipe/blob/master/docs/solutions/face_mesh.md
FACE_INDICES = {
    # 左眼
    "left_eye_upper": [159, 158, 157, 173, 160, 161],
    "left_eye_lower": [145, 144, 163, 7, 160, 161],
    "left_eye_inner": 161,
    "left_eye_outer": 163,
    "left_iris": 468,  # iris 中心 (仅 face_landmarker_v2)
    # 右眼
    "right_eye_upper": [386, 385, 384, 398, 387, 388],
    "right_eye_lower": [374, 373, 390, 249, 387, 388],
    "right_eye_inner": 388,
    "right_eye_outer": 390,
    "right_iris": 473,
    # 嘴巴
    "mouth_upper": [61, 185, 40, 39, 37, 0, 267, 269, 270, 409],
    "mouth_lower": [146, 91, 181, 84, 17, 314, 405, 321, 375],
    "mouth_left": 61,
    "mouth_right": 291,
    "mouth_top": 13,
    "mouth_bottom": 14,
    # 眉毛
    "left_eyebrow": [70, 63, 105, 66, 107],
    "right_eyebrow": [300, 293, 334, 296, 336],
    # 鼻子
    "nose_tip": 4,
    "nose_bridge": 168,
}


def _detect_face_landmarks(image: np.ndarray):
    """使用 MediaPipe Face Landmarker 检测面部关键点。

    Returns:
        list[dict]: 478 个面部关键点 (含 x, y, z)
        None: 未检测到面部
    """
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import (
        FaceLandmarker, FaceLandmarkerOptions, RunningMode,
    )

    model_path = os.environ.get(
        "MEDIAPIPE_FACE_MODEL",
        str(FACE_MODEL_PATH),
    )

    if not os.path.exists(model_path):
        # 尝试自动下载
        logger.warning(f"面部模型未找到: {model_path}")
        logger.info("尝试使用预打包模型...")
        # mediapipe 新版本可能已内置模型
        model_path = None

    if model_path:
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=True,
        )
    else:
        # 使用默认模型
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=os.path.join(
                    os.path.dirname(mp.__file__), "modules", "face_landmarker",
                    "face_landmarker.task"
                )
            ),
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=True,
        )

    with FaceLandmarker.create_from_options(options) as landmarker:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        result = landmarker.detect(mp_image)

    if not result.face_landmarks:
        return None

    h, w = image.shape[:2]
    landmarks = []
    for lm in result.face_landmarks[0]:
        landmarks.append({
            "x": lm.x * w,
            "y": lm.y * h,
            "z": lm.z or 0,
        })

    # 解析 blendshapes
    blendshapes = {}
    if result.face_blendshapes:
        for bs in result.face_blendshapes[0]:
            blendshapes[bs.category_name] = bs.score

    return landmarks, blendshapes


class BlendShapeEstimator:
    """用 Face Mesh 关键点估算面部参数（无 blendshapes 时的 fallback）。"""

    @staticmethod
    def eye_openness(landmarks, eye_indices_upper, eye_indices_lower, eye_center_idx):
        """基于上下眼睑距离估算眼睛开合度。"""
        h, w = None, None  # landmarks are already in pixel coords

        upper_pts = np.array([
            (landmarks[i]["x"], landmarks[i]["y"])
            for i in eye_indices_upper
            if i < len(landmarks)
        ])
        lower_pts = np.array([
            (landmarks[i]["x"], landmarks[i]["y"])
            for i in eye_indices_lower
            if i < len(landmarks)
        ])

        if len(upper_pts) == 0 or len(lower_pts) == 0:
            return 1.0

        # 计算平均垂直距离
        center_x = np.mean(upper_pts[:, 0])
        upper_at_center = upper_pts[np.argmin(np.abs(upper_pts[:, 0] - center_x))]
        lower_at_center = lower_pts[np.argmin(np.abs(lower_pts[:, 0] - center_x))]

        dist = np.abs(upper_at_center[1] - lower_at_center[1])
        # 用眼宽来归一化
        eye_width = np.abs(upper_pts[:, 0].max() - upper_pts[:, 0].min())
        if eye_width < 1:
            return 1.0

        ratio = dist / (eye_width * 0.4)
        return min(1.0, max(0.0, ratio))

    @staticmethod
    def mouth_openness(landmarks):
        """基于嘴唇距离估算嘴巴开合度。"""
        top_idx = FACE_INDICES["mouth_top"]
        bottom_idx = FACE_INDICES["mouth_bottom"]
        left_idx = FACE_INDICES["mouth_left"]
        right_idx = FACE_INDICES["mouth_right"]

        indices = [top_idx, bottom_idx, left_idx, right_idx]
        for i in indices:
            if i >= len(landmarks):
                return 0.0

        top = landmarks[top_idx]
        bottom = landmarks[bottom_idx]
        left = landmarks[left_idx]
        right = landmarks[right_idx]

        mouth_height = abs(top["y"] - bottom["y"])
        mouth_width = abs(left["x"] - right["x"])

        if mouth_width < 1:
            return 0.0

        ratio = mouth_height / (mouth_width * 0.5)
        return min(1.0, max(0.0, ratio))


def detect_face_details(image_path) -> Optional[FaceDetails]:
    """
    检测面部细节。

    Args:
        image_path: 图片路径 (str/Path) 或 PIL Image

    Returns:
        FaceDetails: 面部细节，含眼睛/嘴巴/眉毛参数
        None: 未检测到面部

    注意: 需要下载 face_landmarker_v2_with_blendshapes.task
    """
    import mediapipe  # noqa: F401

    if isinstance(image_path, (str, Path)):
        pil_img = Image.open(image_path).convert("RGB")
    elif isinstance(image_path, Image.Image):
        pil_img = image_path.convert("RGB")
    else:
        raise TypeError(f"不支持的输入类型: {type(image_path)}")

    img_np = np.array(pil_img)

    result = _detect_face_landmarks(img_np)
    if result is None:
        logger.warning("未检测到面部")
        return None

    landmarks, blendshapes = result
    logger.info(f"检测到 {len(landmarks)} 个面部关键点")

    estimator = BlendShapeEstimator()

    # --- 左眼 ---
    left_eye = EyeDetail()
    if blendshapes and "eyeBlinkLeft" in blendshapes:
        left_eye.openness = 1.0 - blendshapes["eyeBlinkLeft"]
    else:
        left_eye.openness = estimator.eye_openness(
            landmarks,
            FACE_INDICES["left_eye_upper"],
            FACE_INDICES["left_eye_lower"],
            FACE_INDICES["left_iris"],
        )

    inner = landmarks[FACE_INDICES["left_eye_inner"]] if FACE_INDICES["left_eye_inner"] < len(landmarks) else {"x": 0, "y": 0}
    outer = landmarks[FACE_INDICES["left_eye_outer"]] if FACE_INDICES["left_eye_outer"] < len(landmarks) else {"x": 0, "y": 0}
    left_eye.inner_corner = (inner["x"], inner["y"])
    left_eye.outer_corner = (outer["x"], outer["y"])

    if FACE_INDICES["left_iris"] < len(landmarks):
        iris = landmarks[FACE_INDICES["left_iris"]]
        left_eye.center = (iris["x"], iris["y"])
    elif blendshapes and "eyeLookInLeft" in blendshapes:
        # 用 blendshape 估算视线
        left_eye.center = (inner["x"] + (outer["x"] - inner["x"]) * 0.5,
                           inner["y"] + (outer["y"] - inner["y"]) * 0.5)

    # --- 右眼 ---
    right_eye = EyeDetail()
    if blendshapes and "eyeBlinkRight" in blendshapes:
        right_eye.openness = 1.0 - blendshapes["eyeBlinkRight"]
    else:
        right_eye.openness = estimator.eye_openness(
            landmarks,
            FACE_INDICES["right_eye_upper"],
            FACE_INDICES["right_eye_lower"],
            FACE_INDICES["right_iris"],
        )

    inner_r = landmarks[FACE_INDICES["right_eye_inner"]] if FACE_INDICES["right_eye_inner"] < len(landmarks) else {"x": 0, "y": 0}
    outer_r = landmarks[FACE_INDICES["right_eye_outer"]] if FACE_INDICES["right_eye_outer"] < len(landmarks) else {"x": 0, "y": 0}
    right_eye.inner_corner = (inner_r["x"], inner_r["y"])
    right_eye.outer_corner = (outer_r["x"], outer_r["y"])

    if FACE_INDICES["right_iris"] < len(landmarks):
        iris = landmarks[FACE_INDICES["right_iris"]]
        right_eye.center = (iris["x"], iris["y"])

    # --- 嘴巴 ---
    mouth = MouthDetail()
    if blendshapes and "jawOpen" in blendshapes:
        mouth.openness = blendshapes["jawOpen"]
    else:
        mouth.openness = estimator.mouth_openness(landmarks)

    if (FACE_INDICES["mouth_left"] < len(landmarks) and
            FACE_INDICES["mouth_right"] < len(landmarks)):
        ml = landmarks[FACE_INDICES["mouth_left"]]
        mr = landmarks[FACE_INDICES["mouth_right"]]
        mouth.center = ((ml["x"] + mr["x"]) / 2, (ml["y"] + mr["y"]) / 2)
        mouth.width = abs(ml["x"] - mr["x"])

    # --- 眉毛 ---
    left_brow = EyebrowDetail()
    left_brow_pts = [landmarks[i] for i in FACE_INDICES["left_eyebrow"] if i < len(landmarks)]
    if left_brow_pts:
        left_brow.center = (np.mean([p["x"] for p in left_brow_pts]),
                            np.mean([p["y"] for p in left_brow_pts]))
        # 用相对眼睛的位置估算眉毛高度
        eye_center_y = (inner["y"] + outer["y"]) / 2
        brow_y = left_brow.center[1]
        # 正常眉毛在眼睛上方 ~0.3-0.5 眼宽
        eye_width = abs(outer["x"] - inner["x"])
        if eye_width > 0:
            dist = eye_center_y - brow_y
            left_brow.position = min(1.0, max(0.0, dist / (eye_width * 0.6)))

    right_brow = EyebrowDetail()
    right_brow_pts = [landmarks[i] for i in FACE_INDICES["right_eyebrow"] if i < len(landmarks)]
    if right_brow_pts:
        right_brow.center = (np.mean([p["x"] for p in right_brow_pts]),
                             np.mean([p["y"] for p in right_brow_pts]))
        eye_center_y_r = (inner_r["y"] + outer_r["y"]) / 2
        brow_y_r = right_brow.center[1]
        eye_width_r = abs(outer_r["x"] - inner_r["x"])
        if eye_width_r > 0:
            dist_r = eye_center_y_r - brow_y_r
            right_brow.position = min(1.0, max(0.0, dist_r / (eye_width_r * 0.6)))

    # --- 鼻子 ---
    nose_tip = (0, 0)
    if FACE_INDICES["nose_tip"] < len(landmarks):
        nt = landmarks[FACE_INDICES["nose_tip"]]
        nose_tip = (nt["x"], nt["y"])

    return FaceDetails(
        left_eye=left_eye,
        right_eye=right_eye,
        mouth=mouth,
        left_eyebrow=left_brow,
        right_eyebrow=right_brow,
        nose_tip=nose_tip,
    )


def check_dependencies() -> bool:
    """检查依赖是否就绪。"""
    try:
        import mediapipe  # noqa: F401
        return True
    except ImportError:
        return False
