#!/usr/bin/env python3
"""
Live2D Image Transformer — 完整管线示例
========================================
从单张图片到 Live2D 模型的端到端流程。

用法:
    python examples/basic_pipeline.py input.jpg -o output_dir -n my_model
    python examples/basic_pipeline.py input.jpg --sam       # 强制 SAM 分割
    python examples/basic_pipeline.py input.jpg --no-sam    # 用椭圆近似
    python examples/basic_pipeline.py input.jpg --face      # 启用面部细节
"""

import argparse
import logging
import sys
import os
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


def _check_sam_available():
    """检查 SAM 是否可用（模型文件 + 依赖）。"""
    model_path = Path(__file__).resolve().parent.parent / "models" / "sam_vit_b_01ec64.pth"
    if not model_path.exists():
        return False
    try:
        import segment_anything  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def _check_face_mesh_available():
    """检查面部细节检测是否可用。"""
    try:
        import mediapipe  # noqa: F401
        return True
    except ImportError:
        return False


def run_pipeline(
    input_path: str,
    output_dir: str = "./output",
    model_name: str = "model",
    atlas_size: int = 2048,
    skip_bg_removal: bool = False,
    use_sam: bool = None,       # None=自动, True=强制, False=禁用
    use_face_details: bool = False,
) -> str:
    """
    执行完整管线。

    Args:
        input_path: 输入图片路径
        output_dir: 输出目录
        model_name: 模型名称
        atlas_size: 纹理图集尺寸
        skip_bg_removal: 跳过背景移除 (如果图片已扣图)
        use_sam: SAM 分割 (None=自动检测)
        use_face_details: 启用面部细节检测

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
    # 智能选择分割模式
    sam_available = _check_sam_available()
    if use_sam is None:
        use_sam = sam_available

    sam_actually_used = False
    if use_sam and sam_available:
        logger.info("使用 SAM 像素级精确分割")
        from core.segmentation.sam_segmentation import separate_layers_sam
        layers, original_size = separate_layers_sam(
            processed_path,
            use_sam_body_mask=True,
        )
        sam_actually_used = True
    else:
        if use_sam and not sam_available:
            logger.warning(
                "SAM 模型未找到，回退到椭圆近似分割。\n"
                "  下载 SAM 模型: bash setup.sh --with-sam"
            )
        else:
            logger.info("使用椭圆近似分割 (快速模式)")
        layers, original_size = separate_layers(processed_path)

    logger.info(f"[2/4] 图层分离完成: {len(layers)} 个图层")

    for layer in layers:
        logger.debug(f"  {layer.name}: bbox={layer.bbox}, parent={layer.parent}")

    # --- Step 2.5: 面部细节 (可选) ---
    face_details = None
    if use_face_details and _check_face_mesh_available():
        try:
            from core.segmentation.face_details import detect_face_details
            face_details = detect_face_details(processed_path)
            if face_details:
                logger.info(
                    f"[面部] 左眼开合={face_details.left_eye.openness:.2f}, "
                    f"右眼开合={face_details.right_eye.openness:.2f}, "
                    f"嘴型={face_details.mouth.openness:.2f}"
                )
        except Exception as e:
            logger.warning(f"面部细节检测失败: {e}")

    # --- Step 3: 骨骼绑定 ---
    rig = auto_rig(layers)

    # 如果检测到面部细节，更新相关参数
    if face_details:
        for param in rig.parameters:
            if param.id == "ParamEyeLOpen":
                param.default = face_details.left_eye.openness
            elif param.id == "ParamEyeROpen":
                param.default = face_details.right_eye.openness
            elif param.id == "ParamMouthOpenY":
                param.default = face_details.mouth.openness

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
    sam_badge = "+SAM" if sam_actually_used else ""
    face_badge = "+Face" if face_details else ""

    logger.info("=" * 50)
    logger.info("管线执行完毕！")
    logger.info(f"  输入:  {input_path}")
    logger.info(f"  输出:  {result}")
    logger.info(f"  模式:  {'SAM 像素级' if sam_actually_used else '椭圆近似'} {sam_badge} {face_badge}")
    logger.info(f"  图层:  {len(layers)} 个")
    logger.info(f"  参数:  {rig.metadata['total_parameters']} 个")
    logger.info(f"  纹理:  {atlas_size}x{atlas_size}")
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
  %(prog)s character.png --sam                  # 强制 SAM 像素级分割
  %(prog)s character.png --face                 # 启用面部细节检测
  %(prog)s character.png --sam --face --atlas-size 4096
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
    parser.add_argument("--sam", action="store_true", default=None,
                        help="强制使用 SAM 像素级分割")
    parser.add_argument("--no-sam", action="store_true",
                        help="禁用 SAM，使用椭圆近似")
    parser.add_argument("--face", action="store_true",
                        help="启用面部细节检测 (眼睛/嘴型/眉毛)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="详细日志输出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 处理 --sam / --no-sam
    use_sam = None
    if args.sam:
        use_sam = True
    elif getattr(args, 'no_sam', False):
        use_sam = False

    try:
        run_pipeline(
            input_path=args.input,
            output_dir=args.output,
            model_name=args.name,
            atlas_size=args.atlas_size,
            skip_bg_removal=args.skip_bg,
            use_sam=use_sam,
            use_face_details=args.face,
        )
    except Exception as e:
        logger.error(f"管线失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
