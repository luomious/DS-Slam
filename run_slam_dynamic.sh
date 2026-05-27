#!/bin/bash
# Run DS-SLAM on dynamic scene dataset

DATASET_NAME="rgbd_dataset_freiburg3_walking_xyz"
DATASET_PATH="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/TUM/${DATASET_NAME}"
VOCAB_PATH="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Vocabulary/ORBvoc.txt"
SETTINGS_PATH="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/TUM3.yaml"
ASSOC_PATH="${DATASET_PATH}/associations.txt"
SLAM_BIN="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/rgbd_tum"
OUTPUT_DIR="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/output"

echo "=== DS-SLAM Dynamic Scene Test ==="
echo "Dataset: ${DATASET_NAME}"
echo "Output: ${OUTPUT_DIR}"

# Create output directory
mkdir -p "${OUTPUT_DIR}/maps"

# Run SLAM
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D
${SLAM_BIN} ${VOCAB_PATH} ${SETTINGS_PATH} ${DATASET_PATH} ${ASSOC_PATH}

echo "=== SLAM Complete ==="
echo "Checking output files..."
ls -la "${OUTPUT_DIR}/CameraTrajectory.txt" 2>/dev/null || echo "No trajectory file"
ls -la "${OUTPUT_DIR}/maps/static_map.ply" 2>/dev/null || echo "No PLY file"
