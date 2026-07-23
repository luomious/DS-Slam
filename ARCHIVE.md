# DS-SLAM 项目封存文档

> 封存日期：2026-07-23
> 最终版本：v2.0
> 仓库：https://github.com/luomious/DS-Slam

## 项目概述

基于 ORB-SLAM3 的动态场景语义 SLAM 系统。核心改进：YOLO 语义分割（M3）+ 对极几何约束（M4）过滤动态特征点，动态场景 ATE 改善 94-96%。

## 最终成果

### 精度数据（EVO ATE RMSE）

| 数据集 | 场景 | RMSE | vs 基线 |
|--------|------|------|---------|
| fr1_xyz | 静态 | 1.06cm | 持平 |
| fr3_sitting_static | 弱动态 | 0.72cm | 持平 |
| fr3_walking_xyz | 强动态 | 1.38cm | 改善 96% |
| fr3_walking_halfsphere | 强动态 | 2.45cm | 改善 94% |

### 已完成模块

| 模块 | 说明 | 状态 |
|------|------|------|
| M0-M1 | 环境搭建 + ORB-SLAM3 编译（MinGW + WSL2） | ✅ |
| M2 | YOLO11n-seg ONNX 导出（11.7MB，CPU 44ms/帧） | ✅ |
| M3 | ONNX C++ 集成（SemanticSegmentator，6 bug 修复） | ✅ |
| M4 | 对极几何约束动态特征剔除 | ✅ |
| M5 | 静态稠密建图（StaticMapper，627 万点 PLY） | ✅ |
| M6 | Web 可视化（FastAPI + Three.js + WebSocket） | ✅ |
| M7 | 系统集成（SlamVisualizer 嵌入 Tracking.cc） | ✅ |
| 阶段 8.1-8.5 | 项目清理 / CMake 修复 / 调试优化 | ✅ |
| 阶段 8.11 | USB 摄像头实时建模（rgbd_camera.cc） | ✅ 编译，⚠️ 运行失败 |
| 阶段 8.6-8.10 | 统一构建 / 配置管理 / 安装包 | 🔲 仅规划 |

### 未解决问题

1. **rgbd_camera.exe 运行失败** — `STATUS_ENTRYPOINT_NOT_FOUND (0xC0000139)`，DLL 入口点不匹配
2. **rgbd_tum WSL2 core dump** — 初始化地图后崩溃，疑似 SlamVisualizer HTTP POST 超时致段错误
3. **WSL2 USB 摄像头不可用** — NAT 模式不支持 USB 直通，camera_bridge.py 未测试

---

## 环境配置需求

### 方案 A：Windows + MinGW（原始开发环境）

#### 系统要求
- Windows 11
- MSYS2 MinGW-w64（`E:\msys64`）
- CMake 3.20+
- Python 3.12+

#### C++ 工具链安装

```powershell
# 1. 安装 MSYS2（https://www.msys2.org/）
# 2. 在 MSYS2 终端安装 MinGW-w64 工具链
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake
pacman -S mingw-w64-x86_64-opencv mingw-w64-x86_64-eigen3
pacman -S mingw-w64-x86_64-boost mingw-w64-x86_64-glew
pacman -S mingw-w64-x86_64-clang

# 3. 确认版本
gcc --version          # 14.x+
cmake --version        # 3.20+
pkg-config --modversion opencv4  # 4.13+
```

#### ONNX Runtime（Windows）

```powershell
# 已包含在 libs/onnxruntime/ 目录
# 如需重新下载：
# https://github.com/microsoft/onnxruntime/releases/tag/v1.16.3
# 下载 onnxruntime-win-x64-1.16.3.zip，解压到 libs/onnxruntime/
```

#### Python 虚拟环境

