#!/bin/bash
# DS-SLAM 编译脚本 - 解决 WSL2+NTFS 编译卡住问题
# 用法: 在 WSL2 中运行 bash build_ds_slam.sh [full|link|slam|test]
#   full  = 全量编译（cmake + make -j1 + 手动链接）
#   link  = 仅重新链接 rgbd_tum（不重编源码）
#   slam  = 仅重编 slam-system 库
#   test  = 编译后运行 fr1_xyz 验证

set -euo pipefail

DS_ROOT="/mnt/e/VSCode/VSCode-Workspace/DS-Slam"
ORBSLAM_DIR="$DS_ROOT/orbslam3"
SLAMSYS_DIR="$DS_ROOT/slam-system"
BUILD_DIR="$ORBSLAM_DIR/build"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[BUILD]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查内存
check_memory() {
    local free_mb=$(free -m | awk '/Mem:/{print $7}')
    if [ "$free_mb" -lt 3000 ]; then
        err "可用内存仅 ${free_mb}MB，编译需要 ≥3GB。请关闭浏览器/IDE 后重试。"
        exit 1
    fi
    log "可用内存: ${free_mb}MB ✓"
}

# 触碰修改过的源文件（解决 NTFS 时间戳问题）
touch_sources() {
    log "触碰最近修改的源文件（NTFS 时间戳修复）..."
    local files=(
        "$ORBSLAM_DIR/src/Tracking.cc"
        "$ORBSLAM_DIR/src/System.cc"
        "$ORBSLAM_DIR/Examples/RGB-D/rgbd_tum.cc"
    )
    for f in "${files[@]}"; do
        if [ -f "$f" ]; then
            touch "$f"
            log "  touched: $(basename $f)"
        fi
    done
}

# 编译 slam-system 库（小库，快速）
build_slam_system() {
    log "编译 slam-system..."
    cd "$SLAMSYS_DIR/build"
    cmake .. -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5
    make -j1 2>&1 | tail -10
    log "slam-system 编译完成 ✓"
    ls -lh "$SLAMSYS_DIR/build"/lib*.a
}

# 编译 ORB-SLAM3（只 make -j1，避免 OOM）
build_orbslam3() {
    log "编译 ORB-SLAM3（make -j1，预计 15-30 分钟）..."
    cd "$BUILD_DIR"
    
    # 仅在需要时重新 cmake
    if [ ! -f "$BUILD_DIR/CMakeCache.txt" ]; then
        log "运行 cmake..."
        cd "$ORBSLAM_DIR"
        mkdir -p build && cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -10
    fi
    
    # make -j1 避免 OOM
    log "开始 make -j1（这会很慢，请耐心等待）..."
    SECONDS=0
    if make -j1 2>&1; then
        log "make 成功，耗时 ${SECONDS}s ✓"
    else
        warn "make 失败，尝试手动链接..."
        manual_link
    fi
}

# 手动链接 rgbd_tum（绕过 make 的 Deleting file 问题）
manual_link() {
    log "手动链接 rgbd_tum..."
    local rgbd_obj="$BUILD_DIR/CMakeFiles/rgbd_tum.dir/Examples/RGB-D/rgbd_tum.cc.o"
    local output="$ORBSLAM_DIR/Examples/RGB-D/rgbd_tum"
    
    if [ ! -f "$rgbd_obj" ]; then
        err "rgbd_tum.cc.o 不存在，需要先编译"
        return 1
    fi
    
    if [ ! -f "$BUILD_DIR/libORB_SLAM3.a" ]; then
        err "libORB_SLAM3.a 不存在，需要先 make"
        return 1
    fi
    
    # 读取 link.txt 获取完整链接命令
    local link_file="$BUILD_DIR/CMakeFiles/rgbd_tum.dir/link.txt"
    if [ -f "$link_file" ]; then
        log "使用 CMake link.txt..."
        SECONDS=0
        cd "$BUILD_DIR"
        bash "$link_file" 2>&1
        if [ $? -eq 0 ] && [ -s "$output" ]; then
            log "链接成功，耗时 ${SECONDS}s ✓"
            ls -lh "$output"
            return 0
        fi
    fi
    
    # fallback: 手动构造链接命令
    warn "link.txt 不可用，手动构造链接命令..."
    SECONDS=0
    cd "$BUILD_DIR"
    /usr/bin/c++ -Wall -frtti -fkeep-inline-functions -std=c++17 -O2 -DNDEBUG \
        CMakeFiles/rgbd_tum.dir/Examples/RGB-D/rgbd_tum.cc.o \
        -o ../Examples/RGB-D/rgbd_tum \
        -Wl,-rpath,$ORBSLAM_DIR/Thirdparty/g2o/lib:$DS_ROOT/libs/onnxruntime-linux/lib:/usr/local/lib \
        libORB_SLAM3.a \
        ../Thirdparty/g2o/lib/libg2o.so \
        ${OpenCV_LIBS:-$(pkg-config --libs opencv4 2>/dev/null || echo "-lopencv_core -lopencv_imgproc")} \
        -lcurl \
        $SLAMSYS_DIR/build/libSemanticSegmentator.a \
        $SLAMSYS_DIR/build/libStaticMapper.a \
        $SLAMSYS_DIR/build/libSlamVisualizer.a \
        $DS_ROOT/libs/onnxruntime-linux/lib/libonnxruntime.so \
        ../Thirdparty/DBoW2/lib/libDBoW2.a \
        -lboost_serialization -lcrypto -lcurl -lstdc++ -lm \
        2>&1
    
    if [ -s "$output" ]; then
        log "链接成功，耗时 ${SECONDS}s ✓"
        ls -lh "$output"
    else
        err "链接失败"
        return 1
    fi
}

# 仅重新链接（不重编源码）
link_only() {
    log "仅重新链接 rgbd_tum..."
    cd "$BUILD_DIR"
    manual_link
}

# 验证测试
run_test() {
    local dataset="rgbd_dataset_freiburg1_xyz"
    log "运行验证测试: $dataset ..."
    cd "$DS_ROOT"
    ./orbslam3/Examples/RGB-D/rgbd_tum \
        ./orbslam3/Vocabulary/ORBvoc.txt \
        ./orbslam3/Examples/RGB-D/TUM3.yaml \
        ./datasets/tum/$dataset \
        ./datasets/tum/$dataset/associations.txt \
        ./segmentation/onnx/yolo11n_seg_v2.onnx \
        2>&1 | tail -15
    log "测试完成 ✓"
}

# === 主逻辑 ===
MODE="${1:-full}"

log "DS-SLAM 编译脚本 [mode=$MODE]"
check_memory

case "$MODE" in
    full)
        touch_sources
        build_slam_system
        build_orbslam3
        ;;
    link)
        link_only
        ;;
    slam)
        build_slam_system
        ;;
    test)
        run_test
        ;;
    *)
        echo "用法: bash build_ds_slam.sh [full|link|slam|test]"
        exit 1
        ;;
esac

log "完成！"
