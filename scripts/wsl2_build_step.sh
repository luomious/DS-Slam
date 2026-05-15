#!/bin/bash
set -e
PROJECT_DIR=/mnt/e/VSCode/VSCode-Workspace/DS-Slam

echo "=== [1/3] Building DBoW2 ==="
cd "$PROJECT_DIR/orbslam3/Thirdparty/DBoW2"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5
make -j1 2>&1 | tail -3
echo "DBoW2 DONE"

echo "=== [2/3] Building g2o ==="
cd "$PROJECT_DIR/orbslam3/Thirdparty/g2o"
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5
make -j1 2>&1 | tail -3
echo "g2o DONE"

echo "=== [3/3] Building ORB-SLAM3 (longest step, ~30-60 min) ==="
cd "$PROJECT_DIR/orbslam3"
rm -rf build
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -10
echo "cmake done, starting make -j1 ..."
make -j1 2>&1
echo "ORB-SLAM3 BUILD COMPLETE"
