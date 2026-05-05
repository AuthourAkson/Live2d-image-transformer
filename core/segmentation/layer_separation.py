"""
图层分离模块 (Layer Separation)
=================================
基于 MediaPipe 姿态检测 + 启发式分割，将人物图像分离为多个图层：
  - head (头部)
  - torso (躯干)
  - left_upper_arm / left_forearm / left_hand
  - right_upper_arm / right_forearm / right_hand
  - left_thigh / left_leg / left_foot
  - right_thigh / right_leg / right_foot

依赖: mediapipe, opencv-python, numpy, Pillow

API:
    separate_layers(image_path: str) -> list[LayerInfo]
        → 返回图层列表，每个图层包含名称、裁剪图像、mask、边界框

    LayerInfo = {
        "name": str,           # 图层名称
        "image": Image.Image,  # 裁剪后的 RGBA 图像
        "mask": Image.Image,   # Alpha mask
        "bbox": (x, y, w, h),  # 在原图中的边界框
        "landmark": (x, y),    # 该部位的中心/关键点坐标
    }
"""

import logging
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LayerInfo:
    """图层信息数据类"""
    name: str                          # 图层名称 (如 "head", "torso")
    image: Image.Image                 # RGBA 裁剪图像
    bbox: tuple                        # 在原图中的边界框 (x, y, w, h)
    landmark: Optional[tuple] = None   # 关键点坐标 (x, y)
    parent: Optional[str] = None       # 父图层名称 (用于骨骼层级)
    pivot: Optional[tuple] = None      # 旋转轴心点 (相对于裁剪图像)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bbox": self.bbox,
            "landmark": self.landmark,
            "parent": self.parent,
            "pivot": self.pivot,
        }


# MediaPipe 姿态关键点索引
# https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
POSE_LANDMARKS = {
    "nose": 0,
    "left_eye_inner": 1, "left_eye": 2, "left_eye_outer": 3,
    "right_eye_inner": 4, "right_eye": 5, "right_eye_outer": 6,
    "left_ear": 7, "right_ear": 8,
    "mouth_left": 9, "mouth_right": 10,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_pinky": 17, "right_pinky": 18,
    "left_index": 19, "right_index": 20,
    "left_thumb": 21, "right_thumb": 22,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
    "left_heel": 29, "right_heel": 30,
    "left_foot_index": 31, "right_foot_index": 32,
}

# 图层定义：(名称, 包含的关键点, 父图层, 扩展系数)
LAYER_DEFS = [
    # 头部：鼻子 + 眼睛 + 耳朵 + 嘴巴 — 向外扩展 50%
    ("head", ["nose", "left_eye", "right_eye", "left_ear", "right_ear",
              "mouth_left", "mouth_right",
              "left_eye_inner", "left_eye_outer",
              "right_eye_inner", "right_eye_outer"], None, 0.5),
    # 躯干：双肩 + 双髋
    ("torso", ["left_shoulder", "right_shoulder",
               "left_hip", "right_hip"], "head", 0.15),
    # 左臂
    ("left_upper_arm", ["left_shoulder", "left_elbow"], "torso", 0.3),
    ("left_forearm", ["left_elbow", "left_wrist"], "left_upper_arm", 0.3),
    ("left_hand", ["left_wrist", "left_index", "left_pinky", "left_thumb"],
     "left_forearm", 0.5),
    # 右臂
    ("right_upper_arm", ["right_shoulder", "right_elbow"], "torso", 0.3),
    ("right_forearm", ["right_elbow", "right_wrist"], "right_upper_arm", 0.3),
    ("right_hand", ["right_wrist", "right_index", "right_pinky", "right_thumb"],
     "right_forearm", 0.5),
    # 左腿
    ("left_thigh", ["left_hip", "left_knee"], "torso", 0.2),
    ("left_leg", ["left_knee", "left_ankle"], "left_thigh", 0.2),
    ("left_foot", ["left_ankle", "left_heel", "left_foot_index"],
     "left_leg", 0.4),
    # 右腿
    ("right_thigh", ["right_hip", "right_knee"], "torso", 0.2),
    ("right_leg", ["right_knee", "right_ankle"], "right_thigh", 0.2),
    ("right_foot", ["right_ankle", "right_heel", "right_foot_index"],
     "right_leg", 0.4),
]


