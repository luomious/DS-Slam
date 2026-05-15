#!/bin/bash
# ========================================================================
# DS-SLAM WSL2 环境配置脚本
# 在 Ubuntu 22.04 WSL2 中运行此脚本
# ========================================================================

set -e

echo "========================================"
echo "  DS-SLAM WSL2 环境配置"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查是否在 WSL2 中运行
if [ ! -d "/mnt/c" ]; then
    echo -e "${RED}[错误] 此脚本应在 WSL2 中运行${NC}"
    exit 1
fi

# 项目路径
PROJECT_DIR="/mnt/e/VSCode/VSCode-Workspace/DS-Slam"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[错误] 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}[1/6] 更新系统包...${NC}"
sudo apt update && sudo apt upgrade -y

echo ""
echo -e "${GREEN}[2/6] 安装编译工具链...${NC}"
sudo apt install -y build-essential cmake git pkg-config

echo ""
echo -e "${GREEN}[3/6] 安装 OpenCV...${NC}"
sudo apt install -y libopencv-dev

echo ""
echo -e "${GREEN}[4/6] 安装 Eigen3...${NC}"
sudo apt install -y libeigen3-dev

echo ""
echo -e "${GREEN}[5/7] 安装 Pangolin 依赖...${NC}"
sudo apt install -y libglew-dev libgl1-mesa-dev libegl1-mesa-dev \
    libwayland-dev libxkbcommon-dev libglfw3-dev \
    libpng-dev libjpeg-dev libopenexr-dev libtiff-dev

echo ""
echo -e "${GREEN}[6/7] 安装 Boost...${NC}"
sudo apt install -y libboost-all-dev

echo ""
echo -e "${GREEN}[7/7] 安装 Python 环境...${NC}"
sudo apt install -y python3.10 python3.10-dev python3-pip python3-venv libcurl4-openssl-dev

echo ""
echo "========================================"
echo "  环境配置完成！"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 编译 ORB-SLAM3: cd $PROJECT_DIR/orbslam3 && mkdir -p build && cd build && cmake .. && make -j\$(nproc)"
echo "  2. 编译 slam-system: cd $PROJECT_DIR/slam-system && mkdir -p build && cd build && cmake .. && make -j\$(nproc)"
echo "  3. 安装 Python YOLO 环境: cd $PROJECT_DIR && python3 -m venv venv && source venv/bin/activate && pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 && pip install ultralytics onnx onnxruntime-gpu opencv-python numpy"
echo ""
echo "验证 CUDA 可用: python3 -c \"import torch; print('CUDA:', torch.cuda.is_available())\""
echo ""