```powershell
cd E:\VSCode\VSCode-Workspace\DS-Slam

# 创建虚拟环境
python -m venv .venv

# 激活
.\.venv\Scripts\Activate.ps1

# 安装依赖（CPU 版 PyTorch，RTX 5060 Blackwell 不被旧版 CUDA 支持）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 验证
python -c "import torch; print(torch.__version__)"
python -c "import onnxruntime as ort; print(ort.__version__)"
```

#### 编译

```powershell
# 1. 编译 DBoW2
cd orbslam3\Thirdparty\DBoW2
mkdir build && cd build
cmake -G "MinGW Makefiles" ..
mingw32-make -j1

# 2. 编译 g2o
cd ..\..\g2o
mkdir build && cd build
cmake -G "MinGW Makefiles" ..
mingw32-make -j1

# 3. 编译 slam-system
cd ..\..\..\slam-system
mkdir build && cd build
cmake -G "MinGW Makefiles" ..
mingw32-make -j1

# 4. 编译 ORB-SLAM3
cd ..\..\orbslam3
mkdir build && cd build
cmake -G "MinGW Makefiles" ..
mingw32-make -j1 ORB_SLAM3
```

> ⚠️ 16GB 内存机器必须 `-j1`，大模板文件多线程编译会 OOM。
> ⚠️ 需要添加 `-Wa,-mbig-obj` 编译标志（已在 CMakeLists.txt 中配置）。

---

### 方案 B：WSL2 Ubuntu 22.04（推荐运行环境）

#### 系统要求
- Windows 11 + WSL2 Ubuntu 22.04
- 至少 8GB 可用内存（编译时需要 5GB+）

#### 环境安装

```bash
# 一键安装（项目自带脚本）
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam
chmod +x scripts/wsl2_setup.sh
./scripts/wsl2_setup.sh

# 手动安装等效命令：
sudo apt update && sudo apt install -y \
    build-essential cmake git pkg-config \
    libopencv-dev libeigen3-dev libboost-all-dev \
    libglew-dev libgl1-mesa-dev libegl1-mesa-dev \
    libwayland-dev libxkbcommon-dev libglfw3-dev \
    libpng-dev libjpeg-dev libtiff-dev libopenexr-dev \
    python3.10 python3-dev python3-pip python3-venv \
    libcurl4-openssl-dev
```

#### Pangolin 安装（WSL2 可视化依赖）

```bash
git clone https://github.com/stevenlovegrove/Pangolin.git
cd Pangolin
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
```

#### ONNX Runtime（Linux）

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/libs
wget https://github.com/microsoft/onnxruntime/releases/download/v1.16.3/onnxruntime-linux-x64-1.16.3.tgz
tar xzf onnxruntime-linux-x64-1.16.3.tgz
mv onnxruntime-linux-x64-1.16.3 onnxruntime-linux
```

#### 编译（WSL2）

```bash
# 一键编译（项目自带脚本）
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam
chmod +x scripts/wsl2_build.sh
./scripts/wsl2_build.sh

# 或手动编译：
# DBoW2
cd orbslam3/Thirdparty/DBoW2 && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j2

# g2o
cd ../../g2o && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j2

# ORB-SLAM3
cd ../../.. && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j2

# slam-system
cd ../../slam-system && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DORT_ROOT=$PWD/../../libs/onnxruntime-linux
make -j2
```

> ⚠️ WSL2 + NTFS 文件系统下 `ld` 链接 707MB 静态库需 10-15 分钟，耐心等待。
> ⚠️ 如遇编译卡住，使用 `scripts/wsl2_build_step.sh` 分步编译。

---

### 方案 C：便携版（无需编译，直接运行）

项目 `dist/` 目录包含预编译的 Windows 便携版：

```
dist/
├── rgbd_tum.exe          # SLAM 主程序
├── libORB_SLAM3.dll      # ORB-SLAM3 核心库
├── onnxruntime.dll       # ONNX Runtime
├── ORBvoc.txt            # ORB 词汇表（145MB）
├── runtime_config.json   # 运行时配置
├── main.py               # 可视化后端
├── index.html            # 前端入口
└── *.dll                 # 所有依赖 DLL
```

```powershell
# 直接运行
cd dist
python main.py                    # 启动可视化后端
# 浏览器打开 index.html
```

> ⚠️ 便携版可能遇到 Windows Application Control 拦截未签名 exe。

---

## 运行方式

### 1. 数据集测试（WSL2）

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D

# 静态场景
./rgbd_tum ../../Vocabulary/ORBvoc.txt TUM1.yaml \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz/associations.txt

# 动态场景
./rgbd_tum ../../Vocabulary/ORBvoc.txt TUM3.yaml \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_xyz \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_xyz/associations.txt
```

