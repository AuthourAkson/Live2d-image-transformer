"""
Live2D Image Transformer — Core Package
========================================
将静态图片自动转换为 Live2D 可动模型。

Pipeline:
    1. preprocessing  — 背景移除、图像增强
    2. segmentation   — 身体部位分割 (椭圆/SAM)、面部细节检测
    3. rigging        — 自动骨骼绑定、参数生成
    4. export         — Live2D Cubism 格式导出
"""

__version__ = "0.2.0"
__author__ = "AuthourAkson"

from .preprocessing.background_removal import remove_background
from .segmentation.layer_separation import separate_layers
from .segmentation.sam_segmentation import separate_layers_sam
from .segmentation.face_details import detect_face_details
from .rigging.auto_rigging import auto_rig
from .export.live2d_export import export_live2d
