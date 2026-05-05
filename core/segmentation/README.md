# 图层分离模块 (Segmentation / Layer Separation)

## 功能
- 基于 MediaPipe Pose 检测人体 33 个关键点
- 将人物自动分离为 14 个独立图层：
  - head (头部)
  - torso (躯干)
  - 左/右臂各三段: upper_arm, forearm, hand
  - 左/右腿各三段: thigh, leg, foot
- 每个图层包含 RGBA 图像、mask、边界框、关节 pivot

## 依赖
| 包 | 版本 | 用途 |
|---|---|---|
| mediapipe | >=0.10.0 | 人体姿态关键点检测 |
| opencv-python | >=4.8.0 | 图像处理、形态学操作 |
| numpy | >=1.24.0 | 数组计算 |
| Pillow | >=10.0.0 | 图像 I/O |

## API 参考

### `separate_layers(image_path, *, return_original_size=True, min_visibility=0.3) -> tuple`
对输入图片进行图层分离。

```python
from core.segmentation import separate_layers

# 从文件
layers, original_size = separate_layers("character.png")

# 从 PIL Image
from PIL import Image
img = Image.open("character.png")
layers, size = separate_layers(img)

# 访问图层
for layer in layers:
    print(f"{layer.name}: {layer.bbox}, parent={layer.parent}")
    layer.image.save(f"{layer.name}.png")
```

### `LayerInfo` 数据类
```python
@dataclass
class LayerInfo:
    name: str           # 图层名称
    image: Image.Image  # RGBA 裁剪图像
    bbox: tuple         # 在原图中的边界框 (x, y, w, h)
    landmark: tuple     # 部位中心坐标
    parent: str         # 父图层 (用于骨骼层级)
    pivot: tuple        # 旋转轴心 (相对于裁剪图像)
```

## 技术细节
- 使用 MediaPipe Pose Landmarker 的 33 点人体模型
- 关键点可见度阈值: `min_visibility=0.3` (可调)
- 基于关键点生成椭圆 mask + 形态学闭运算填充
- 扩展系数 (expand_ratio) 控制裁剪边界框的宽松程度

## 局限性 & 改进方向
- 当前使用简单椭圆 mask，非像素级精确分割
- **建议**: 可集成 SAM (Segment Anything) 获得更精确的边界
- **建议**: 可增加服装/头发等软体部件的分离
- 多人场景暂不支持，只处理检测到的第一人

## 注意事项
- MediaPipe 首次运行自动下载模型 (~50MB)
- 需要图片中人物清晰可见、姿态自然
- 遮挡严重时关键点检测可能失败
