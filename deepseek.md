# DeepSeek / AI Agent 协作文件

> 本文档供 AI Agent 快速理解项目架构、规则和当前进度。
> 人类开发者也可阅读以对齐认知。

---

## 项目定位

**Live2D Image Transformer** — 输入一张人物图片，自动扣图、分层、绑骨骼，生成最基础的 Live2D 可动模型。

目标：让没有 Live2D 经验的用户也能为角色赋予"动起来"的能力。

---

## 协作规则

1. **工作目录**: `/mnt/d/live2d-image-transformer/` (Windows D:\live2d-image-transformer)
2. **仓库地址**: https://github.com/AuthourAkson/Live2d-image-transformer.git
3. **提交策略**: 每次关键功能更新后，**必须测试运行**，通过后立即 `git commit` + `git push`
4. **模块化要求**: 核心功能放在 `core/` 下，每个子模块有独立 `README.md` 文档，便于被其他项目导入
5. **文档要求**: 项目根目录维护 `README.md` (项目总览) 和 `deepseek.md` (本文档，Agent 规则+进度)
6. **中文思考模式**: 项目架构和方向用中文思维理解，代码注释和文档优先中文
7. **用户操作提示**: 当某功能需要 API key 或第三方平台支持时，主动暂停并向用户说明需要的具体操作
8. **依赖优先级**: 
   - 优先使用**离线/免费**方案 (rembg, MediaPipe, SAM, 本地模型)
   - 仅在必要时引入需要 API key 的服务
   - 在模块文档中明确标注每个依赖是否需要网络/付费
9. **测试图片**: 测试时使用 `assets/` 文件夹下的图片
   - `assets/tested_live2d.png` — 真人照片，适合 MediaPipe 姿态检测
   - `assets/gura.png` — 二次元角色，MediaPipe 无法检测（需 SAM 直接分割）
10. **一键启动**: 提供 `setup.sh` (安装) 和 `start_webui.sh`/`start_webui.bat` (启动)

---

## 项目架构

```
live2d-image-transformer/
├── core/                        # 核心管线 (模块化，可独立 pip install)
│   ├── __init__.py              # 统一导出 (v0.2.0)
│   ├── preprocessing/           # ① 背景移除 (rembg, U²-Net)
│   ├── segmentation/            # ② 图层分离
│   │   ├── layer_separation.py  #    椭圆近似 (快速模式)
│   │   ├── sam_segmentation.py  #    SAM 像素级 (精确模式) ← v0.2 新增
│   │   └── face_details.py      #    面部细节检测 ← v0.2 新增
│   ├── rigging/                 # ③ 骨骼绑定 (Live2D 参数体系)
│   └── export/                  # ④ Live2D Cubism 4 导出
├── webui/                       # FastAPI Web 界面
│   ├── app.py                   # 后端 (支持 SAM + 面部细节)
│   ├── static/                  # 前端资源
│   └── templates/               # Jinja2 模板
├── examples/                    # CLI 脚本
│   └── basic_pipeline.py        # 管线脚本 (--sam / --face / --no-sam)
├── models/                      # AI 模型文件
│   ├── pose_landmarker_lite.task    # MediaPipe Pose (5.7MB)
│   ├── sam_vit_b_01ec64.pth         # SAM 分割模型 (358MB)
│   └── face_landmarker_v2.task      # Face Landmarker (可选)
├── assets/                      # 测试图片
│   ├── tested_live2d.png        # 真人测试图
│   └── gura.png                 # 二次元测试图
├── setup.sh                     # 一键安装脚本 ← v0.2 新增
├── start_webui.sh               # Linux/WSL 启动脚本 ← v0.2 新增
├── start_webui.bat              # Windows 启动脚本 ← v0.2 新增
├── requirements.txt
├── README.md                    # 项目总览
└── deepseek.md                  # ← 当前文件
```

## 技术栈

| 组件 | 技术选择 | 备注 |
|---|---|---|
| 背景移除 | rembg (U²-Net ONNX) | 离线可用，首次下载 176MB 模型 |
| 关键点检测 | MediaPipe Pose | 离线可用，33 点人体模型 |
| 像素级分割 | SAM (vit_b) | 离线可用，358MB 模型，替代椭圆近似 |
| 面部细节 | MediaPipe Face Landmarker | 478 点面部网格，眼睛/嘴型/眉毛追踪 |
| 图像处理 | OpenCV + Pillow | 纯离线 |
| Web 框架 | FastAPI + Jinja2 | 轻量、异步 |
| 前端 | 原生 HTML/CSS/JS | 零构建步骤 |
| 导出格式 | Live2D Cubism 4 JSON | 兼容 SDK 4.x |

## 管线流程

```
Input Image
  │
  ▼
[preprocessing]  rembg 去背景 → RGBA PNG
  │
  ▼
[segmentation]   MediaPipe 关键点 → SAM 像素级 mask → 14 部位图层
  │  (可选)       Face Landmarker → 眼睛开合/嘴型/眉毛参数
  ▼
[rigging]        图层 → 参数绑定 + 层级关系
  │
  ▼
[export]         图层打包纹理图集 → .model3.json + .cdi3.json + .physics3.json
  │
  ▼
Output: Live2D Cubism 4 模型包
```