def _detect_landmarks(image: np.ndarray):
    """
    使用 MediaPipe Pose 检测人物关键点（Tasks API）。

    Returns:
        list[dict]: 关键点列表，每个含 x, y, z, visibility
        None: 如果未检测到人物

    注意：首次运行会自动下载 pose_landmarker.task 模型文件。
    """
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

    # 模型文件位置
    model_path = os.environ.get(
        "MEDIAPIPE_POSE_MODEL",
        str(Path(__file__).resolve().parent.parent.parent / "models" / "pose_landmarker_lite.task")
    )

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
    )

    with PoseLandmarker.create_from_options(options) as landmarker:
        # 将 numpy 数组转为 MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        result = landmarker.detect(mp_image)

    if not result.pose_landmarks:
        return None

    h, w, _ = image.shape
    landmarks = []
    for lm in result.pose_landmarks[0]:
        landmarks.append({
            "x": lm.x * w,
            "y": lm.y * h,
            "z": lm.z or 0,
            "visibility": lm.visibility or 0,
        })
    return landmarks


def _extract_part(
    image: np.ndarray,
    mask: np.ndarray,
    bbox: tuple,
    part_name: str,
    landmarks: list,
    landmark_names: list,
    parent: Optional[str],
) -> LayerInfo:
    """从原图中裁剪指定部位，生成 RGBA 图层。"""
    x, y, w, h = bbox
    h_img, w_img = image.shape[:2]

    # 裁剪
    crop_img = image[y:y+h, x:x+w]
    crop_mask = mask[y:y+h, x:x+w]

    # 确保裁剪区域有效
    if crop_img.size == 0:
        crop_img = np.zeros((h, w, 3), dtype=np.uint8)
        crop_mask = np.zeros((h, w), dtype=np.uint8)

    # 转为 RGBA
    rgba = np.dstack([
        crop_img[:, :, 0],
        crop_img[:, :, 1],
        crop_img[:, :, 2],
        crop_mask,
    ])

    pil_image = Image.fromarray(rgba, "RGBA")

    # 计算旋转轴心 (关节连接点)
    pivot = None
    if landmark_names:
        # 用第一个关键点作为轴心
        lm_idx = POSE_LANDMARKS.get(landmark_names[0])
        if lm_idx is not None and lm_idx < len(landmarks):
            lm = landmarks[lm_idx]
            pivot = (lm["x"] - x, lm["y"] - y)  # 相对于裁剪图像

    # 计算部位中心点
    center = None
    weights = []
    xs, ys = [], []
    for name in landmark_names:
        idx = POSE_LANDMARKS.get(name)
        if idx is not None and idx < len(landmarks):
            lm = landmarks[idx]
            xs.append(lm["x"])
            ys.append(lm["y"])
    if xs:
        center = (sum(xs) / len(xs), sum(ys) / len(ys))

    return LayerInfo(
        name=part_name,
        image=pil_image,
        bbox=bbox,
        landmark=center,
        parent=parent,
        pivot=pivot,
    )


