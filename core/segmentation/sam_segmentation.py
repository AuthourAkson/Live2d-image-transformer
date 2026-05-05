"""
SAM 精确分割模块 (SAM-based Segmentation)
==========================================
基于 Meta SAM (Segment Anything Model) 实现像素级身体部位分割。
替代原有的椭圆近似 mask，提供精确的图层分离。

工作流程:
  1. MediaPipe Pose 检测关键点 → 确定部位边界框
  2. SAM 用边界框 prompt 生成精确 mask
  3. 精确提取每个身体部位

依赖: segment-anything, mediapipe, opencv-python, numpy
模型: sam_vit_b_01ec64.pth (~358MB, 首次自动下载)

API:
    separate_layers_sam(image_path) -> list[LayerInfo]
"""

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .layer_separation import (
    LayerInfo, POSE_LANDMARKS, LAYER_DEFS, _detect_landmarks,
)

logger = logging.getLogger(__name__)

# SAM 模型路径
SAM_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
SAM_MODEL_NAME = "sam_vit_b_01ec64.pth"
SAM_MODEL_PATH = SAM_MODEL_DIR / SAM_MODEL_NAME

# 全局 SAM 实例（单例）
_sam_predictor = None


def _get_sam_predictor():
    """获取或初始化 SAM predictor（单例模式）。"""
    global _sam_predictor
    if _sam_predictor is None:
        from segment_anything import sam_model_registry, SamPredictor

        if not SAM_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"SAM 模型未找到: {SAM_MODEL_PATH}\n"
                f"请下载: wget -O {SAM_MODEL_PATH} "
                f"https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
            )

        logger.info(f"加载 SAM 模型: {SAM_MODEL_PATH}")
        sam = sam_model_registry["vit_b"](checkpoint=str(SAM_MODEL_PATH))

        # 尝试用 GPU，失败则用 CPU
        try:
            import torch
            if torch.cuda.is_available():
                sam.to(device="cuda")
                logger.info("SAM 使用 CUDA GPU")
            elif torch.backends.mps.is_available():
                sam.to(device="mps")
                logger.info("SAM 使用 Apple MPS")
            else:
                sam.to(device="cpu")
                logger.info("SAM 使用 CPU (较慢)")
        except Exception:
            sam.to(device="cpu")
            logger.info("SAM 使用 CPU")

        _sam_predictor = SamPredictor(sam)
        logger.info("SAM predictor 已就绪")
    return _sam_predictor


def _compute_body_mask_with_sam(image: np.ndarray) -> np.ndarray:
    """
    用 SAM 生成全身 mask（基于全身边界框）。
    
    先用 MediaPipe 检测肩膀到髋部的边界，再用 SAM 精确分割人体。
    
    Returns:
        np.ndarray: HxW 的二值 mask (0/255)
    """
    predictor = _get_sam_predictor()
    h, w = image.shape[:2]

    # 检测姿态关键点，获取身体大致范围
    landmarks = _detect_landmarks(image)
    if landmarks is None:
        raise ValueError("未检测到人物，请确认图片中包含清晰完整的人体")

    # 用肩膀 + 髋部确定身体大致边界，然后外扩 30%
    body_indices = [
        POSE_LANDMARKS["left_shoulder"], POSE_LANDMARKS["right_shoulder"],
        POSE_LANDMARKS["left_hip"], POSE_LANDMARKS["right_hip"],
        POSE_LANDMARKS["nose"],
        POSE_LANDMARKS["left_ankle"], POSE_LANDMARKS["right_ankle"],
    ]

    xs, ys = [], []
    for idx in body_indices:
        if idx < len(landmarks) and landmarks[idx]["visibility"] > 0.3:
            xs.append(landmarks[idx]["x"])
            ys.append(landmarks[idx]["y"])

    if not xs:
        # fallback: 全图
        return np.ones((h, w), dtype=np.uint8) * 255

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # 扩展边界框
    bw = max_x - min_x
    bh = max_y - min_y
    pad_w = bw * 0.5
    pad_h = bh * 0.5

    box_x = max(0, int(min_x - pad_w))
    box_y = max(0, int(min_y - pad_h))
    box_w = min(w - box_x, int(bw + 2 * pad_w))
    box_h = min(h - box_y, int(bh + 2 * pad_h))

    # SAM 预测
    predictor.set_image(image)
    input_box = np.array([box_x, box_y, box_x + box_w, box_y + box_h])
    masks, scores, _ = predictor.predict(
        point_coords=None,
        point_labels=None,
        box=input_box[None, :],
        multimask_output=False,
    )

    body_mask = (masks[0] * 255).astype(np.uint8)
    logger.info(f"SAM 全身 mask 已生成 (分数: {scores[0]:.3f})")
    return body_mask


