"""分割子包 — 图层分离、身体部位检测、面部细节"""
from .layer_separation import separate_layers, LayerInfo, check_dependencies
from .sam_segmentation import separate_layers_sam
from .face_details import detect_face_details, FaceDetails