def separate_layers(
    image_path,
    *,
    return_original_size: bool = True,
    min_visibility: float = 0.3,
):
    """
    对输入图片进行图层分离。

    Args:
        image_path: 图片路径 (str/Path) 或 PIL Image
        return_original_size: 是否返回原始图像尺寸
        min_visibility: 关键点最低可见度阈值

    Returns:
        layers: list[LayerInfo] — 分离后的图层列表
        original_size: tuple (w, h) — 仅在 return_original_size=True 时返回

    Raises:
        ValueError: 未检测到人物
        ImportError: mediapipe 未安装
    """
    try:
        import mediapipe  # noqa: F401
    except ImportError:
        raise ImportError("mediapipe 未安装，请运行: pip install mediapipe")

    # --- 加载图像 ---
    if isinstance(image_path, (str, Path)):
        pil_img = Image.open(image_path).convert("RGB")
    elif isinstance(image_path, Image.Image):
        pil_img = image_path.convert("RGB")
    else:
        raise TypeError(f"不支持的输入类型: {type(image_path)}")

    original_size = pil_img.size  # (w, h)
    img_np = np.array(pil_img)
    h, w = img_np.shape[:2]

    # --- 检测关键点 ---
    landmarks = _detect_landmarks(img_np)
    if landmarks is None:
        raise ValueError("未检测到人物，请确认图片中包含清晰完整的人体")

    logger.info(f"检测到 {len(landmarks)} 个关键点")

    # --- 创建全身 mask ---
    # 简化方案：基于关键点生成椭圆形区域 mask
    # 后续可用 SAM 等更精确的分割模型替代
    body_mask = np.zeros((h, w), dtype=np.uint8)

    # 用所有可见关键点生成粗略的身体 mask
    for lm in landmarks:
        if lm["visibility"] > min_visibility:
            cv_x, cv_y = int(lm["x"]), int(lm["y"])
            # 每个关键点周围画一个椭圆区域
            radius = 40
            y1 = max(0, cv_y - radius)
            y2 = min(h, cv_y + radius)
            x1 = max(0, cv_x - radius)
            x2 = min(w, cv_x + radius)
            body_mask[y1:y2, x1:x2] = 255

    # 对 mask 做形态学闭运算填充空洞
    import cv2
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_CLOSE, kernel)
    body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_OPEN, kernel)

    # --- 按部位分离 ---
    layers = []
    for part_name, lm_names, parent, expand_ratio in LAYER_DEFS:
        # 收集该部位的关键点坐标
        points = []
        visible_points = []
        for name in lm_names:
            idx = POSE_LANDMARKS.get(name)
            if idx is not None and idx < len(landmarks):
                lm = landmarks[idx]
                points.append((lm["x"], lm["y"]))
                if lm["visibility"] > min_visibility:
                    visible_points.append((lm["x"], lm["y"]))

        if not visible_points:
            logger.debug(f"跳过 {part_name}: 所有关键点不可见")
            continue

        # 计算边界框
        xs = [p[0] for p in visible_points]
        ys = [p[1] for p in visible_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        bw = max_x - min_x
        bh = max_y - min_y

        # 扩展边界框
        expand = expand_ratio
        pad_w = bw * expand
        pad_h = bh * expand

        # 确保最小尺寸
        bw = max(bw, 30)
        bh = max(bh, 30)

        bbox_x = max(0, int(min_x - pad_w))
        bbox_y = max(0, int(min_y - pad_h))
        bbox_w = min(w - bbox_x, int(bw + 2 * pad_w))
        bbox_h = min(h - bbox_y, int(bh + 2 * pad_h))

        bbox = (bbox_x, bbox_y, bbox_w, bbox_h)

        # 为当前部位生成局部 mask
        part_mask = np.zeros((h, w), dtype=np.uint8)
        for px, py in visible_points:
            cv2.circle(part_mask, (int(px), int(py)),
                       int(min(bw, bh) * 0.6), 255, -1)

        # 用全身 mask 限制范围
        part_mask = cv2.bitwise_and(part_mask, body_mask)

        layer = _extract_part(
            img_np, part_mask, bbox, part_name,
            landmarks, lm_names, parent
        )
        layers.append(layer)

    logger.info(f"图层分离完成: {len(layers)} 个图层")

    if return_original_size:
        return layers, original_size
    return layers


# --- 模块自检 ---
def check_dependencies() -> bool:
    """检查模块依赖是否就绪。"""
    try:
        import mediapipe  # noqa: F401
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False
