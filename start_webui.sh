#!/bin/bash
# ============================================
#  Live2D Image Transformer — WebUI 启动脚本
# ============================================
# 自动激活 venv、检测 LD_LIBRARY_PATH，启动 WebUI
#
# 用法:
#   bash start_webui.sh              # 默认端口 8000
#   bash start_webui.sh --port 9000  # 自定义端口
#   bash start_webui.sh --host 0.0.0.0 --port 8000  # 允许外部访问
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 默认参数
HOST="0.0.0.0"
PORT="8000"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --port|-p) PORT="$2"; shift 2 ;;
        --host|-h) HOST="$2"; shift 2 ;;
        *) echo "未知参数: $1"; shift ;;
    esac
done

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}[INFO]${NC} 虚拟环境已激活"
else
    echo -e "${YELLOW}[WARN]${NC} 未找到 venv，使用系统 Python"
fi

# 设置 LD_LIBRARY_PATH (WSL 环境需要)
if [ -d "lib" ]; then
    export LD_LIBRARY_PATH="./lib:$LD_LIBRARY_PATH"
    echo -e "${GREEN}[INFO]${NC} LD_LIBRARY_PATH 已设置 (WSL 适配)"
fi

# 检查关键依赖
python -c "from webui.app import app" 2>/dev/null || {
    echo -e "${YELLOW}[WARN]${NC} 依赖未安装，运行: bash setup.sh"
    exit 1
}

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   🎭 Live2D Image Transformer       ║${NC}"
echo -e "${CYAN}║   WebUI 启动中...                   ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════╣${NC}"
echo -e "${CYAN}║   地址: http://localhost:${PORT}        ║${NC}"
echo -e "${CYAN}║   API:  http://localhost:${PORT}/docs  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# 启动
python webui/app.py
