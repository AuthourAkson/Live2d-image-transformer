# 🎭 Live2D Image Transformer

> 上传一张图片 → 自动扣图 → 分层 → 绑骨骼 → 生成 Live2D 可动模型

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Live2D](https://img.shields.io/badge/Live2D-Cubism%204-orange.svg)](https://www.live2d.com/)

## 📸 效果预览

```
  输入图片                处理管线                   输出
  ┌────────┐     ┌──────┬──────┬──────┐     ┌──────────────┐
  │        │     │ 扣图 │ 分层 │ 骨骼 │     │ .model3.json │
  │  🧍    │ ──▶ │  →   │  →   │  →   │ ──▶ │ texture.png  │
  │        │     │      │      │      │     │ .moc3        │
  └────────┘     └──────┴──────┴──────┘     └──────────────┘
```

## 🏗 项目架构

```
live2d-image-transformer/
├── core/                        # 核心模块（模块化、可独立导入）
│   ├── __init__.py              # 统一导出 API
│   ├── preprocessing/           # ① 预处理
│   │   ├── README.md            #    模块文档
│   │   └── background_removal.py
│   ├── segmentation/            # ② 图层分离
│   │   ├── README.md
│   │   └── layer_separation.py
│   ├── rigging/                 # ③ 骨骼绑定
│   │   ├── README.md
│   │   └── auto_rigging.py
│   └── export/                  # ④ Live2D 导出
│       ├── README.md
│       └── live2d_export.py
├── webui/                       # Web 界面
│   ├── app.py                   # FastAPI 后端
│   ├── static/                  # CSS / JS
│   └── templates/               # HTML 模板
├── examples/                    # 使用示例
│   └── basic_pipeline.py        # 命令行管线脚本
├── requirements.txt
├── README.md                    # ← 你在这里
└── deepseek.md                  # Agent 协作规则与进度
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 命令行使用

```bash
# 基本用法
python examples/basic_pipeline.py my_character.png

# 指定输出目录和模型名
python examples/basic_pipeline.py my_character.png -o ./output -n my_model

# 如果图片已经扣过背景
python examples/basic_pipeline.py character_nobg.png --skip-bg
```

### 3. WebUI 使用

```bash
python webui/app.py
# 或
uvicorn webui.app:app --host 0.0.0.0 --port 8000 --reload
```

打开 http://localhost:8000 ，上传图片即可。

### 4. 作为库导入

```python
from core import remove_background, separate_layers, auto_rig, export_live2d

# Step 1: 背景移除
clean_path = remove_background("input.jpg")

# Step 2: 图层分离
layers, size = separate_layers(clean_path)

# Step 3: 骨骼绑定
rig = auto_rig(layers)

# Step 4: 导出
export_live2d(layers, rig, "./output", "my_model")
```

## 🔧 处理管线

| 步骤 | 模块 | 输入 | 输出 | 依赖 |
|---|---|---|---|---|
| ① 背景移除 | `preprocessing` | 原始图片 | RGBA 透明 PNG | rembg (U²-Net) |
| ② 图层分离 | `segmentation` | 透明 PNG | 14 个身体图层 | MediaPipe Pose |
| ③ 骨骼绑定 | `rigging` | 图层列表 | 骨骼参数 + 层级 | 无 (纯算法) |
| ④ 导出 | `export` | 图层 + 骨骼 | .model3.json + 纹理 | Pillow |

### 图层分离详情

```
head              ← 头部 (眼睛、口型参数)
 └─ torso         ← 躯干 (呼吸、身体角度)
      ├─ left_upper_arm  → left_forearm  → left_hand
      ├─ right_upper_arm → right_forearm → right_hand
      ├─ left_thigh      → left_leg      → left_foot
      └─ right_thigh     → right_leg     → right_foot
```

## 📦 输出格式

导出兼容 **Live2D Cubism 4** 格式：

```
output/model/
├── model.model3.json        # 模型定义
├── model.cdi3.json          # 显示信息
├── model.physics3.json      # 物理模拟
├── model.moc3               # 占位（需 Cubism Editor 生成正式版）
└── model.4096/
    └── texture_00.png       # 纹理图集
```

## ⚠️ 注意事项

- **首次运行** rembg 和 MediaPipe 会自动下载模型文件 (~226MB 总计)，需要网络连接
- `.moc3` 文件为**占位文件**，需用 [Live2D Cubism Editor](https://www.live2d.com/download/) 打开 `.model3.json` 后生成正式版
- 建议输入**正面或半侧面、姿势自然、光照均匀**的人物图片
- 图层分离基于关键点 mask，非像素级精确分割。如需精确分割，可替换为 SAM 模型

## 🛣 路线图

- [x] 背景移除 (rembg)
- [x] 14 部位图层分离 (MediaPipe Pose)
- [x] 自动骨骼绑定
- [x] Live2D Cubism 4 格式导出
- [x] WebUI 界面
- [ ] 集成 SAM 实现像素级精确分割
- [ ] 面部细节参数 (眉毛、睫毛、瞳孔追踪)
- [ ] 自动网格生成 + .moc3 二进制导出
- [ ] 3D 视角校正 (单图转多角度)
- [ ] 动画预览播放器

## 🤝 贡献

欢迎提 Issue 和 PR。开发前请阅读 `deepseek.md` 了解项目规则。

## 📄 许可

MIT License — 详见 [LICENSE](LICENSE)