def separate_layers_sam(
    image_path,
    *,
    return_original_size: bool = True,
    min_visibility: float = 0.3,
    use_sam_body_mask: bool = True,
):
    """
    使用 SAM 进行像素级精确图层分离。
    
    Args:
        image_path: 图片路径 (str/Path) 或 PIL Image
        return_original_size: 是否返回原始图像尺寸
        min_visibility: 关键点最低可见度阈值
        use_sam_body_mask: 是否用 SAM 生成全身 mask (否则用椭圆近似)
    
    Returns:
        layers: list[LayerInfo] — 精确分离的图层列表
        original_size: tuple (w, h) — 仅 return_original_size=True 时
    
    Raises:
        FileNotFoundError: SAM 模型未下载
        ValueError: 未检测到人物
    """
    import cv2

    # --- 加载图像 ---
    if isinstance(image_path, (str, Path)):
        pil_img = Image.open(image_path).convert("RGB")
    elif isinstance(image_path, Image.Image):
        pil_img = image_path.convert("RGB")
    else:
        raise TypeError(f"不支持的输入类型: {type(image_path)}")

    original_size = pil_img.size
    img_np = np.array(pil_img)
    h, w = img_np.shape[:2]

    # --- 检测关键点 ---
    landmarks = _detect_landmarks(img_np)
    if landmarks is None:
        raise ValueError("未检测到人物，请确认图片中包含清晰完整的人体")

    logger.info(f"检测到 {len(landmarks)} 个关键点 (SAM 增强模式)")

    # --- 生成全身 mask ---
    if use_sam_body_mask:
        body_mask = _compute_body_mask_with_sam(img_np)
    else:
        # fallback: 椭圆近似
        body_mask = np.zeros((h, w), dtype=np.uint8)
        for lm in landmarks:
            if lm["visibility"] > min_visibility:
                cv_x, cv_y = int(lm["x"]), int(lm["y"])
                radius = 40
                y1 = max(0, cv_y - radius)
                y2 = min(h, cv_y + radius)
                x1 = max(0, cv_x - radius)
                x2 = min(w, cv_x + radius)
                body_mask[y1:y2, x1:x2] = 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_CLOSE, kernel)
        body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_OPEN, kernel)

    # --- SAM 逐部位分割 ---
    predictor = _get_sam_predictor()
    predictor.set_image(img_np)

    layers = []
    for part_name, lm_names, parent, expand_ratio in LAYER_DEFS:
        # 收集可见关键点
        visible_points = []
        for name in lm_names:
            idx = POSE_LANDMARKS.get(name)
            if idx is not None and idx < len(landmarks):
                lm = landmarks[idx]
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

        bw = max(max_x - min_x, 30)
        bh = max(max_y - min_y, 30)

        # 扩展边界框
        pad_w = bw * expand_ratio
        pad_h = bh * expand_ratio

        box_x = max(0, int(min_x - pad_w))
        box_y = max(0, int(min_y - pad_h))
        box_w = min(w - box_x, int(bw + 2 * pad_w))
        box_h = min(h - box_y, int(bh + 2 * pad_h))

        bbox = (box_x, box_y, box_w, box_h)

        # 用关键点作为正样本提示点
        point_coords = np.array(visible_points, dtype=np.float32)
        point_labels = np.ones(len(visible_points), dtype=np.int32)

        # SAM 预测
        input_box = np.array([box_x, box_y, box_x + box_w, box_y + box_h])
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=input_box[None, :],
            multimask_output=False,
        )

        part_mask = (masks[0] * 255).astype(np.uint8)

        # 用全身 mask 约束
        part_mask = cv2.bitwise_and(part_mask, body_mask)

        # 提取图层
        layer = _extract_part_sam(
            img_np, part_mask, bbox, part_name,
            landmarks, lm_names, parent
        )
        layers.append(layer)

        logger.debug(
            f"  {part_name}: bbox={bbox}, SAM score={scores[0]:.3f}"
        )

    logger.info(f"SAM 图层分离完成: {len(layers)} 个图层 (像素级精度)")

    if return_original_size:
        return layers, original_size
    return layers


def _extract_part_sam(
    image: np.ndarray,
    mask: np.ndarray,
    bbox: tuple,
    part_name: str,
    landmarks: list,
    landmark_names: list,
    parent: Optional[str],
) -> LayerInfo:
    """从原图中用 SAM mask 裁剪指定部位。"""
    x, y, w, h = bbox
    h_img, w_img = image.shape[:2]

    # 裁剪
    crop_img = image[y:y+h, x:x+w]
    crop_mask = mask[y:y+h, x:x+w]

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

    # 旋转轴心
    pivot = None
    if landmark_names:
        lm_idx = POSE_LANDMARKS.get(landmark_names[0])
        if lm_idx is not None and lm_idx < len(landmarks):
            lm = landmarks[lm_idx]
            pivot = (lm["x"] - x, lm["y"] - y)

    # 中心点
    center = None
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


def check_dependencies() -> bool:
    """检查 SAM 分割模块依赖是否就绪。"""
    try:
        import segment_anything  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False
