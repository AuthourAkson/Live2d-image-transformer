#!/bin/bash
# ============================================
#  Live2D Image Transformer — 一键安装脚本
# ============================================
# 自动检测环境、安装依赖、下载模型
# 支持: Ubuntu/Debian, WSL, macOS
#
# 用法:
#   bash setup.sh
#   bash setup.sh --with-sam    # 同时下载 SAM 模型 (358MB)
#   bash setup.sh --with-face   # 同时下载 Face Landmarker 模型
#   bash setup.sh --all         # 下载所有模型 (~400MB)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step()  { echo -e "\n${CYAN}========================================${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}========================================${NC}"; }

DOWNLOAD_SAM=false
DOWNLOAD_FACE=false

for arg in "$@"; do
    case $arg in
        --with-sam|--all) DOWNLOAD_SAM=true ;;
        --with-face|--all) DOWNLOAD_FACE=true ;;
        --help|-h)
            echo "用法: bash setup.sh [选项]"
            echo "  --with-sam   下载 SAM 模型 (358MB)"
            echo "  --with-face  下载 Face Landmarker 模型"
            echo "  --all        下载所有模型"
            exit 0
            ;;
    esac
done

step "1/5 检测 Python 环境"

if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    error "未找到 Python，请安装 Python 3.10+"
fi

PY_VER=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
info "Python $PY_VER 已就绪"

step "2/5 创建虚拟环境"

if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    info "虚拟环境已创建"
else
    info "虚拟环境已存在"
fi

# 激活虚拟环境
source venv/bin/activate

step "3/5 安装 Python 依赖"

pip install --upgrade pip -q
pip install -r requirements.txt
info "依赖安装完成"

step "4/5 下载 AI 模型"

mkdir -p models

# MediaPipe Pose 模型 (已内置在 requirements 中，但确认存在)
if [ ! -f "models/pose_landmarker_lite.task" ]; then
    info "下载 MediaPipe Pose 模型..."
    wget -q --show-progress -O models/pose_landmarker_lite.task \
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task" || \
        warn "Pose 模型下载失败，将使用内置模型"
fi

# SAM 模型
if [ "$DOWNLOAD_SAM" = true ]; then
    if [ ! -f "models/sam_vit_b_01ec64.pth" ]; then
        info "下载 SAM 模型 (358MB)..."
        wget -q --show-progress -O models/sam_vit_b_01ec64.pth \
            "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth" || \
            warn "SAM 模型下载失败，将使用椭圆近似分割"
    else
        info "SAM 模型已存在"
    fi
fi

# Face Landmarker 模型
if [ "$DOWNLOAD_FACE" = true ]; then
    if [ ! -f "models/face_landmarker_v2_with_blendshapes.task" ]; then
        info "下载 Face Landmarker 模型..."
        wget -q --show-progress -O models/face_landmarker_v2_with_blendshapes.task \
            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task" || \
            warn "Face Landmarker 模型下载失败"
    else
        info "Face Landmarker 模型已存在"
    fi
fi

step "5/5 验证安装"

# 检查核心依赖
$PYTHON -c "
from core.preprocessing import check_dependencies as c1
from core.segmentation import check_dependencies as c2
print(f'  rembg (背景移除): {\"✅\" if c1() else \"❌\"}')
print(f'  mediapipe (姿态检测): {\"✅\" if c2() else \"❌\"}')
" || warn "核心依赖检查失败"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   🎭 安装完成！                      ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                      ║${NC}"
echo -e "${GREEN}║  启动 WebUI:                         ║${NC}"
echo -e "${GREEN}║    bash start_webui.sh               ║${NC}"
echo -e "${GREEN}║                                      ║${NC}"
echo -e "${GREEN}║  命令行使用:                         ║${NC}"
echo -e "${GREEN}║    python examples/basic_pipeline.py ║${NC}"
echo -e "${GREEN}║         assets/tested_live2d.png     ║${NC}"
echo -e "${GREEN}║                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
