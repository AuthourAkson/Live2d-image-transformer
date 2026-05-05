"""
Live2D 导出模块 (Live2D Export)
===============================
将图层 + 骨骼绑定结果导出为 Live2D Cubism 4 格式 (.model3.json + 纹理图集)。

输出结构：
    output_dir/
    ├── <name>.model3.json       # 模型定义文件
    ├── <name>.4096/
    │   └── texture_00.png       # 纹理图集 (atlas)
    └── <name>.cdi3.json         # 补充显示信息 (可选)

兼容: Live2D Cubism SDK for Native 4.x / Web 4.x

API:
    export_live2d(layers, rig_result, output_dir, model_name) -> str
        → 返回输出目录路径
"""

import json
import logging
import math
import os
from pathlib import Path
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)


def _pack_textures(layers, atlas_size: int = 2048) -> tuple:
    """
    将所有图层打包到一张纹理图集中（简单矩形 packer）。

    Returns:
        atlas_image: PIL Image — 纹理图集
        uv_map: dict — {layer_name: (x, y, w, h)} 归一化 UV 坐标
    """
    # 按面积从大到小排序
    sorted_layers = sorted(
        layers, key=lambda l: l.image.width * l.image.height, reverse=True
    )

    atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))
    uv_map = {}

    # 简单行式 packer
    x, y = 0, 0
    row_height = 0

    for layer in sorted_layers:
        img = layer.image
        iw, ih = img.width, img.height

        # 如果超出当前行宽度，换行
        if x + iw > atlas_size:
            x = 0
            y += row_height
            row_height = 0

        # 如果超出总高度
        if y + ih > atlas_size:
            logger.warning(f"纹理图集溢出！图层 {layer.name} 放不下。扩大 atlas 尺寸。")
            # 简单处理：跳过
            uv_map[layer.name] = (0.0, 0.0, 0.0, 0.0)
            continue

        # 贴入图集
        atlas.paste(img, (x, y), img if img.mode == "RGBA" else None)

        # 记录归一化 UV (左上角 + 尺寸)
        uv_map[layer.name] = (
            x / atlas_size,
            y / atlas_size,
            iw / atlas_size,
            ih / atlas_size,
        )

        x += iw
        row_height = max(row_height, ih)

    return atlas, uv_map


def _build_model3_json(
    model_name: str,
    layers,
    rig_result,
    uv_map: dict,
    atlas_size: int,
    canvas_size: tuple,
) -> dict:
    """
    构建 .model3.json 模型定义文件。

    兼容 Live2D Cubism 4 format。
    """
    parts_list = []
    for layer in layers:
        name = layer.name
        uv = uv_map.get(name, (0, 0, 0, 0))
        parts_list.append({"Name": name, "Id": name})

    # 构建参数定义
    params_list = []
    for p in rig_result.parameters:
        params_list.append({
            "Id": p.id,
            "Name": p.name,
            "Default": p.default,
            "Min": p.min,
            "Max": p.max,
        })

    # 构建部件绑定到参数的关系
    # 在实际 Live2D 中这是通过 deformer 实现的，这里做简化
    groups = []
    group_id = 0
    for binding in rig_result.parts:
        group_id += 1
        group = {
            "Target": "Parameter",
            "Name": f"Group{binding.part_name}",
            "Ids": binding.params,
        }
        groups.append(group)

    # 画布尺寸
    canvas_w = canvas_size[0] if isinstance(canvas_size, tuple) else canvas_size[0]
    canvas_h = canvas_size[1] if isinstance(canvas_size, tuple) else canvas_size[1]

    model3 = {
        "Version": 3,
        "FileReferences": {
            "Moc": f"{model_name}.moc3",
            "Textures": [f"{model_name}.4096/texture_00.png"],
            "Physics": f"{model_name}.physics3.json",
            "DisplayInfo": f"{model_name}.cdi3.json",
        },
        "Groups": [
            {
                "Target": "Parameter",
                "Name": "Global",
                "Ids": [p.id for p in rig_result.parameters],
            }
        ],
        "HitAreas": [],
    }

    return model3