---

## 当前进度

### ✅ 已完成 (v0.2.0)

- [x] **SAM 像素级分割** — 集成 Meta SAM (vit_b)，用边界框+关键点 prompt 生成精确 mask
- [x] **面部细节检测** — MediaPipe Face Landmarker 提取眼睛开合、嘴型、眉毛参数
- [x] **智能模式切换** — 管线自动检测 SAM 模型，无模型时回退椭圆近似
- [x] **一键启动脚本** — `setup.sh` (安装) + `start_webui.sh/.bat` (启动)
- [x] **面部参数绑定** — 眼睛开合/嘴型参数从面部检测结果自动填入骨骼绑定

### ✅ 已完成 (v0.1.1)

- [x] **依赖安装与验证** — 所有 Python 依赖成功安装 (rembg, mediapipe, opencv, fastapi 等)
- [x] **MediaPipe API 迁移** — 从旧 `mediapipe.solutions` 迁移到新 `mediapipe.tasks` Task API
- [x] **MediaPipe 模型配置** — 下载 pose_landmarker_lite.task 模型至 `models/` 目录
- [x] **WSL 环境适配** — 编译 libGLESv2 库至 `lib/`，解决 GPU 依赖问题（软渲染 fallback）
- [x] **管线验证** — 14 图层 / 12 参数 / 完整 Live2D 导出

### ✅ 已完成 (v0.1.0)

- [x] 项目结构搭建
- [x] `core/preprocessing/` — 背景移除模块 + README
- [x] `core/segmentation/` — 图层分离模块 (14部位) + README
- [x] `core/rigging/` — 自动骨骼绑定 + README
- [x] `core/export/` — Live2D Cubism 4 格式导出 + README
- [x] `examples/basic_pipeline.py` — 命令行管线脚本
- [x] `webui/` — FastAPI Web 界面 (上传/处理/下载)
- [x] `README.md` — 项目总览文档
- [x] `deepseek.md` — Agent 协作文件

### 🔜 下一步计划

1. **精确实例分割** — 改进 SAM prompt 策略（负样本点 + 多 mask 选择）
2. **二次元角色支持** — SAM 直接分割（跳过 MediaPipe），支持动漫/插画角色
3. **.moc3 生成** — 探索程序化生成 Live2D 二进制网格数据
4. **动画预览** — WebUI 内置 Live2D Viewer 实时预览
5. **Docker 部署** — Dockerfile + docker-compose 一键部署
6. **多角度支持** — 3D 视角校正，从单张图推断多角度

### ⚠️ 已知问题

- ~~图层 mask 使用关键点椭圆近似，非像素级精确分割~~ → **v0.2 已用 SAM 解决**
- `.moc3` 仅为占位文件，需 Cubism Editor 生成正式版
- MediaPipe 对遮挡/非正面姿态的检测效果有限
- MediaPipe Pose 无法检测二次元角色（需用 SAM 直接分割）
- 纹理图集简单行式打包，图层过多可能浪费空间
- 运行管线前需设置 `LD_LIBRARY_PATH=./lib:$LD_LIBRARY_PATH` (WSL环境)
- SAM 首次加载需 10-30 秒（加载 358MB 模型 + CPU 推理）

---

## 面向 Agent 的操作指南

### 快速测试

```bash
cd /mnt/d/live2d-image-transformer

# 椭圆近似 (快速)
LD_LIBRARY_PATH="./lib:$LD_LIBRARY_PATH" venv/bin/python examples/basic_pipeline.py assets/tested_live2d.png -o ./output -n test_model --no-sam

# SAM 像素级 (精确)
LD_LIBRARY_PATH="./lib:$LD_LIBRARY_PATH" venv/bin/python examples/basic_pipeline.py assets/tested_live2d.png -o ./output -n sam_model --sam

# SAM + 面部细节
LD_LIBRARY_PATH="./lib:$LD_LIBRARY_PATH" venv/bin/python examples/basic_pipeline.py assets/tested_live2d.png -o ./output -n full_model --sam --face
```

### WebUI 启动

```bash
# Linux/WSL
bash start_webui.sh

# Windows
start_webui.bat
```

### 添加新核心模块

1. 在 `core/<module_name>/` 下创建 `.py` 文件
2. 编写 `README.md` (参考已有模块格式)
3. 更新 `core/__init__.py` 导出新 API
4. 更新 `requirements.txt` 添加新依赖
5. 在 `examples/basic_pipeline.py` 中集成
6. 在 WebUI 中集成新步骤
7. 更新本文档的「项目架构」和「当前进度」

### 提交代码

```bash
cd /mnt/d/live2d-image-transformer
git add -A
git commit -m "<type>: <description>"
git push origin main
```

---

*最后更新: 2026-05-05 — v0.2.0 SAM 像素级分割 + 面部细节 + 一键脚本*
