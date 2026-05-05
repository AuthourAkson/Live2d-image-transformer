# 🎭 Live2D Image Transformer

> 上传一张图片 → 自动扣图 → 分层 → 绑骨骼 → 生成 Live2D 可动模型

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Live2D](https://img.shields.io/badge/Live2D-Cubism%204-orange.svg)](https://www.live2d.com/)
[![SAM](https://img.shields.io/badge/SAM-Pixel_Segmentation-red.svg)](https://segment-anything.com/)

## 📸 效果预览

```
  输入图片                处理管线                   输出
  ┌────────┐     ┌──────┬──────┬──────┐     ┌──────────────┐
  │        │     │ 扣图 │ 分层 │ 骨骼 │     │ .model3.json │
  │  🧍    │ ──▶ │  →   │  →   │  →   │ ──▶ │ texture.png  │
  │        │     │      │ SAM  │      │     │ .moc3        │
  └────────┘     └──────┴──────┴──────┘     └──────────────┘
```

## ✨ 新功能 (v0.2.0)

- 🔬 **SAM 像素级分割** — Meta Segment Anything 模型，精确提取身体部位（替代椭圆近似）
- 😊 **面部细节检测** — 眼睛开合、嘴型、眉毛位置自动识别
- 🚀 **一键脚本** — `bash setup.sh` 安装，`bash start_webui.sh` 启动
- 🧠 **智能模式** — 自动检测 SAM 模型，有则用精确模式，无则回退快速模式

## 🏗 项目架构

```
live2d-image-transformer/
├── core/                        # 核心模块（模块化、可独立导入）
│   ├── __init__.py              # 统一导出 API
│   ├── preprocessing/           # ① 预处理
│   ├── segmentation/            # ② 图层分离
│   │   ├── layer_separation.py  #    椭圆近似 (快速)
│   │   ├── sam_segmentation.py  #    SAM 像素级 (精确)
│   │   └── face_details.py      #    面部细节检测
│   ├── rigging/                 # ③ 骨骼绑定
│   └── export/                  # ④ Live2D 导出
├── webui/                       # Web 界面
├── examples/                    # CLI 脚本
├── models/                      # AI 模型
├── assets/                      # 测试图片
├── setup.sh                     # 一键安装
├── start_webui.sh               # 启动脚本 (Linux/WSL)
├── start_webui.bat              # 启动脚本 (Windows)
├── requirements.txt
└── README.md
```

## 🚀 快速开始

### 1. 一键安装

```bash
# 基本安装 (背景移除 + 姿态检测)
bash setup.sh

# 完整安装 (含 SAM 358MB 模型)
bash setup.sh --all
```

### 2. 命令行使用

```bash
# 快速模式 (椭圆近似)
python examples/basic_pipeline.py assets/tested_live2d.png

# SAM 像素级精确分割
python examples/basic_pipeline.py assets/tested_live2d.png --sam

# SAM + 面部细节
python examples/basic_pipeline.py assets/tested_live2d.png --sam --face

# 指定输出目录和模型名
python examples/basic_pipeline.py my_character.png -o ./output -n my_model
```

### 3. WebUI 使用

```bash
bash start_webui.sh    # Linux / WSL
start_webui.bat        # Windows
```

打开 http://localhost:8000 ，上传图片即可。

### 4. 作为库导入

```python
from core import remove_background, separate_layers, auto_rig, export_live2d

# 快速模式 (椭圆近似)
clean_path = remove_background("input.jpg")
layers, size = separate_layers(clean_path)
rig = auto_rig(layers)
export_live2d(layers, rig, "./output", "my_model")

# SAM 精确模式
from core.segmentation.sam_segmentation import separate_layers_sam
layers, size = separate_layers_sam(clean_path)
```

## 🔧 处理管线

| 步骤 | 模块 | 输入 | 输出 | 技术 |
|---|---|---|---|---|
| ① 背景移除 | `preprocessing` | 原始图片 | RGBA 透明 PNG | rembg (U²-Net) |
| ② 图层分离 | `segmentation` | 透明 PNG | 14 个身体图层 | MediaPipe Pose + SAM |
| ②.5 面部细节 | `segmentation` | 透明 PNG | 眼睛/嘴型/眉毛参数 | MediaPipe Face Landmarker |
| ③ 骨骼绑定 | `rigging` | 图层列表 | 12 个骨骼参数 + 层级 | 自动算法 |
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

### 分割模式对比

| 特性 | 椭圆近似 | SAM 像素级 |
|---|---|---|
| 速度 | ⚡ 快速 (~5s) | 🐢 较慢 (~30s) |
| 精度 | 粗略 | 像素级精确 |
| 模型大小 | 无需额外模型 | 358MB |
| 适用场景 | 快速原型 | 生产质量 |

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
- **SAM 模型** (358MB) 需手动下载：`bash setup.sh --with-sam`
- `.moc3` 文件为**占位文件**，需用 [Live2D Cubism Editor](https://www.live2d.com/download/) 打开 `.model3.json` 后生成正式版
- 建议输入**正面或半侧面、姿势自然、光照均匀**的人物图片
- **WSL 用户**：启动脚本已自动设置 `LD_LIBRARY_PATH`

## 🛣 路线图

- [x] 背景移除 (rembg)
- [x] 14 部位图层分离 (MediaPipe Pose)
- [x] SAM 像素级精确分割 ← v0.2
- [x] 面部细节参数 (眼睛/嘴型/眉毛) ← v0.2
- [x] 一键安装和启动脚本 ← v0.2
- [x] 自动骨骼绑定
- [x] Live2D Cubism 4 格式导出
- [x] WebUI 界面
- [ ] 二次元角色支持 (SAM 直接分割)
- [ ] 自动网格生成 + .moc3 二进制导出
- [ ] 动画预览播放器
- [ ] Docker 部署
- [ ] 3D 视角校正 (单图转多角度)

## 🤝 贡献

欢迎提 Issue 和 PR。开发前请阅读 `deepseek.md` 了解项目规则。

## 📄 许可

MIT License — 详见 [LICENSE](LICENSE)