### 2. 可视化系统

```powershell
# Windows 端启动后端
cd E:\VSCode\VSCode-Workspace\DS-Slam
.\.venv\Scripts\python.exe visualization\backend\main.py

# 或用 uvicorn
.\.venv\Scripts\uvicorn.exe visualization.backend.main:app --host 0.0.0.0 --port 8300

# 浏览器访问
# http://localhost:8300
```

### 3. 精度评估

```bash
# EVO ATE 评估
evo_ape tum \
    datasets/tum/rgbd_dataset_freiburg1_xyz/groundtruth.txt \
    orbslam3/Examples/RGB-D/CameraTrajectory.txt -va
```

### 4. 一键启动（Windows）

```powershell
.\start_system.bat datasets\tum\rgbd_dataset_freiburg1_xyz
```

---

## 关键依赖版本

| 组件 | Windows 版本 | WSL2 版本 |
|------|-------------|-----------|
| GCC | 14.x (MinGW) | 11.4.0 |
| CMake | 4.x | 3.22.1 |
| OpenCV | 4.13.0 | 4.5.4 |
| Eigen3 | 3.4.x | 3.4.0 |
| Python | 3.12.10 | 3.10.12 |
| PyTorch | 2.11.0+cpu | - |
| ONNX Runtime | 1.25.1 (GPU) | 1.16.3 |
| ultralytics | 8.4.47 | - |
| FastAPI | 0.115.2 | - |
| uvicorn | 0.29.0 | - |
| websockets | 13.1 | - |
| scipy | 1.17.1 | - |
| evo | 1.36.3 | 1.36.3 |

## Python 依赖安装（可视化后端）

```powershell
# 完整依赖
pip install -r requirements.txt

# 仅可视化后端
pip install -r visualization/backend/requirements.txt
```

## 相机配置文件

| 文件 | 相机 | 用途 |
|------|------|------|
| `TUM1.yaml` | TUM fr1 | 静态数据集测试 |
| `TUM2.yaml` | TUM fr2 | 通用 |
| `TUM3.yaml` | TUM fr3 | 动态数据集测试 |
| `Astra_Pro.yaml` | Orbbec Astra Pro | USB 摄像头实时建模 |
| `RealSense_D435i.yaml` | Intel RealSense D435i | RGB-D 摄像头 |

## ONNX 模型

| 模型 | 大小 | 用途 |
|------|------|------|
| `yolo11n_seg_v2.onnx` | 11.7MB | 默认（快速推理） |
| `yolo11s-seg.onnx` | 40.7MB | 高精度 |
| `yolo11m-seg.onnx` | 89.9MB | 最高精度 |

> 模型文件不在 git 中（.gitignore 排除），需要单独放置到 `segmentation/onnx/` 目录。

## 项目结构

