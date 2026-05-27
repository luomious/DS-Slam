#!/bin/bash
# Run DS-SLAM on a specific dataset with dataset-specific output

DATASET_NAME="$1"
if [ -z "$DATASET_NAME" ]; then
    echo "Usage: $0 <dataset_name>"
    echo "Available datasets:"
    ls /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/TUM/
    exit 1
fi

DATASET_PATH="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/TUM/${DATASET_NAME}"
VOCAB_PATH="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Vocabulary/ORBvoc.txt"
SETTINGS_PATH="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/TUM3.yaml"
ASSOC_PATH="${DATASET_PATH}/associations.txt"
SLAM_BIN="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/rgbd_tum"
OUTPUT_DIR="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/TUM/${DATASET_NAME}"

echo "=== DS-SLAM Dataset-Specific Run ==="
echo "Dataset: ${DATASET_NAME}"
echo "Output: ${OUTPUT_DIR}"

# Check if dataset exists
if [ ! -d "${DATASET_PATH}" ]; then
    echo "ERROR: Dataset not found: ${DATASET_PATH}"
    exit 1
fi

# Check if association file exists
if [ ! -f "${ASSOC_PATH}" ]; then
    echo "ERROR: Association file not found: ${ASSOC_PATH}"
    echo "Please generate associations.txt first"
    exit 1
fi

# Create output directory
mkdir -p "${OUTPUT_DIR}/maps"

# Run SLAM
echo "Starting SLAM..."
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D
${SLAM_BIN} ${VOCAB_PATH} ${SETTINGS_PATH} ${DATASET_PATH} ${ASSOC_PATH}

echo "=== SLAM Complete ==="
echo "Checking output files..."
ls -la "${OUTPUT_DIR}/CameraTrajectory.txt" 2>/dev/null || echo "No trajectory file"
ls -la "${OUTPUT_DIR}/maps/static_map.ply" 2>/dev/null || echo "No PLY file"
ls -la "${OUTPUT_DIR}/maps/grid_map.png" 2>/dev/null || echo "No grid map"
