#!/usr/bin/env python3
"""
Live2D Image Transformer — 完整管线示例
========================================
从单张图片到 Live2D 模型的端到端流程。

用法:
    python examples/basic_pipeline.py input.jpg -o output_dir -n my_model
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到 path (便于直接运行)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.preprocessing import remove_background
from core.segmentation import separate_layers
from core.rigging import auto_rig
from core.export import export_live2d

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


def run_pipeline(
    input_path: str,
    output_dir: str = "./output",
    model_name: str = "model",
    atlas_size: int = 2048,
    skip_bg_removal: bool = False,
) -> str:
    """
    执行完整管线。

    Args:
        input_path: 输入图片路径
        output_dir: 输出目录
        model_name: 模型名称
        atlas_size: 纹理图集尺寸
        skip_bg_removal: 跳过背景移除 (如果图片已扣图)

    Returns:
        输出目录路径
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: 背景移除 ---
    if skip_bg_removal:
        logger.info("跳过背景移除 (已扣图模式)")
        processed_path = str(input_path)
    else:
        processed_path = remove_background(
            str(input_path),
            str(output_dir / f"{input_path.stem}_nobg.png"),
        )
    logger.info(f"[1/4] 背景移除完成: {processed_path}")

    # --- Step 2: 图层分离 ---
    layers, original_size = separate_layers(processed_path)
    logger.info(f"[2/4] 图层分离完成: {len(layers)} 个图层")

    for layer in layers:
        logger.debug(f"  {layer.name}: bbox={layer.bbox}, parent={layer.parent}")

    # --- Step 3: 骨骼绑定 ---
    rig = auto_rig(layers)
    logger.info(f"[3/4] 骨骼绑定完成: {rig.metadata['total_parameters']} 个参数")

    # --- Step 4: 导出 Live2D ---
    l2d_output = output_dir / model_name
    result = export_live2d(
        layers=layers,
        rig_result=rig,
        output_dir=str(l2d_output),
        model_name=model_name,
        atlas_size=atlas_size,
    )
    logger.info(f"[4/4] Live2D 导出完成: {result}")

    # --- 汇总 ---
    logger.info("=" * 50)
    logger.info("管线执行完毕！")
    logger.info(f"  输入: {input_path}")
    logger.info(f"  输出: {result}")
    logger.info(f"  图层: {len(layers)} 个")
    logger.info(f"  参数: {rig.metadata['total_parameters']} 个")
    logger.info(f"  纹理: {atlas_size}x{atlas_size}")
    logger.info("=" * 50)
    logger.info("下一步: 用 Live2D Cubism Editor 打开 .model3.json 进行细化调整")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Live2D Image Transformer — 图片转 Live2D 模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s character.png
  %(prog)s character.png -o ./my_output -n my_chara --skip-bg
  %(prog)s character.png --atlas-size 4096
        """,
    )
    parser.add_argument("input", help="输入图片路径")
    parser.add_argument("-o", "--output", default="./output",
                        help="输出目录 (默认: ./output)")
    parser.add_argument("-n", "--name", default="model",
                        help="模型名称 (默认: model)")
    parser.add_argument("--atlas-size", type=int, default=2048,
                        help="纹理图集尺寸 (默认: 2048)")
    parser.add_argument("--skip-bg", action="store_true",
                        help="跳过背景移除 (图片已扣图)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="详细日志输出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        run_pipeline(
            input_path=args.input,
            output_dir=args.output,
            model_name=args.name,
            atlas_size=args.atlas_size,
            skip_bg_removal=args.skip_bg,
        )
    except Exception as e:
        logger.error(f"管线失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