```
DS-Slam/
├── orbslam3/                  # ORB-SLAM3 改造版
│   ├── src/Tracking.cc        # M3+M4 核心集成
│   ├── src/System.cc          # 语义分割器初始化
│   ├── Examples/RGB-D/        # 运行配置 + 可执行文件
│   │   ├── rgbd_tum.cc        # 数据集模式入口
│   │   ├── rgbd_camera.cc     # USB 摄像头模式入口
│   │   ├── TUM1.yaml          # TUM fr1 相机参数
│   │   ├── TUM3.yaml          # TUM fr3 相机参数
│   │   └── Astra_Pro.yaml     # Astra Pro 相机参数
│   ├── Vocabulary/ORBvoc.txt  # ORB 词汇表
│   └── Thirdparty/            # DBoW2 + g2o
├── slam-system/               # 自研 C++ 模块
│   ├── include/               # 头文件
│   ├── src/                   # 源文件
│   │   ├── SemanticSegmentator.cpp   # M3 ONNX 推理
│   │   ├── StaticMapper.cpp          # M5 稠密建图
│   │   └── SlamVisualizer.cpp        # M6 HTTP 推送
│   └── CMakeLists.txt
├── visualization/             # Web 可视化
│   ├── backend/
│   │   ├── main.py            # FastAPI 服务（151KB）
│   │   ├── dynamic_object_tracker.py
│   │   ├── keyframe_collector.py
│   │   ├── multi_frame_fusion.py
│   │   ├── photometric_error.py
│   │   ├── pose_optimizer.py
│   │   └── realtime_gaussian_updater.py
│   └── frontend/
│       ├── index.html
│       └── static/
│           ├── css/style.css
│           └── js/
│               ├── app_loader.js    # 主逻辑（63KB）
│               ├── renderer.js      # Three.js 渲染
│               └── websocket.js
├── segmentation/onnx/         # ONNX 模型（需单独下载）
├── datasets/tum/              # TUM 数据集（需单独下载）
├── libs/onnxruntime/          # Windows ONNX Runtime
├── scripts/                   # 构建/评估/部署脚本
├── dist/                      # 便携版（预编译）
├── config/                    # 统一配置
├── output/                    # 运行输出
├── requirements.txt           # Python 依赖
├── start_system.bat           # Windows 一键启动
├── PROGRESS.md                # 完整开发进度
└── README.md                  # 项目说明
```

## 需要单独获取的文件

以下文件因体积过大被 .gitignore 排除，需要单独获取：

1. **ORB 词汇表**：`orbslam3/Vocabulary/ORBvoc.txt`（145MB）—— 已包含在 dist/ 中
2. **ONNX 模型**：`segmentation/onnx/yolo11n_seg_v2.onnx`（11.7MB）—— 从 ultralytics 导出或联系作者
3. **TUM 数据集**：`datasets/tum/` —— 从 https://vision.in.tum.de/data/datasets/rgbd-dataset/download 下载
4. **ONNX Runtime Linux**：`libs/onnxruntime-linux/` —— 从 GitHub releases 下载
5. **YOLO 权重**：`yolo11s-seg.pt`（10MB）—— ultralytics 官方下载

## 技术要点备忘

1. **M3+M4 协同效应**：单独使用任一模块都会恶化结果，组合后互相抵消副作用。M3 掩码阻止 M4 对动态区域特征匹配，减少 M4 对静态特征的误杀。
2. **Eigen 跨 DLL 传递**：必须 `-DEIGEN_DONT_ALIGN_STATICALLY=1 -DEIGEN_MAX_ALIGN_BYTES=0`
3. **MinGW 大文件编译**：需要 `-Wa,-mbig-obj` 标志
4. **16GB 内存限制**：必须 `-j1` 编译，否则 OOM
5. **RTX 5060 (Blackwell sm_120)**：PyTorch ≤2.5 CUDA 不支持，使用 CPU PyTorch + ONNX Runtime GPU
6. **Windows 端口保留**：Hyper-V/WSL2 保留 8000-8080，可视化后端使用 8300
7. **WSL2 + NTFS 编译**：链接大型静态库极慢（10-15 分钟），建议在 ext4 分区编译
8. **PowerShell 编码**：`>` 重定向写 UTF-16 LE BOM，g++ 无法读取，必须用 write 工具或 `Out-File -Encoding utf8NoBOM`
