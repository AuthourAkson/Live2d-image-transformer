# 预处理模块 (Preprocessing)

## 功能
- **背景移除**: 使用 rembg (U²-Net ONNX 模型) 自动去除图片背景
- 输出带透明通道 (RGBA) 的 PNG 图片

## 依赖
| 包 | 版本 | 用途 |
|---|---|---|
| rembg | >=2.0.0 | 背景移除核心算法 |
| onnxruntime | >=1.15.0 | ONNX 模型运行 |
| Pillow | >=10.0.0 | 图像 I/O |

## API 参考

### `remove_background(input_path, output_path=None) -> str`
从文件中读取图片，移除背景后保存。

```python
from core.preprocessing import remove_background

# 自动命名输出文件 (input_nobg.png)
output = remove_background("photo.jpg")

# 指定输出路径
output = remove_background("photo.jpg", "output/photo_clean.png")
```

### `remove_background_pil(image: Image.Image) -> Image.Image`
直接处理 PIL Image 对象（适合 pipeline 内部调用）。

```python
from PIL import Image
from core.preprocessing import remove_background_pil

img = Image.open("photo.jpg")
clean = remove_background_pil(img)  # 返回 RGBA Image
```

## 技术细节
- 模型: U²-Net (u2net)，首次运行自动下载 (~176MB)
- 模型缓存位置: `~/.u2net/`
- 输入格式: 支持 Pillow 可打开的所有格式 (JPG/PNG/WEBP/BMP 等)
- 输出格式: PNG (RGBA)

## 注意事项
- 首次运行需要网络连接下载模型
- 复杂背景 (如杂乱的植物、网格图案) 可能残留边缘
- 建议输入分辨率 ≥ 512px 以获得最佳效果
