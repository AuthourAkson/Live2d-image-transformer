# Live2D 导出模块 (Export)

## 功能
- 将图层 + 骨骼绑定结果导出为 Live2D Cubism 4 兼容格式
- 生成纹理图集 (texture atlas)、model3.json、cdi3.json、physics3.json

## 依赖
无外部依赖，仅使用 Python 标准库 + Pillow。

## 输出文件结构
```
output_dir/
├── model.model3.json          # 模型定义 (参数、纹理引用、碰撞区)
├── model.cdi3.json            # 显示信息 (参数分组)
├── model.physics3.json        # 物理模拟 (基础模板)
├── model.moc3                 # 占位文件 (moc3 为二进制格式)
├── model.4096/
│   └── texture_00.png         # 纹理图集
├── preview_head.png            # 图层预览 (调试用)
├── preview_torso.png
└── ...
```

## API 参考

### `export_live2d(layers, rig_result, output_dir, model_name="model", atlas_size=2048) -> str`
导出完整 Live2D 模型。

```python
from core.export import export_live2d

output_path = export_live2d(
    layers=layers,
    rig_result=rig,
    output_dir="./output/my_model",
    model_name="my_character",
    atlas_size=2048,
)
print(f"模型已导出到: {output_path}")
```

## 格式说明

### .model3.json
Live2D Cubism 3+ 的模型描述文件，包含：
- `Version`: 格式版本 (3)
- `FileReferences`: 引用其他文件 (Moc, Textures, Physics, DisplayInfo)
- `Groups`: 参数分组
- `HitAreas`: 碰撞检测区域

### .moc3
二进制网格/骨骼数据文件。**本项目生成的是占位文件** — 完整 .moc3 需用 Live2D Cubism Editor 生成。
工作流: 加载 .model3.json → 在 Editor 中调整 → 导出 .moc3

### .cdi3.json
Cubism Display Info 3 — 参数显示名称与分组。

### .physics3.json
物理模拟设置 (重力、风力、摆动物理)。

## 在 Live2D Viewer 中加载
1. 将整个输出目录复制到 Live2D 项目
2. 在 Cubism Editor 中打开 .model3.json
3. 调整网格和变形器
4. 导出 .moc3

## 注意事项
- 纹理图集默认 2048×2048，图层过多可能溢出 (会打印警告)
- 若溢出，增大 `atlas_size` 参数 (如 4096)
- .moc3 是占位文件，不能直接用于 SDK 加载