def _build_cdi3_json(model_name: str, parameters: list) -> dict:
    """构建 .cdi3.json (Cubism Display Info 3)。"""
    param_groups = []
    for p in parameters:
        param_groups.append({
            "Id": p.id,
            "GroupId": "Global",
            "Name": p.name,
        })

    return {
        "Version": 3,
        "Parameters": param_groups,
        "ParameterGroups": [
            {
                "Id": "Global",
                "Name": "全局参数",
                "GroupId": "",
            }
        ],
        "Parts": [],
    }


def _build_physics3_json(model_name: str) -> dict:
    """构建 .physics3.json (物理模拟，基础模板)。"""
    return {
        "Version": 3,
        "Meta": {
            "Fps": 30,
            "EffectiveForces": {
                "Gravity": {"X": 0, "Y": -1},
                "Wind": {"X": 0, "Y": 0},
            },
            "PhysicsSettingCount": 0,
        },
        "PhysicsSettings": [],
    }


def export_live2d(
    layers,
    rig_result,
    output_dir,
    model_name: str = "model",
    atlas_size: int = 2048,
) -> str:
    """
    将图层和绑定结果导出为 Live2D 格式。

    Args:
        layers: list[LayerInfo] — 分离后的图层
        rig_result: RigResult — 骨骼绑定结果
        output_dir: str/Path — 输出目录
        model_name: str — 模型名称
        atlas_size: int — 纹理图集尺寸 (默认 2048)

    Returns:
        str: 输出目录路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 纹理子目录
    texture_dir = output_dir / f"{model_name}.4096"
    texture_dir.mkdir(exist_ok=True)

    # --- 1. 打包纹理 ---
    atlas, uv_map = _pack_textures(layers, atlas_size)
    texture_path = texture_dir / "texture_00.png"
    atlas.save(str(texture_path), "PNG")
    logger.info(f"纹理图集已保存: {texture_path} ({atlas.width}x{atlas.height})")

    # --- 2. 确定画布尺寸 ---
    canvas_w = max((l.bbox[0] + l.bbox[2] for l in layers), default=512)
    canvas_h = max((l.bbox[1] + l.bbox[3] for l in layers), default=512)
    canvas_size = (canvas_w, canvas_h)

    # --- 3. 构建 model3.json ---
    model3 = _build_model3_json(
        model_name, layers, rig_result, uv_map, atlas_size, canvas_size
    )
    model3_path = output_dir / f"{model_name}.model3.json"
    with open(model3_path, "w", encoding="utf-8") as f:
        json.dump(model3, f, indent=2, ensure_ascii=False)
    logger.info(f"模型定义已保存: {model3_path}")

    # --- 4. 构建 cdi3.json ---
    cdi3 = _build_cdi3_json(model_name, rig_result.parameters)
    cdi3_path = output_dir / f"{model_name}.cdi3.json"
    with open(cdi3_path, "w", encoding="utf-8") as f:
        json.dump(cdi3, f, indent=2, ensure_ascii=False)

    # --- 5. 构建 physics3.json ---
    physics3 = _build_physics3_json(model_name)
    physics3_path = output_dir / f"{model_name}.physics3.json"
    with open(physics3_path, "w", encoding="utf-8") as f:
        json.dump(physics3, f, indent=2, ensure_ascii=False)

    # --- 6. 生成占位 .moc3 (二进制格式，生成占位说明) ---
    moc3_placeholder = output_dir / f"{model_name}.moc3"
    moc3_placeholder.write_text(
        "# Live2D .moc3 placeholder\n"
        "# .moc3 是 Live2D 的二进制网格/骨骼数据格式。\n"
        "# 完整生成需 Live2D Cubism SDK 或 Cubism Editor。\n"
        "# 此文件为占位符，实际 moc3 请用 Cubism Editor 加载 .model3.json 后生成。\n",
        encoding="utf-8"
    )
    logger.info(f"MOC3 占位文件已创建: {moc3_placeholder}")

    # --- 7. 导出图层预览 ---
    for layer in layers:
        preview_path = output_dir / f"preview_{layer.name}.png"
        layer.image.save(str(preview_path), "PNG")

    logger.info(f"Live2D 导出完成 → {output_dir}")
    return str(output_dir.resolve())


# --- 模块自检 ---
def check_dependencies() -> bool:
    """无需外部依赖。"""
    return True
