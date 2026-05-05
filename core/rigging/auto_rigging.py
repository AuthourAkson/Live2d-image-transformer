"""
自动骨骼绑定模块 (Auto Rigging)
================================
基于图层信息自动生成 Live2D 骨骼和变形参数。
采用 Cubism 3+ 参数体系，为每个图层自动配置：

  - 标准角度参数: ParamAngleX, ParamAngleY, ParamAngleZ
  - 身体参数: ParamBodyAngleX, ParamBodyAngleY, ParamBodyAngleZ
  - 呼吸参数: ParamBreath
  - 部位特有参数: 如眼睛开合、嘴型等 (placeholder)

输出格式兼容 Live2D Cubism SDK 的 .model3.json 参数定义。

API:
    auto_rig(layers: list[LayerInfo]) -> RigResult
        → 返回骨骼绑定结果

    RigResult = {
        "parameters": [...],   # Live2D 参数定义
        "parts": [...],        # 部件绑定信息
        "hierarchy": {...},    # 骨骼层级
    }
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ParameterDef:
    """Live2D 参数定义"""
    id: str                # 参数 ID (如 "ParamAngleX")
    name: str              # 显示名称
    default: float = 0.0   # 默认值
    min: float = -30.0     # 最小值
    max: float = 30.0      # 最大值


@dataclass
class PartBinding:
    """部件与参数的绑定关系"""
    part_name: str         # 图层名称
    params: list[str]      # 绑定的参数 ID 列表
    pivot: Optional[tuple] = None  # 旋转轴心


@dataclass
class RigResult:
    """骨骼绑定结果"""
    parameters: list[ParameterDef]
    parts: list[PartBinding]
    hierarchy: dict          # {part_name: parent_name}
    metadata: dict = field(default_factory=dict)


# === 标准 Live2D 参数定义 ===
STANDARD_PARAMETERS = [
    # --- 全局角度 ---
    ParameterDef("ParamAngleX", "角度 X", 0.0, -30.0, 30.0),
    ParameterDef("ParamAngleY", "角度 Y", 0.0, -30.0, 30.0),
    ParameterDef("ParamAngleZ", "角度 Z", 0.0, -30.0, 30.0),

    # --- 身体 ---
    ParameterDef("ParamBodyAngleX", "身体角度 X", 0.0, -10.0, 10.0),
    ParameterDef("ParamBodyAngleY", "身体角度 Y", 0.0, -10.0, 10.0),
    ParameterDef("ParamBodyAngleZ", "身体角度 Z", 0.0, -10.0, 10.0),

    # --- 呼吸 ---
    ParameterDef("ParamBreath", "呼吸", 0.0, 0.0, 1.0),
]

# 每个部位特有的附加参数
PART_SPECIFIC_PARAMS = {
    "head": [
        ParameterDef("ParamHeadAngleX", "头部角度 X", 0.0, -15.0, 15.0),
        ParameterDef("ParamHeadAngleY", "头部角度 Y", 0.0, -15.0, 15.0),
        ParameterDef("ParamEyeLOpen", "左眼开合", 1.0, 0.0, 1.0),
        ParameterDef("ParamEyeROpen", "右眼开合", 1.0, 0.0, 1.0),
        ParameterDef("ParamMouthOpenY", "嘴纵向开合", 0.0, 0.0, 1.0),
    ],
    "torso": [
        ParameterDef("ParamBodyAngleX", "身体角度 X", 0.0, -10.0, 10.0),
        ParameterDef("ParamBodyAngleY", "身体角度 Y", 0.0, -10.0, 10.0),
    ],
}

# 各部位绑定的参数
PART_PARAM_BINDINGS = {
    "head": ["ParamAngleX", "ParamAngleY", "ParamAngleZ",
             "ParamHeadAngleX", "ParamHeadAngleY",
             "ParamEyeLOpen", "ParamEyeROpen", "ParamMouthOpenY"],
    "torso": ["ParamAngleX", "ParamAngleY", "ParamBodyAngleX",
              "ParamBodyAngleY", "ParamBreath"],
    # 四肢默认绑定身体角度 + 全局角度
    "left_upper_arm":  ["ParamAngleX", "ParamAngleY", "ParamBodyAngleY"],
    "left_forearm":    ["ParamAngleX", "ParamAngleY", "ParamBodyAngleY"],
    "left_hand":       ["ParamAngleX", "ParamAngleY", "ParamBodyAngleY"],
    "right_upper_arm": ["ParamAngleX", "ParamAngleY", "ParamBodyAngleY"],
    "right_forearm":   ["ParamAngleX", "ParamAngleY", "ParamBodyAngleY"],
    "right_hand":      ["ParamAngleX", "ParamAngleY", "ParamBodyAngleY"],
    "left_thigh":  ["ParamAngleX", "ParamAngleY", "ParamBodyAngleX"],
    "left_leg":    ["ParamAngleX", "ParamAngleY", "ParamBodyAngleX"],
    "left_foot":   ["ParamAngleX", "ParamAngleY", "ParamBodyAngleX"],
    "right_thigh": ["ParamAngleX", "ParamAngleY", "ParamBodyAngleX"],
    "right_leg":  ["ParamAngleX", "ParamAngleY", "ParamBodyAngleX"],
    "right_foot": ["ParamAngleX", "ParamAngleY", "ParamBodyAngleX"],
}


def auto_rig(layers) -> RigResult:
    """
    对分离后的图层进行自动骨骼绑定。

    Args:
        layers: list[LayerInfo] — separate_layers() 的输出

    Returns:
        RigResult: 包含参数定义、部件绑定、层级信息
    """
    # --- 收集所有参数 ---
    all_params: dict[str, ParameterDef] = {}
    for p in STANDARD_PARAMETERS:
        all_params[p.id] = p

    # --- 构建部件绑定 ---
    part_bindings = []
    hierarchy = {}

    for layer in layers:
        name = layer.name
        parent = layer.parent

        # 获取该部位的参数
        param_ids = PART_PARAM_BINDINGS.get(name, ["ParamAngleX", "ParamAngleY"])
        part_bindings.append(PartBinding(
            part_name=name,
            params=param_ids,
            pivot=layer.pivot,
        ))

        # 层级
        hierarchy[name] = parent

        # 添加部位特有参数
        specific_params = PART_SPECIFIC_PARAMS.get(name, [])
        for sp in specific_params:
            if sp.id not in all_params:
                all_params[sp.id] = sp

    # --- 计算元数据 ---
    metadata = {
        "total_parts": len(layers),
        "total_parameters": len(all_params),
        "part_names": [l.name for l in layers],
        "root_part": next((n for n, p in hierarchy.items() if p is None), None),
    }

    logger.info(
        f"骨骼绑定完成: {metadata['total_parts']} 个部件, "
        f"{metadata['total_parameters']} 个参数"
    )

    return RigResult(
        parameters=list(all_params.values()),
        parts=part_bindings,
        hierarchy=hierarchy,
        metadata=metadata,
    )


# --- 模块自检 ---
def check_dependencies() -> bool:
    """无需外部依赖。"""
    return True
