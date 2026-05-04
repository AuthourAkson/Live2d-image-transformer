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
   - 优先使用**离线/免费**方案 (rembg, MediaPipe, 本地模型)
   - 仅在必要时引入需要 API key 的服务
   - 在模块文档中明确标注每个依赖是否需要网络/付费

---

## 项目架构

```
live2d-image-transformer/
├── core/                        # 核心管线 (模块化，可独立 pip install)
│   ├── preprocessing/           # ① 背景移除 (rembg, U²-Net)
│   ├── segmentation/            # ② 图层分离 (MediaPipe Pose, 33关键点)
│   ├── rigging/                 # ③ 骨骼绑定 (Live2D 参数体系)
│   └── export/                  # ④ Live2D Cubism 4 导出
├── webui/                       # FastAPI Web 界面
│   ├── app.py                   # 后端 (上传→管线→ZIP下载)
│   ├── static/                  # 前端资源
│   └── templates/               # Jinja2 模板
├── examples/                    # CLI 脚本
├── requirements.txt
├── README.md                    # 项目总览
└── deepseek.md                  # ← 当前文件
```

## 技术栈

| 组件 | 技术选择 | 备注 |
|---|---|---|
| 背景移除 | rembg (U²-Net ONNX) | 离线可用，首次下载 176MB 模型 |
| 关键点检测 | MediaPipe Pose | 离线可用，33 点人体模型 |
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
[segmentation]   MediaPipe 关键点 → 14 部位 mask → 裁剪图层
  │
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

### ✅ 已完成 (v0.1.1)

- [x] **依赖安装与验证** — 所有 Python 依赖成功安装 (rembg, mediapipe, opencv, fastapi 等)
- [x] **MediaPipe API 迁移** — 从旧 `mediapipe.solutions` 迁移到新 `mediapipe.tasks` Task API
- [x] **MediaPipe 模型配置** — 下载 pose_landmarker_lite.task 模型至 `models/` 目录
- [x] **WSL 环境适配** — 编译 libGLESv2 库至 `lib/`，解决 GPU 依赖问题（软渲染 fallback）
- [x] **Starlette 1.0 适配** — 修复 `TemplateResponse` API 签名变更 (request 参数前置)
- [x] **管线验证** — 背景移除正常，MediaPipe 姿态检测正常启动
- [x] **WebUI 健康检查** — `/api/health` 返回正常

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

1. ✅ **端到端测试** — 用 tested_live2d.png 跑通完整管线: 14图层/12参数/Live2D导出
2. **像素级分割优化** — 集成 SAM (Segment Anything) 替代简单椭圆 mask
3. **面部细节** — 增加眉毛、瞳孔、口型变化参数  
4. **.moc3 生成** — 探索程序化生成 Live2D 二进制网格数据
5. **部署支持** — Docker 化，方便一键部署

### ⚠️ 已知问题

- 图层 mask 使用关键点椭圆近似，非像素级精确分割
- `.moc3` 仅为占位文件，需 Cubism Editor 生成正式版
- MediaPipe 对遮挡/非正面姿态的检测效果有限
- 纹理图集简单行式打包，图层过多可能浪费空间
- **新增**: MediaPipe 需要真实人物照片（绘制/合成图姿态检测精度不足）
- **新增**: 运行管线前需设置 `LD_LIBRARY_PATH=./lib:$LD_LIBRARY_PATH` (WSL环境)

---

## 面向 Agent 的操作指南

### 添加新核心模块

1. 在 `core/<module_name>/` 下创建 `.py` 文件
2. 编写 `README.md` (参考已有模块格式)
3. 更新 `core/__init__.py` 导出新 API
4. 更新 `requirements.txt` 添加新依赖
5. 在 `examples/basic_pipeline.py` 中集成
6. 在 WebUI 中集成新步骤
7. 更新本文档的「项目架构」和「当前进度」

### 测试运行

```bash
cd /mnt/d/live2d-image-transformer
pip install -r requirements.txt
python -c "from core.preprocessing import check_dependencies; print(check_dependencies())"
```

### 提交代码

```bash
cd /mnt/d/live2d-image-transformer
git add -A
git commit -m "<type>: <description>"
git push origin main
```

---

*最后更新: 2026-05-05 — v0.1.1 依赖安装 & API 适配完成*
