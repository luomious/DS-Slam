#!/bin/bash
# ========================================================================
# DS-SLAM WSL2 编译脚本
# 在 Ubuntu 22.04 WSL2 中运行此脚本
# ========================================================================

set -e

echo "========================================"
echo "  DS-SLAM WSL2 编译"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/mnt/e/VSCode/VSCode-Workspace/DS-Slam"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[错误] 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi

# 编译 ORB-SLAM3 第三方库
echo -e "${GREEN}[1/4] 编译 DBoW2...${NC}"
cd "$PROJECT_DIR/orbslam3/Thirdparty/DBoW2"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j2

echo ""
echo -e "${GREEN}[2/4] 编译 g2o...${NC}"
cd "$PROJECT_DIR/orbslam3/Thirdparty/g2o"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j2

echo ""
echo -e "${GREEN}[3/4] 编译 ORB-SLAM3...${NC}"
cd "$PROJECT_DIR/orbslam3"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j2

echo ""
echo -e "${YELLOW}[4/4] 跳过 slam-system 编译（需要 ONNX Runtime Linux）${NC}"
echo "  下载 ONNX Runtime Linux 后运行:"
echo "  cd $PROJECT_DIR/slam-system && mkdir -p build && cd build"
echo "  cmake .. -DCMAKE_BUILD_TYPE=Release -DORT_ROOT=\$PROJECT_DIR/libs/onnxruntime-linux"
echo "  make -j2"

echo ""
echo "========================================"
echo "  编译完成！"
echo "========================================"
echo ""
echo "可执行文件位置:"
echo "  ORB-SLAM3: $PROJECT_DIR/orbslam3/build/Examples/RGB-D/rgbd_tum"
echo "  slam-system 库: $PROJECT_DIR/slam-system/build/*.a"
echo ""
echo "运行测试:"
echo "  cd $PROJECT_DIR/orbslam3/Examples/RGB-D"
echo "  ./rgbd_tum ../../Vocabulary/ORBvoc.txt TUM1.yaml /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz/associations/rgbd_dataset_freiburg1_xyz.txt"
echo ""
