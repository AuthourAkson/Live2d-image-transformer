"""
背景移除模块 (Background Removal)
==================================
使用 rembg (ONNX-based) 自动扣图，移除图片背景，输出透明 PNG。

依赖: rembg, Pillow, onnxruntime
首次运行会自动下载 ONNX 模型 (~176MB, 缓存于 ~/.u2net/)。

API:
    remove_background(input_path: str, output_path: str = None) -> str
        → 返回输出文件路径

    remove_background_pil(image: Image.Image) -> Image.Image
        → 返回带透明通道的 PIL Image

示例:
    >>> from core.preprocessing.background_removal import remove_background
    >>> output = remove_background("input.jpg", "output.png")
    >>> print(f"Saved to: {output}")
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union
from PIL import Image

logger = logging.getLogger(__name__)

# 延迟导入，允许模块在 rembg 未安装时仍能被 import（仅调用时才报错）
_rembg_session = None


def _get_session():
    """获取或创建 rembg session（单例模式，避免重复加载模型）。"""
    global _rembg_session
    if _rembg_session is None:
        try:
            from rembg import new_session
            _rembg_session = new_session("u2net")
            logger.info("rembg session 已创建 (u2net 模型)")
        except ImportError:
            raise ImportError(
                "rembg 未安装，请运行: pip install rembg onnxruntime"
            )
    return _rembg_session


def remove_background_pil(image: Image.Image) -> Image.Image:
    """
    移除 PIL Image 的背景，返回 RGBA 图像。

    Args:
        image: 输入的 PIL Image (RGB 或 RGBA)

    Returns:
        RGBA 格式的 PIL Image，背景已透明

    Raises:
        ImportError: rembg 未安装
        ValueError: 输入图像无效
    """
    if image is None:
        raise ValueError("输入图像不能为 None")

    from rembg import remove

    # rembg 期望 RGB 输入
    if image.mode != "RGB":
        image = image.convert("RGB")

    session = _get_session()
    output = remove(image, session=session)
    return output


def remove_background(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None
) -> str:
    """
    移除图片背景，保存到文件。

    Args:
        input_path: 输入图片路径 (支持 jpg/png/webp 等常见格式)
        output_path: 输出路径，默认为同目录下的 <原名>_nobg.png

    Returns:
        输出文件的绝对路径

    Raises:
        FileNotFoundError: 输入文件不存在
        ImportError: rembg 未安装
    """
    input_path = Path(input_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_nobg.png"
    else:
        output_path = Path(output_path)

    logger.info(f"正在移除背景: {input_path.name}")

    image = Image.open(input_path)
    result = remove_background_pil(image)
    result.save(str(output_path), "PNG")

    logger.info(f"背景移除完成 → {output_path}")
    return str(output_path.resolve())


# 模块自检
def check_dependencies() -> bool:
    """检查模块依赖是否就绪。"""
    try:
        import rembg  # noqa: F401
        import onnxruntime  # noqa: F401
        return True
    except ImportError:
        return False
