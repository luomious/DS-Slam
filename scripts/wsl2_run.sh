#!/bin/bash
# ========================================================================
# DS-SLAM WSL2 运行脚本
# 在 Ubuntu 22.04 WSL2 中运行此脚本
# 用法: ./wsl2_run.sh [数据集路径] [关联文件] [ONNX模型]
# ========================================================================

set -e

echo "========================================"
echo "  DS-SLAM WSL2 运行"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/mnt/e/VSCode/VSCode-Workspace/DS-Slam"

# 检查参数
if [ $# -lt 1 ]; then
    echo -e "${RED}用法: $0 <数据集路径> [关联文件] [ONNX模型]${NC}"
    echo ""
    echo "示例:"
    echo "  $0 /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz"
    echo "  $0 /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_xyz /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_xyz/associations/rgbd_dataset_freiburg3_walking_xyz.txt /mnt/e/VSCode/VSCode-Workspace/DS-Slam/segmentation/onnx/yolo11n_seg_v2.onnx"
    exit 1
fi

DATASET=$1
ASSOC=${2:-"$DATASET/associations/rgbd_dataset_freiburg1_xyz.txt"}
ONNX_MODEL=${3:-"$PROJECT_DIR/segmentation/onnx/yolo11n_seg_v2.onnx"}

# 检查关键文件
if [ ! -f "$PROJECT_DIR/orbslam3/build/Examples/RGB-D/rgbd_tum" ]; then
    echo -e "${RED}[错误] 未找到编译产物: $PROJECT_DIR/orbslam3/build/Examples/RGB-D/rgbd_tum${NC}"
    echo "请先运行: ./wsl2_build.sh"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/orbslam3/Vocabulary/ORBvoc.txt" ]; then
    echo -e "${RED}[错误] 未找到词汇表文件${NC}"
    exit 1
fi

if [ ! -d "$DATASET" ]; then
    echo -e "${RED}[错误] 数据集目录不存在: $DATASET${NC}"
    exit 1
fi

# 确定配置文件
CONFIG="TUM1.yaml"
if echo "$DATASET" | grep -qi "freiburg2"; then
    CONFIG="TUM2.yaml"
elif echo "$DATASET" | grep -qi "freiburg3"; then
    CONFIG="TUM3.yaml"
fi

echo -e "${GREEN}[配置] 使用 $CONFIG${NC}"
echo -e "${GREEN}[数据集] $DATASET${NC}"
echo -e "${GREEN}[关联] $ASSOC${NC}"
if [ -f "$ONNX_MODEL" ]; then
    echo -e "${GREEN}[ONNX] $ONNX_MODEL${NC}"
fi
echo ""

# 运行 SLAM
cd "$PROJECT_DIR/orbslam3/Examples/RGB-D"

echo -e "${YELLOW}启动 SLAM 系统...${NC}"
echo "Pangolin 窗口将显示 3D 轨迹和特征点"
echo ""

if [ -f "$ONNX_MODEL" ]; then
    "$PROJECT_DIR/orbslam3/build/Examples/RGB-D/rgbd_tum" \
        "$PROJECT_DIR/orbslam3/Vocabulary/ORBvoc.txt" \
        "$PROJECT_DIR/orbslam3/Examples/RGB-D/$CONFIG" \
        "$DATASET" \
        "$ASSOC" \
        "$ONNX_MODEL"
else
    "$PROJECT_DIR/orbslam3/build/Examples/RGB-D/rgbd_tum" \
        "$PROJECT_DIR/orbslam3/Vocabulary/ORBvoc.txt" \
        "$PROJECT_DIR/orbslam3/Examples/RGB-D/$CONFIG" \
        "$DATASET" \
        "$ASSOC"
fi

echo ""
echo "========================================"
echo "  SLAM 运行完成"
echo "========================================"
echo ""
echo "输出文件位置:"
echo "  轨迹: $PROJECT_DIR/orbslam3/Examples/RGB-D/CameraTrajectory.txt"
echo "  地图: $PROJECT_DIR/orbslam3/Examples/RGB-D/output/maps/"
echo ""
