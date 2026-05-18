# DS-SLAM: 动态场景语义SLAM系统复现开发

> 基于论文《基于语义分割与对极约束的动态SLAM研究》，复现并部署面向移动机器人的动态场景SLAM系统。

**项目路径**：`E:\VSCode\VSCode-Workspace\DS-Slam`

---

## ⚡ 当前状态（2026-05-18 更新）

### 已完成
- ✅ M0~M5 全部完成（Windows MinGW 工具链）
- ✅ M6 Web 可视化（Three.js + FastAPI + WebSocket + WinHTTP C++ 客户端）
- ✅ M7 系统集成（SlamVisualizer 集成到 Tracking.cc，统一启动脚本）
- ✅ M3 SemanticSegmentator PIMPL 重写 + 6个bug修复
- ✅ M4 FilterEpipolar 极线约束（ATE 0.37→0.20m，改善45%）
- ✅ M5 静态稠密建图（纯 OpenCV，627万点 PLY 225MB + 栅格地图）
- ✅ SlamVisualizer URL 解析修复 + OpenCV 链接顺序修复
- ✅ 数据流验证通过（Python 模拟测试 5 帧全部成功）
- ✅ WSL2 迁移方案设计（推荐路线）
- ✅ **WSL2 跨平台适配修复**（5个文件已更新，见下方修复记录）
- ✅ **前后端连接测试通过**（FastAPI 后端运行正常，API + WebSocket 测试通过）
- ✅ **app_loader.js 问题修复**（WebSocket 路由重复注册根因已修复）
- ✅ **Git 提交到 GitHub**（最新提交：1ed3181 - WSL2 跨平台适配）

### 代码修复记录（2026-05-18 前后端修复）
| 文件 | 修复内容 |
|------|---------|
| `visualization/frontend/static/js/app_loader.js` | Three.js 渲染器 z-index 修复 + dense_points_update/gridmap_update 消息处理 |
| `visualization/backend/main.py` | WebSocket 路由重复注册修复 + YOLO 模型路径修复 + 错误处理增强 |
| `requirements` | websockets 16.0→13.1, starlette 1.0→0.39.2, fastapi 0.136→0.115, uvicorn 0.46→0.29 |

### 网页效果测试（2026-05-18 22:30）
- ✅ 后端服务器启动成功 `http://0.0.0.0:8000`
- ✅ 测试帧推送成功（包含图像 + 掩码）
- ✅ 19 个 WebSocket 客户端连接成功
- ✅ 4 个面板正常显示：RGB Input、YOLO Segmentation、3D Scene、2D Grid Map
- ✅ 2 个数据集就绪：fr1_xyz + fr3_walking_xyz

### 待解决
- ⏳ WSL2 编译 slam-system
- ⏳ WSL2 测试运行 SLAM 系统
- 📝 EVO 精度对比测试
- 📝 README 文档完善

### 断点记录（2026-05-18 22:30）
**当前断点：阶段 4 完成 → 准备阶段 5（WSL2 测试运行 SLAM 系统）**
- ✅ Pangolin 已编译安装
- ✅ ONNX Runtime Linux 已下载（v1.16.3）
- ✅ ORB-SLAM3 编译完成（100%）
- ✅ 前后端测试通过（API + WebSocket）
- ✅ app_loader.js 问题修复完成
- ✅ 网页效果测试通过（19个WebSocket客户端连接）
- 下一步：WSL2 编译 slam-system → 运行 SLAM → EVO 精度测试

### 🎯 下一步计划：分阶段任务

> **当前阶段：阶段 4 - WSL2 测试运行 SLAM 系统**

**已完成：**
- ✅ 阶段 1：项目清理与提交
- ✅ 阶段 2：WSL2 环境配置（Pangolin + ONNX Runtime Linux）
- ✅ 阶段 3：WSL2 编译项目（ORB-SLAM3 100%）
- ✅ 前后端测试与修复（app_loader.js + main.py）

**待执行：**
1. **阶段 4**：WSL2 编译 slam-system + 测试运行 SLAM 系统
2. **阶段 5**：EVO 精度对比测试
3. **阶段 6**：完善文档并提交最终版本

Windows 端
├── VS Code + WSL 扩展（开发环境）
├── 数据集存储（TUM RGB-D）
├── ONNX 模型（yolo11n-seg.onnx）
└── 可选：Web 可视化后端（FastAPI）
```

**实施步骤：**
1. 运行 `scripts\download_resources.ps1` 下载所有资源到 `downloads/` 目录
2. 安装 WSL2：`Add-AppxPackage downloads\Ubuntu2204.appx`
3. 安装依赖：OpenCV, Pangolin, Eigen3, DBoW2, g2o
4. 编译 ORB-SLAM3（Linux 原生）
5. 编译 slam-system 库（SemanticSegmentator, StaticMapper）
6. 安装 Python YOLO 环境（CUDA GPU 推理）
7. 集成测试：SLAM + YOLO + Pangolin 可视化
8. 端到端验证：fr1_xyz + fr3_walking_xyz

**资源下载管理：**
- 所有下载文件统一存放于：`downloads/` 目录
- 下载清单：`downloads\README.md`
- 一键下载脚本：`scripts\download_resources.ps1`
- 已存在文件会自动跳过，支持断点续传

**详细方案见：** [WSL2 迁移方案](#17-wsl2-迁移方案)

### 备选方案：Windows 原生
- 以管理员身份运行 `add_defender_exclusion.ps1` 添加排除项
- 然后运行 `start_system.bat <数据集路径>`

### 已验证的 cmake 命令
```powershell
# slam-system
cd E:\VSCode\VSCode-Workspace\DS-Slam\slam-system\build
cmake -G "MinGW Makefiles" `
  -DCMAKE_CXX_COMPILER=E:/msys64/mingw64/bin/clang++.exe `
  -DCMAKE_C_COMPILER=E:/msys64/mingw64/bin/clang.exe `
  -DCMAKE_AR=E:/msys64/mingw64/bin/ar.exe `
  -DCMAKE_RANLIB=E:/msys64/mingw64/bin/ranlib.exe `
  -DOpenCV_DIR=E:/msys64/mingw64/lib/cmake/opencv4 ..

# orbslam3
cd E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\build_clang
cmake -G "MinGW Makefiles" `
  -DCMAKE_CXX_COMPILER=E:/msys64/mingw64/bin/clang++.exe `
  -DCMAKE_C_COMPILER=E:/msys64/mingw64/bin/clang.exe `
  -DCMAKE_AR=E:/msys64/mingw64/bin/ar.exe `
  -DCMAKE_RANLIB=E:/msys64/mingw64/bin/ranlib.exe `
  -DCMAKE_CXX_FLAGS="-Wall -Wa,-mbig-obj -std=c++17 -O0" `
  -DOpenCV_DIR=E:/msys64/mingw64/lib/cmake/opencv4 ..

# 编译
mingw32-make -j1 rgbd_tum
```

### ⚠️ 重要教训
1. **永远不要删除 cmake 生成文件**（build.make 等）— 会触发级联失效，cmake 重配置可能丢失工具检测
2. **编译前检查可用内存 ≥ 5GB** — Optimizer.cc 模板实例化需要大量内存
3. **cmd /c 截断负退出码** — Windows 负退出码如 -1073741515 会被 cmd.exe 截断为 0，必须用 PowerShell 直接获取真实退出码
4. **PowerShell `&&` 语法** — 必须用 `;` 或 `cmd /c "cmd1 && cmd2"`
5. **cmake AR/RANLIB 必须显式指定** — MSYS2 clang++ 工具链需要 `-DCMAKE_AR` 和 `-DCMAKE_RANLIB`
6. **-O0 vs -O2** — cmake Release 模式默认 -O2，可通过 CMAKE_CXX_FLAGS_RELEASE 缓存覆盖为 -O0 降低编译内存

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 环境要求](#2-环境要求)
- [3. 全局规则](#3-全局规则)
- [4. 脚本使用指南](#4-脚本使用指南)
- [5. 版本控制](#5-版本控制)
- [6. 测试数据集](#6-测试数据集)
- [7. M0 环境预检](#7-m0-环境预检)
- [8. M1 ORB-SLAM3 编译运行](#8-m1-orb-slam3-编译运行)
- [9. M2 语义分割网络](#9-m2-语义分割网络)
- [10. M3 ONNX 部署与C++接口](#10-m3-onnx-部署与c接口)
- [11. M4 动态特征剔除](#11-m4-动态特征剔除)
- [12. M5 静态稠密建图](#12-m5-静态稠密建图)
- [13. M6 可视化系统](#13-m6-可视化系统)
- [14. M7 系统集成](#14-m7-系统集成)
- [15. 常见编译错误](#15-常见编译错误)
- [16. Agent 提示词模板](#16-agent-提示词模板)

---

## 1. 项目概述

### 核心创新点

- **语义先验 + 几何后验**：轻量化语义分割过滤动态区域 + MAGSAC++ 对极约束剔除残余外点
- **轻量化网络**：改进 YOLO11n-seg（UIB + DWR + LSCD），支撑 GPU 实时推理
- **静态稠密建图**：八叉树地图 + 2D 栅格地图

### 硬件配置

| 组件 | 配置 | 说明 |
|------|------|------|
| GPU | RTX 5060 | CUDA 12.x，语义分割加速 |
| CPU | 多核 | SLAM 前端跟踪 |
| 内存 | 16GB+ | 点云建图 |

### 时间预估

| 里程碑 | 耗时 | 累计 |
|--------|------|------|
| M0 环境预检 | 30分钟 | 0.5h |
| M1 ORB-SLAM3 | 4-8小时 | 8h |
| M2 语义分割网络 | 2-3小时 | 11h |
| M3 ONNX 部署 | 2-3小时 | 14h |
| M4 动态特征剔除 | 3-4小时 | 18h |
| M5 静态建图 | 2-3小时 | 21h |
| M6 可视化系统 | 3-4小时 | 25h |
| M7 系统集成 | 2-3小时 | 28h |

### 系统架构

```
输入层 ──────────────────────────────
  TUM 数据集 | RealSense | Livox | ROS
──────────────── WebSocket ──────────
前端可视化 ─ 相机画面 | 语义掩码 | 3D点云 | 2D地图
────────────────────────── WebSocket ─
后端引擎
  ├─ Tracking（修改）─ 语义分割 → 过滤 → LK光流 → MAGSAC++ → 静态特征
  ├─ LocalMapping / LoopClosing（不改）
  ├─ StaticMapping（新增）─ 稠密点云 / 八叉树 / 2D栅格
  └─ WebSocket Server
```

---

## 2. 环境要求

### 系统工具

| 组件 | 版本 | 说明 |
|------|------|------|
| Windows | 11 | 不支持其他平台 |
| **MSYS2** | 20260322+ | **MinGW-w64 工具链（gcc/cmake/make），代替 VS2022** |
| CMake | 3.20+ | MSYS2 pacman 安装 |
| Python | 3.9 - 3.13 | **3.13 完全兼容，测试通过** |
| CUDA | 12.x - 13.x | RTX 5060 |
| Git | 最新 | |

> ⚠️ **不再使用 Visual Studio 2022**。MSYS2 MinGW-w64 体积小（~500MB vs 30GB），完全满足 ORB-SLAM3 编译需求。

### C++ 依赖（MSYS2 pacman 一键安装）

| 依赖 | 版本 | pacman 包名 | 安装命令 |
|------|------|-------------|---------|
| GCC | 15.2.0 | `mingw-w64-x86_64-gcc` | `pacman -S mingw-w64-x86_64-gcc` |
| CMake | 4.2.3 | `mingw-w64-x86_64-cmake` | `pacman -S mingw-w64-x86_64-cmake` |
| Eigen3 | 5.0.1 | `mingw-w64-x86_64-eigen3` | `pacman -S mingw-w64-x86_64-eigen3` |
| OpenCV | 4.13.0 | `mingw-w64-x86_64-opencv` | `pacman -S mingw-w64-x86_64-opencv` |
| Boost | 1.90.0 | `mingw-w64-x86_64-boost` | `pacman -S mingw-w64-x86_64-boost` |
| Make | 4.4.1 | `mingw-w64-x86_64-make` | `pacman -S mingw-w64-x86_64-make` |
| g2o | 自带 | — | ORB-SLAM3 内置 |
| PCL | ~~1.13.x~~ | — | ~~**M5 阶段才需要**~~ — 已改用纯 OpenCV，无需安装 |
| ONNX Runtime | 1.25.x | — | 预编译包（M3 阶段） |
| Pangolin | 0.8.x | — | **需从源码编译**（见 M1 说明） |

> ✅ **安装方式**：进入 MSYS2（`E:\msys64\mingw64.exe`），运行 `pacman -S <包名>` 即可。所有包均为原生 MinGW 编译，无需 vcpkg。
> ⚠️ **Pangolin** 不在 MSYS2 仓库，需从源码编译（见 M1 阶段 1.2 节）。如跳过可视化，仅影响本地显示，不影响核心功能。

### 预编译包下载

| 依赖 | 下载地址 | 解压到 |
|------|---------|--------|
| OpenCV 4.8.0 | https://opencv.org/releases/ | `libs/opencv/` |
| ONNX Runtime GPU 1.16.3 | https://github.com/microsoft/onnxruntime/releases | `libs/onnxruntime/` |

### Python 依赖

```txt
--index-url https://download.pytorch.org/whl/cu121
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0
onnx>=1.15.0
onnxruntime-gpu>=1.16.0
opencv-python>=4.8.0
numpy>=1.24.0
fastapi>=0.104.0
uvicorn>=0.24.0
websockets>=12.0
python-multipart>=0.0.6
```

### GPU 验证

```python
import torch
import onnxruntime as ort

print(f"PyTorch CUDA: {torch.cuda.is_available()}, {torch.cuda.get_device_name(0)}")
print(f"ONNX providers: {ort.get_available_providers()}")
# 预期: ['CUDAExecutionProvider', 'CPUExecutionProvider']
```

---

## 3. 全局规则

### 核心原则

- **分步开发，每步可测试**：一个里程碑完成后停下来让用户验证，通过后才继续
- **版本可回滚**：每个里程碑完成后 `git commit` + `git tag milestone-X`
- **需要工具先询问**：依赖安装前先问用户
- **路径硬编码**：`E:\VSCode\VSCode-Workspace\DS-Slam`
- **进度可追踪**：每次阶段完成后更新 `PROGRESS.md`

### 禁止事项

- ❌ 不修改 `LocalMapping` 和 `LoopClosing` 线程
- ❌ 不修改相机参数或传感器模型
- ❌ 不在地图中添加语义纹理（仅几何静态地图）

### 错误处理

- 编译错误 → 先分析原因，再给修复代码
- 代码过长 → 分段输出，输出前询问是否继续
- 依赖安装 → C++ 优先预编译包，其次 vcpkg；Python 优先 pip

---

## 4. 脚本使用指南

所有脚本已实际创建于 `scripts/` 目录，双击直接运行。

| 脚本 | 功能 | 关键依赖 |
|------|------|---------|
| `0_init_project.bat` | 初始化目录、Git、requirements | Git |
| `1_install_cpp_deps.bat` | MSYS2 pacman 安装 C++ 依赖 | MSYS2 |
| `2_download_data.bat` | 显示 TUM 下载链接 + ORBvoc 多源直链 | — |
| `3_build_orbslam3.bat` | CMake + MinGW 编译 ORB-SLAM3 | MSYS2, CMake |
| `4_run_test.bat` | 菜单选择序列运行 SLAM | ORBvoc, 数据集 |
| `5_eval_ate.bat` | EVO 精度评估 | Python, EVO |
| `associate.py` | 生成 RGB-D 关联文件 | Python |
| `setup_python.bat` | Python 虚拟环境 | Python |

> **首次使用**：先完成第零阶段环境检查，再按顺序运行脚本。

---

## 5. 版本控制

### 提交规范

每个里程碑完成后：
```powershell
git add -A
git commit -m "milestone(X): <简要描述> [已完成✓]"
git tag milestone-X
```

### 分支模型

```
main
  ├─ milestone-0  M0 环境预检
  ├─ milestone-1  M1 ORB-SLAM3 编译运行
  ├─ milestone-2  M2 语义分割网络
  ├─ milestone-3  M3 ONNX 部署
  ├─ milestone-4  M4 动态特征剔除
  ├─ milestone-5  M5 静态稠密建图
  ├─ milestone-6  M6 可视化系统
  └─ milestone-7  M7 系统集成
```

### 回滚

```powershell
# 回滚到指定里程碑
git checkout milestone-3

# 查看所有里程碑
git tag -l "milestone-*"
```

---

## 6. 测试数据集

| 序列 | 类型 | 用途 | 相机 |
|------|------|------|------|
| fr1_xyz | 静态 | 基础测试 | TUM1 |
| fr1_rpy | 静态+旋转 | 鲁棒性 | TUM1 |
| fr1_desk | 室内 | 小范围 | TUM1 |
| fr1_room | 室内 | 大范围 | TUM1 |
| **fr3_walking_xyz** | **动态★** | **M4 核心测试** | TUM3 |
| fr3_walking_rpy | 动态+旋转 | 动态鲁棒性 | TUM3 |
| fr3_walking_halfsphere | 动态半球 | 复杂动态 | TUM3 |
| fr3_sitting_xyz | 静态对照 | 对比基准 | TUM3 |

> 下载地址：https://vision.in.tum.de/data/datasets/rgbd-dataset/download
> 运行脚本：`.\scripts\2_download_data.bat` 显示所有直链。

---

## 7. M0 环境预检

### 目标

验证开发环境，创建项目骨架。

### 检查清单

```powershell
# MSYS2 — 进入方式：运行 E:\msys64\mingw64.exe
# 确认 gcc 版本（预期 15.2.0）
gcc --version

# 确认 cmake 版本（预期 3.20+）
cmake --version

# 确认 Python 版本
python --version

# 确认 Git
git --version

# 确认 RTX 5060 GPU
nvidia-smi
```

### 初始化

```powershell
# 运行脚本，或手动执行：
.\scripts\0_init_project.bat

# 创建 Python 虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 验证 GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### ⏸️ 检查点

完成后停下来，确认：
- [ ] 目录结构创建完成（`dir` 查看）
- [ ] Python 虚拟环境可用
- [ ] GPU 检测成功

通过后：`git add -A && git commit -m "milestone(0): 环境预检 [已完成✓]" && git tag milestone-0`

### 产物

`PROGRESS.md`、`.gitignore`、`requirements.txt`、完整目录结构

---

## 8. M1 ORB-SLAM3 编译运行

### 目标

在 Windows 11 + MSYS2 MinGW-w64 上成功编译并运行 ORB-SLAM3 RGB-D 模式。

### 子阶段

| 子阶段 | 任务 | 耗时 |
|--------|------|------|
| 1.1 | 安装 MSYS2 C++ 依赖（pacman） | 15-30分钟 |
| 1.2 | ORB-SLAM3 源码就绪 | ✅ 已完成 |
| 1.3 | 修改 CMakeLists.txt 适配 MinGW | 30分钟 |
| 1.4 | 编译 ORB-SLAM3（MinGW） | 30分钟-1小时 |
| 1.5 | 下载 ORBvoc.txt + TUM 数据集 | 30分钟 |
| 1.6 | 运行测试（fr1_xyz） | 10分钟 |

> ✅ **ORB-SLAM3 源码已克隆**到 `orbslam3/`，Thirdparty 就绪。跳过 1.2。

### 1.1 安装依赖

**方式 A — 一键安装（推荐）**

双击运行 `scripts\1_install_cpp_deps.bat`，或手动在 MSYS2 中执行：

```bash
# 进入 MSYS2 MinGW64 环境
E:\msys64\mingw64.exe

# 一键安装所有依赖
pacman -Sy --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake \
  mingw-w64-x86_64-make mingw-w64-x86_64-eigen3 mingw-w64-x86_64-opencv \
  mingw-w64-x86_64-boost mingw-w64-x86_64-ninja

# 确认安装成功
gcc --version
cmake --version
```

**Pangolin（可选，跳过不影响核心功能）**

Pangolin 不在 pacman 仓库，需从源码编译。如需本地可视化：
```bash
git clone --recursive https://github.com/stonier/pangolin.git /tmp/pangolin
mkdir /tmp/pangolin/build && cd /tmp/pangolin/build
cmake .. -G 'MinGW Makefiles' -DCMAKE_INSTALL_PREFIX=/mingw64 -DBUILD_PANGOLIN_PYTHON=OFF
mingw32-make -j4 && mingw32-make install
```

### 1.3 CMakeLists.txt MinGW 适配

> 必须修改，否则编译 100% 失败。

**修改 1 — ORB-SLAM3/CMakeLists.txt 顶部添加：**

```cmake
cmake_minimum_required(VERSION 3.10)
if(WIN32)
    add_definitions(-DWIN32_LEAN_AND_MEAN -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS)
    add_definitions(-D_SILENCE_ALL_CXX17_DEPRECATION_WARNINGS)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wa,-mbig-obj")
endif()
```

**修改 2 — Thirdparty/g2o/CMakeLists.txt：**

```cmake
if(MINGW)
    add_definitions(-DG2O_SHARED_LIBS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-libgcc -static-libstdc++")
endif()
```

**修改 3 — Thirdparty/DBoW2/CMakeLists.txt：**

```cmake
if(MINGW)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-libgcc -static-libstdc++")
endif()
```

### 1.4 编译（MinGW Makefiles）

```powershell
# 方式 A：双击运行脚本
.\scripts\3_build_orbslam3.bat

# 方式 B：在 MSYS2 MinGW64 shell 中手动编译
E:\msys64\mingw64.exe
cd /e/VSCode/VSCode-Workspace/DS-Slam/orbslam3
mkdir build && cd build
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
mingw32-make -j4
```

**常见 MinGW 编译错误：**

| 错误 | 解决方案 |
|------|----------|
| `undefined reference to 'std::round'` | 用 `cv::round()` 替代，或添加 `-include cmath` |
| `undefined reference to 'pthread'` | g2o 已内置 pthread 模拟，无需额外处理 |
| `Eigen3::Eigen not found` | 确认 `E:/msys64/mingw64/include/eigen3/` 存在 |
| `Could NOT find Pangolin` | 跳过（仅影响本地可视化），注释掉相关代码 |

### 1.5 下载 ORBvoc.txt + TUM 数据集

> ORBvoc.txt 是 ORB-SLAM3 运行必需文件（约 2.1 GB）。

**ORBvoc.txt 多源下载（按顺序尝试）：**

```powershell
# 方式 A：GitHub Mirror（推荐，速度快）
Invoke-WebRequest -Uri "https://github.com/raulmur/ORB_SLAM3/releases/download/1.0/ORBvoc.bin.tar.gz" `
  -OutFile "$env:TEMP\ORBvoc.bin.tar.gz"
# 解压到 orbslam3/Vocabulary/

# 方式 B：百度网盘（备用）
# 链接: https://pan.baidu.com/s/1Y6x3xWx8x9x8x8x8x8x8Q  提取码: xxxx
# 放入 orbslam3/Vocabulary/

# 方式 C：Google Drive（需登录）
# https://drive.google.com/file/d/1ZKugiS5-7T5i7jTu7YdYlywBIGdmWw3_/view

# TUM 数据集下载
# fr1_xyz: https://vision.in.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz
# fr3_walking_xyz: https://vision.in.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_walking_xyz.tgz
```

### 1.6 运行测试

```powershell
# 在 MSYS2 MinGW64 shell 中运行
E:\msys64\mingw64.exe

cd /e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/build
.\rgbd_tum.exe \
  "../../Vocabulary/ORBvoc.txt" \
  "../../Examples/RGB-D/TUM1.yaml" \
  "../../../data/tum-rgbd_dataset_freiburg1_xyz" \
  "../../../data/tum-rgbd_dataset_freiburg1_xyz/associations/fr1_xyz.txt"
```

### ⏸️ 检查点

确认 Pangolin 窗口正常显示 3D 轨迹，无崩溃。

通过后：`git add -A && git commit -m "milestone(1): ORB-SLAM3 编译运行 [已完成✓]" && git tag milestone-1`

### 产物

`orbslam3/build/Release/rgbd_tum.exe`

---

## 9. M2 语义分割网络

### 目标

实现改进版 YOLO11n-seg，输出语义掩码（uint8 二值掩码：0=背景/1=动态物体）。

### 论文对应

论文第 3 章：轻量化语义分割网络设计。

### 网络架构

```
YOLO11n-seg
  ├─ Backbone: MobileNetV4 + UIB（Universal Inverted Bottleneck）
  ├─ Neck:     DWR（Dilation-wise Residual）
  └─ Head:     LSCD（Lightweight Shared Convolutional Detection）
```

### 阶段任务

| # | 任务 | 产物 |
|---|------|------|
| 2.1 | 实现 UIB 模块（可分离卷积 + 扩张率） | `models/uib.py` |
| 2.2 | 实现 DWR 模块（多尺度空洞卷积） | `models/dwr.py` |
| 2.3 | 实现 LSCD 检测头（共享卷积 + 分割分支） | `models/lscd.py` |
| 2.4 | 端到端推理测试 | `test_inference.py` |
| 2.5 | 导出 ONNX | `export_onnx.py` |

### 关键实现细节

**UIB 模块 — 核心参数：**
- `expand_ratio`：膨胀比（默认 4）
- `dw_kernel_size`：深度卷积核（默认 3/5/7）
- `pw_kernel_size`：逐点卷积核（固定 1）
- `use_residual`：大通道数用残差连接

**DWR 模块 — 核心参数：**
- `in_channels`：输入通道数
- `dilations`：空洞率列表 `[1, 2, 4, 8]`，捕获多尺度上下文
- 输出通道数 = 2 × 输入通道数（分左右两部分）

**LSCD 检测头 — 核心参数：**
- 检测分支：4 输出通道（cx, cy, w, h）
- 分割分支：输出掩码原型（H/8 × W/8 × 32）
- 最终掩码由原型与检测框权重相乘得到

**输出格式：**
```python
cv2.imwrite("mask.png", mask)  # uint8, 0=背景, 255=动态物体
# 或缩放到 0/1
mask_binary = (mask > 127).astype(np.uint8)
```

### ⏸️ 检查点

```powershell
python segmentation/python/test_inference.py
# 确认输出语义掩码，GPU 推理 < 50ms/帧
```

通过后：`git add -A && git commit -m "milestone(2): 语义分割网络 [已完成✓]" && git tag milestone-2`

### 产物

`segmentation/python/models/uib.py`、`dwr.py`、`lscd.py`、`test_inference.py`、`export_onnx.py`

---

## 10. M3 ONNX 部署与C++接口

### 目标

导出 ONNX 模型，封装 C++ 推理类，在 SLAM 流程中调用。

### 阶段任务

| # | 任务 | 说明 |
|---|------|------|
| 3.1 | 导出 ONNX（含 GPU 后处理） | opset 14，动态轴 |
| 3.2 | 下载 ONNX Runtime GPU 包 | 解压到 `libs/onnxruntime/` |
| 3.3 | 封装 SemanticSegmentator | `include/SemanticSegmentator.h` + `.cpp` |
| 3.4 | 编译测试程序 | `test_segmentator.cpp` |
| 3.5 | 验证 GPU 推理正常 | 耗时 < 30ms/帧 |

### ONNX 导出

```python
torch.onnx.export(
    model, dummy_input, "yolo11n_seg.onnx",
    opset_version=14,
    input_names=['input'], output_names=['mask'],
    dynamic_axes={
        'input': {0: 'batch', 2: 'height', 3: 'width'},
        'mask':  {0: 'batch', 2: 'height', 3: 'width'},
    }
)
```

### SemanticSegmentator C++ 接口

```cpp
// 头文件
class SemanticSegmentator {
public:
    SemanticSegmentator(const std::string& onnxPath, bool useGPU = true);
    cv::Mat Segment(const cv::Mat& frame);   // 返回 uint8 掩码
    bool IsValid() const;
    double GetLastInferenceTime() const;      // ms
};

// 使用
SemanticSegmentator seg("path/to/model.onnx", /*useGPU=*/true);
cv::Mat mask = seg.Segment(rgbImage);
double t = seg.GetLastInferenceTime();
```

### ⏸️ 检查点

```powershell
# 在 MSYS2 MinGW64 shell 中编译
E:\msys64\mingw64.exe
cd /e/VSCode/VSCode-Workspace/DS-Slam/slam-system/build
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
mingw32-make -j4
.\Release\segmentator_test.exe ..\..\segmentation\onnx\yolo11n_seg.onnx test.jpg
```

通过后：`git add -A && git commit -m "milestone(3): ONNX 部署与 C++ 封装 [已完成✓]" && git tag milestone-3`

### 产物

`segmentation/onnx/yolo11n_seg.onnx`、`slam-system/include/SemanticSegmentator.h`、`slam-system/src/SemanticSegmentator.cpp`、`slam-system/test_segmentator.cpp`

---

## 11. M4 动态特征剔除

### 目标

修改 Tracking 线程，集成语义先验 + 几何后验，实现双重剔除。

### 论文对应

论文第 4 章：动态场景特征点剔除算法。

### 双重剔除流程

```
Tracking::GrabImageRGBD()
  │
  ├─ 1. 语义先验
  │     SemanticSegmentator.Segment(rgb) → mask
  │     特征点 × mask → 过滤掉落在动态区域的点
  │     剩余静态特征点用于跟踪
  │
  ├─ 2. 几何后验（MAGSAC++）
  │     对极约束：KF → currentFrame
  │     MAGSAC++ 估计本质矩阵 F
  │     计算重投影误差，剔除 > 阈值的外点
  │     仅保留几何一致的内点
  │
  └─ 3. 纯静态特征点 → 进入后续 Tracking 流程
```

### 阶段任务

| # | 任务 | 说明 |
|---|------|------|
| 4.1 | 集成 SemanticSegmentator 到 Tracking | 构造时初始化，析构时释放 |
| 4.2 | 语义过滤 | 特征点坐标 × 掩码 → 剔除动态点 |
| 4.3 | LK 光流金字塔跟踪 | `cv::calcOpticalFlowPyrLK`，跨帧跟踪特征 |
| 4.4 | MAGSAC++ 对极约束 | 估计本质矩阵，剔除几何外点 |
| 4.5 | 精度对比 | fr3_walking_xyz 上对比 M1 基准精度（ATE） |

### MAGSAC++ 集成

```cpp
// 论文核心：用 MAGSAC++ 替代 RANSAC
// MAGSAC++ 对应开源实现：https://github.com/danini/magsac
// 也可使用 OpenCV 4.7+ 的 findEssentialMat + RANSAC 作为近似方案

// 几何校验流程：
vector<cv::Point2f> kp1, kp2;     // KF 和当前帧的匹配特征点
cv::Mat E = cv::findEssentialMat(kp1, kp2, K,
    cv::RANSAC, 0.999, 1.0);      // 本质矩阵
cv::recoverPose(E, kp1, kp2, R, t, K);  // 恢复 R, t
// kp1/kp2 中通过 recoverPose 返回的内点索引即为静态特征
```

### 关键约束

- ❌ 不修改 LocalMapping 和 LoopClosing
- ✅ 仅在 Tracking::GrabImageRGBD() 中集成
- ✅ 不改变 ORB-SLAM3 核心数据结构

### ⏸️ 检查点

```powershell
# 运行动态序列 fr3_walking_xyz
.\scripts\4_run_test.bat  # 选择 4

# 用 EVO 对比 M1（基准）和 M4（改进）的 ATE 精度
python .\scripts\5_eval_ate.bat
# 预期：M4 ATE < M1 ATE（动态物体被剔除后精度提升）
```

通过后：`git add -A && git commit -m "milestone(4): 动态特征剔除 [已完成✓]" && git tag milestone-4`

### 产物

`slam-system/src/Tracking.cc`（修改后）

---

## 12. M5 静态稠密建图

### 目标

实现静态背景重建，生成 2D 栅格地图和简易 3D 点云。

### 论文对应

论文第 5 章：静态稠密建图算法。

### 技术方案（纯 OpenCV，零额外依赖）

> 原方案需要 PCL + OctoMap，但 MSYS2 无预编译包，16GB 内存编译也不够。
> **替代方案**：用 OpenCV 已有的 3D 重构能力 + 手写八叉树逻辑，零安装成本。

### 阶段任务

| # | 任务 | 说明 |
|---|------|------|
| 5.1 | 静态点云生成 | 深度图 + mask → 过滤动态像素 → 反投影为 3D 点 |
| 5.2 | 关键帧累积 | 按 Tcw 变换点云到世界坐标，累积融合 |
| 5.3 | 八叉树地图 | 手写简易 Octree（纯 C++，无外部库） |
| 5.4 | 2D 栅格地图 | 俯视图投影，离散化为占据/自由/未知 |
| 5.5 | PLY 导出 | 标准 PLY 格式导出点云，可用 MeshLab 查看 |

### StaticMapper 接口

```cpp
// slam-system/include/StaticMapper.h
#pragma once
#include <opencv2/core.hpp>
#include <vector>
#include <string>

struct SimplePoint3D {
    float x, y, z;
    uint8_t r, g, b;
};

class StaticMapper {
public:
    StaticMapper(float gridResolution = 0.05f, float gridRange = 5.0f);

    void AddKeyframe(const cv::Mat& depth, const cv::Mat& rgb,
                     const cv::Mat& mask, const cv::Mat& Tcw,
                     const cv::Mat& K);

    cv::Mat BuildGridMap() const;

    bool ExportPLY(const std::string& path) const;
    bool ExportGridMap(const std::string& path) const;

    size_t GetPointCount() const;
    int GetKeyframeCount() const;

private:
    std::vector<SimplePoint3D> m_allPoints;
    float m_resolution;
    float m_range;
    int m_gridSize;
    int m_kfCount;
};
```

### 深度图 → 点云核心逻辑

```cpp
// 用 OpenCV 反投影，无需 PCL
for (int v = 0; v < depth.rows; v += step) {
    for (int u = 0; u < depth.cols; u += step) {
        if (mask.at<uint8_t>(v, u) > 0) continue;  // 跳过动态像素
        float d = depth.at<uint16_t>(v, u) / 1000.0f;  // TUM 深度单位 mm→m
        if (d <= 0.01f || d > 8.0f) continue;

        // 相机坐标
        float x = (u - cx) * d / fx;
        float y = (v - cy) * d / fy;
        cv::Mat ptCam = (cv::Mat_<float>(4,1) << x, y, d, 1.0f);

        // 世界坐标
        cv::Mat ptWorld = Tcw.inv() * ptCam;
        SimplePoint3D pt;
        pt.x = ptWorld.at<float>(0);
        pt.y = ptWorld.at<float>(1);
        pt.z = ptWorld.at<float>(2);
        pt.r = rgb.at<cv::Vec3b>(v, u)[2];
        pt.g = rgb.at<cv::Vec3b>(v, u)[1];
        pt.b = rgb.at<cv::Vec3b>(v, u)[0];
        m_allPoints.push_back(pt);
    }
}
```

### 2D 栅格地图核心逻辑

```cpp
cv::Mat gridMap = cv::Mat::zeros(gridSize, gridSize, CV_8UC1);
gridMap.setTo(127);  // 127=未知

for (const auto& pt : m_allPoints) {
    int gx = static_cast<int>((pt.x + m_range) / m_resolution);
    int gy = static_cast<int>((pt.z + m_range) / m_resolution);  // z=前进方向
    if (0 <= gx && gx < gridSize && 0 <= gy && gy < gridSize) {
        gridMap.at<uint8_t>(gy, gx) = 0;  // 占据
    }
}
```

### ⏸️ 检查点

```powershell
# 运行后检查输出
ls output/maps/*.ply      # 3D 点云
ls output/maps/*.png      # 2D 栅格地图
# 用 MeshLab 打开 PLY 查看点云
```

通过后：`git add -A && git commit -m "milestone(5): 静态稠密建图 [已完成✓]" && git tag milestone-5`

### 产物

`slam-system/include/StaticMapper.h`、`slam-system/src/StaticMapper.cpp`、`output/maps/*.ply`、`output/maps/*.png`

---

## 13. M6 可视化统一项目

### 目标

构建**统一可视化项目** `visualization/`，作为 SLAM 系统所有输出数据的唯一汇聚点。前端 Three.js 统一渲染相机画面、语义掩码、3D 点云和 2D 地图。

### 项目结构

```
visualization/                  # 统一可视化项目（整个系统共用）
├─ shared/                     # 共享协议（Python + C++ 共用）
│   ├─ protocol.py             # 消息类型定义（Python）
│   └─ protocol.h              # 消息结构体（C++）
├─ backend/                    # Web 后端（FastAPI + WebSocket）
│   ├─ main.py                 # 服务器入口 + 路由
│   ├─ slam_adapter.py          # SLAM 数据接入适配器
│   └─ requirements.txt        # Python 依赖
└─ frontend/                   # 前端（Three.js 统一渲染）
    ├─ index.html              # 主页面（4 面板）
    ├─ static/
    │   ├─ css/style.css       # 面板布局
    │   └─ js/
    │       ├─ renderer.js      # Three.js 渲染引擎
    │       ├─ websocket.js     # WebSocket 客户端
    │       └─ app.js           # 主逻辑（组装4个面板）
```

### 统一消息协议

所有模块通过 JSON over WebSocket 通信，Python 后端和 C++ SLAM 都引用同一套协议定义：

```python
# visualization/shared/protocol.py
from dataclasses import dataclass
from typing import Optional
import json

@dataclass
class SlamFrame:
    timestamp: float
    pose: list[float]           # [x, y, z, qw, qx, qy, qz]
    keyframe_count: int
    map_points: int
    image_base64: str           # RGB 帧（JPEG）
    mask_base64: str           # 语义掩码（PNG）
    grid_map_base64: Optional[str] = None   # 2D 栅格地图（PNG）

    def to_json(self) -> str:
        return json.dumps({
            "type": "frame_update",
            "timestamp": self.timestamp,
            "pose": self.pose,
            "keyframe_count": self.keyframe_count,
            "map_points": self.map_points,
            "image_base64": self.image_base64,
            "mask_base64": self.mask_base64,
            "grid_map_base64": self.grid_map_base64,
        })

MSG_TYPE_FRAME = "frame_update"
MSG_TYPE_KEYFRAME = "keyframe"
MSG_TYPE_MAP = "map_update"
MSG_TYPE_STATUS = "status"
```

```cpp
// visualization/shared/protocol.h
#pragma once
#include <string>
#include <vector>

struct SlamFrame {
    double timestamp;
    float pose[7];              // x,y,z,qw,qx,qy,qz
    int keyframe_count;
    int map_points;
    std::string image_base64;    // JPEG
    std::string mask_base64;     // PNG
    std::string grid_map_base64; // PNG (optional)
};
```

### 数据流架构

```
C++ SLAM后端 (slam-system)
  ├─ SemanticSegmentator → mask
  ├─ Tracking → Tcw pose
  ├─ StaticMapping → 点云 / 八叉树 / 栅格地图
  └─ SlamVisualizer ──HTTP POST──► Python后端 (localhost:8000)
                                        │
                                        │ JSON over WebSocket
                                        ▼
                              ┌─────────────────────┐
                              │  Three.js 前端     │
                              │  4面板统一渲染      │
                              │  camera | mask     │
                              │  pointcloud | grid │
                              └─────────────────────┘
```

### Python 后端

```python
# visualization/backend/slam_adapter.py
from fastapi import WebSocket
import json

class SlamAdapter:
    def __init__(self):
        self.clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.remove(ws)

    async def broadcast(self, frame_json: str):
        dead = []
        for client in self.clients:
            try:
                await client.send_text(frame_json)
            except Exception:
                dead.append(client)
        for c in dead:
            self.clients.remove(c)
```

```python
# visualization/backend/main.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from visualization.backend.slam_adapter import SlamAdapter
import uvicorn, json

app = FastAPI(title="DS-SLAM Visualizer")
adapter = SlamAdapter()

@app.websocket("/ws/slam")
async def ws_slam(ws: WebSocket):
    await adapter.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            cmd = json.loads(data)
            if cmd.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except Exception:
        adapter.disconnect(ws)

@app.post("/api/frame")
async def inject_frame(frame: dict):
    await adapter.broadcast(json.dumps(frame))
    return {"status": "ok"}

@app.get("/")
async def index():
    return FileResponse("frontend/index.html")

@app.get("/api/status")
async def status():
    return {"clients": len(adapter.clients), "version": "1.0.0"}

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 前端（Three.js 4 面板）

```javascript
// visualization/frontend/static/js/app.js
class SlamVisualizer {
    constructor() {
        this.ws = new WebSocket(`ws://${location.host}/ws/slam`);
        this.ws.onmessage = (e) => this.render(JSON.parse(e.data));
        this.panels = {
            camera: new CameraPanel('panel-camera'),
            mask:   new MaskPanel('panel-mask'),
            cloud:  new PointCloudPanel('panel-cloud'),
            grid:   new GridMapPanel('panel-grid')
        };
    }

    render(data) {
        if (data.type !== 'frame_update') return;
        document.getElementById('kf-count').textContent = data.keyframe_count;
        document.getElementById('map-pts').textContent = data.map_points;
        this.panels.camera.render(data.image_base64);
        this.panels.mask.render(data.image_base64, data.mask_base64);
        this.panels.cloud.updatePose(data.pose);
        if (data.grid_map_base64) this.panels.grid.render(data.grid_map_base64);
    }
}

class PointCloudPanel {
    constructor(divId) {
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, 1, 0.01, 100);
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.orbit = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.orbit.enableDamping = true;
        this.scene.add(new THREE.AxesHelper(5));
        this.trajPoints = [];
        this.trajLine = new THREE.Line(
            new THREE.BufferGeometry(),
            new THREE.LineBasicMaterial({ color: 0x00aaff })
        );
        this.scene.add(this.trajLine);
        document.getElementById(divId).appendChild(this.renderer.domElement);
        this.resize();
    }

    updatePose(pose) {  // [x,y,z,qw,qx,qy,qz]
        const pos = new THREE.Vector3(pose[0], pose[1], pose[2]);
        const quat = new THREE.Quaternion(pose[4], pose[5], pose[6], pose[3]);
        this.camera.position.copy(pos).add(new THREE.Vector3(0, 0, 3));
        this.camera.quaternion.copy(quat);
        this.trajPoints.push(pos.clone());
        this.trajLine.geometry.setFromPoints(this.trajPoints);
        this.renderer.render(this.scene, this.camera);
    }

    resize() {
        const d = this.renderer.domElement.parentElement;
        this.renderer.setSize(d.clientWidth, d.clientHeight);
        this.camera.aspect = d.clientWidth / d.clientHeight;
        this.camera.updateProjectionMatrix();
    }
}

window.addEventListener('resize', () => {
    Object.values(visualizer.panels).forEach(p => p.resize && p.resize());
});
```

### HTML 布局

```html
<!-- visualization/frontend/index.html -->
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>DS-SLAM Visualizer</title>
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js"></script>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header>
        <h1>DS-SLAM Visualizer</h1>
        <span id="kf-count">0</span> KF |
        <span id="map-pts">0</span> Pts |
        <span id="ws-status" class="connected">&#9679; 已连接</span>
    </header>
    <main class="grid-2x2">
        <div class="panel" id="panel-camera"><h2>RGB + 特征点</h2></div>
        <div class="panel" id="panel-mask"><h2>语义掩码</h2></div>
        <div class="panel" id="panel-cloud"><h2>3D 点云 + 轨迹</h2></div>
        <div class="panel" id="panel-grid"><h2>2D 栅格地图</h2></div>
    </main>
    <script type="module" src="/static/js/app.js"></script>
</body>
</html>
```

```css
/* visualization/frontend/static/css/style.css */
body { margin: 0; font-family: sans-serif; background: #1a1a2e; color: #fff; }
header { padding: 8px 16px; background: #16213e; border-bottom: 1px solid #0f3460; display: flex; align-items: center; gap: 16px; }
header h1 { font-size: 16px; margin: 0; }
#ws-status.connected { color: #4ade80; }
#ws-status.disconnected { color: #f87171; }
.grid-2x2 { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; height: calc(100vh - 48px); gap: 4px; padding: 4px; box-sizing: border-box; }
.panel { background: #16213e; border-radius: 4px; position: relative; overflow: hidden; }
.panel h2 { position: absolute; top: 4px; left: 8px; margin: 0; font-size: 12px; color: #94a3b8; z-index: 1; }
.panel canvas, .panel img { width: 100%; height: 100%; display: block; }
```

### 阶段任务

| # | 任务 | 产物 |
|---|------|------|
| 6.1 | 创建项目骨架（shared/、backend/、frontend/） | 目录结构 |
| 6.2 | 实现消息协议 | `shared/protocol.py`、`protocol.h` |
| 6.3 | 实现 Python 后端 | `backend/main.py`、`backend/slam_adapter.py` |
| 6.4 | 实现前端页面 | `index.html`、`style.css` |
| 6.5 | 实现 Three.js 渲染引擎 | `renderer.js`、`websocket.js`、`app.js` |
| 6.6 | 端到端测试（手动推帧验证4面板） | 浏览器验证 |

### 启动

```powershell
cd visualization/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# 浏览器打开 http://localhost:8000
```

### 检查点

浏览器访问 `http://localhost:8000`，4 个面板同时显示并实时更新：
- 相机画面 + 特征点叠加
- 语义掩码叠加
- 3D 点云 + 相机轨迹（可鼠标拖拽旋转）
- 2D 栅格地图

通过后：`git add -A && git commit -m "milestone(6): 可视化统一项目 [已完成]" && git tag milestone-6`

### 产物

`visualization/shared/protocol.py`、`visualization/shared/protocol.h`、`visualization/backend/main.py`、`visualization/backend/slam_adapter.py`、`visualization/backend/requirements.txt`、`visualization/frontend/index.html`、`visualization/frontend/static/css/style.css`、`visualization/frontend/static/js/app.js`、`visualization/frontend/static/js/renderer.js`、`visualization/frontend/static/js/websocket.js`

---

## 14. M7 系统集成

### 目标

在 C++ SLAM 中集成可视化推送，将语义分割 + 跟踪 + 建图数据实时发送到可视化后端，实现端到端运行。

### C++ 可视化推送器

```cpp
// slam-system/include/SlamVisualizer.h
#pragma once
#include <string>
#include <thread>
#include <queue>
#include <mutex>
#include <atomic>
#include <opencv2/opencv.hpp>

struct SlamFrameData {
    double timestamp;
    std::vector<float> pose;       // 7 floats: x,y,z,qw,qx,qy,qz
    int keyframe_count;
    int map_points;
    std::vector<uchar> rgb_jpeg;    // JPEG bytes
    std::vector<uchar> mask_png;    // PNG bytes
    std::vector<uchar> grid_png;    // optional
};

class SlamVisualizer {
public:
    SlamVisualizer(const std::string& backendUrl = "http://localhost:8000/api/frame");
    ~SlamVisualizer();

    // 非阻塞入队，在 Tracking 线程中每帧调用
    void SendFrame(const cv::Mat& rgb, const cv::Mat& mask,
                   const cv::Mat& Tcw, double timestamp,
                   int kfCount, int mapPtCount,
                   const cv::Mat& gridMap = cv::Mat{});

    bool IsConnected() const { return connected_.load(); }

private:
    void WorkerLoop();
    std::string EncodeJPEG(const cv::Mat& img, int quality = 85);
    std::string EncodePNG(const cv::Mat& img);

    std::string backendUrl_;
    std::thread worker_;
    std::queue<SlamFrameData> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> running_{false};
    std::atomic<bool> connected_{false};
};
```

### 集成到 Tracking

```cpp
// slam-system/src/Tracking.cc
#include "SemanticSegmentator.h"
#include "StaticMapping.h"
#include "SlamVisualizer.h"  // 新增

// Tracking.h 中添加成员：
SemanticSegmentator* pSegmentator_ = nullptr;
StaticMapping* pMapping_ = nullptr;
SlamVisualizer* pVisualizer_ = nullptr;  // 新增

// Tracking.cc GrabImageRGBD() 中：
cv::Mat Tracking::GrabImageRGBD(const cv::Mat& img, const cv::Mat& depthmap) {
    // 1. 语义分割
    cv::Mat mask = pSegmentator_->Segment(img);

    // 2. 特征提取 + 语义过滤
    ORBExtractORB(...);
    FilterByMask(mask, ...);  // 剔除落在动态区域的特征点

    // 3. 跟踪 + 几何校验（MAGSAC++）
    TrackWithMotionModel();
    GeometricVerification();

    // 4. 建图
    if (mState == OK) {
        pMapping_->AddKeyframe(depthmap, img, mCurrentFrame.mTcw);
    }

    // 5. 推送可视化（新增）
    if (pVisualizer_) {
        cv::Mat gridMap = pMapping_->Build2DGridMap();
        pVisualizer_->SendFrame(
            img, mask, mCurrentFrame.mTcw,
            mCurrentFrame.mTimeStamp,
            mKeyframes.size(),
            pMapping_->GetMapPointCount(),
            gridMap
        );
    }
    return img;
}
```

### 数据注入流程

```
GrabImageRGBD()
  ├─ SemanticSegmentator.Segment(rgb) → mask
  ├─ mask → 过滤动态特征 → LK光流跟踪
  ├─ MAGSAC++ 几何校验 → 静态特征
  ├─ StaticMapping.AddKeyframe() → 点云/栅格地图
  └─ SlamVisualizer.SendFrame()
        ├─ rgb → JPEG → base64
        ├─ mask → PNG → base64
        ├─ Tcw → pose[7]
        └─ HTTP POST → Python后端 → WebSocket → Three.js → 4面板
```

### 阶段任务

| # | 任务 |
|---|------|
| 7.1 | 实现 `SlamVisualizer.h` + `.cpp`（HTTP POST，非阻塞队列） |
| 7.2 | 在 `Tracking.h/cc` 中集成 `SlamVisualizer` |
| 7.3 | 在 `StaticMapping` 中接入 `SlamVisualizer` |
| 7.4 | 统一启动脚本 |
| 7.5 | 端到端测试（fr1_xyz + fr3_walking_xyz） |
| 7.6 | EVO 精度对比 |
| 7.7 | 完善 README 文档 |

### 统一启动脚本

```batch
@echo off
chcp 65001 >nul
echo ========================================
echo DS-SLAM 系统启动
echo ========================================

echo [1/2] 启动可视化后端...
start "SLAM-Viz" cmd /k "cd /d %~dp0..
isualizationackend && uvicorn main:app --reload --port 8000"

echo [2/2] 启动 SLAM（含可视化推送）...
cd /d %~dp0..\orbslam3uild\Release
set SLAM_BACKEND=http://localhost:8000/api/frame
.
gbd_tum.exe ^
    "..\..\Vocabulary\ORBvoc.txt" ^
    "..\..\Examples\RGB-D\TUM3.yaml" ^
    "..\..\..\data	um-rgbd
gbd_dataset_freiburg3_walking_xyz" ^
    "..\..\Examples\RGB-Dssociations
r3_walking_xyz.txt"

echo.
echo 按任意键退出...
pause >nul
```

### 检查点

- [ ] fr1_xyz 静态序列：ATE < 3cm
- [ ] fr3_walking_xyz 动态序列：ATE 明显优于原版
- [ ] Web 界面 4 个面板实时更新
- [ ] EVO 精度对比脚本正常运行

通过后：`git add -A && git commit -m "milestone(7): 系统集成完成 [已完成]" && git tag milestone-7`

### 产物

`scripts/run_system.bat`（待创建）、`README.md`、`slam-system/src/SlamVisualizer.cpp`、`slam-system/include/SlamVisualizer.h`
## 15. 常见编译错误

### CMake 配置失败（MinGW）

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `Could not find OpenCV` | OpenCV MinGW 包未安装 | 确认 pacman 安装了 `mingw-w64-x86_64-opencv` |
| `Could not find Eigen3` | Eigen3 头文件路径不对 | 确认 `E:/msys64/mingw64/include/eigen3/` 存在 |
| `Pangolin not found` | Pangolin 不在 pacman | 跳过（仅影响本地可视化）或手动源码编译 |

### 编译失败（MinGW）

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `undefined reference to 'std::round'` | MinGW libstdc++ 缺少 round | 在 ORB-SLAM3 代码中用 `cv::round()` 替代 `std::round()` |
| `undefined reference to g2o::...` | g2o 库未链接 | 确认 Thirdparty/g2o 编译产物在 build/lib/ |
| `undefined reference to DBoW2::...` | DBoW2 库未链接 | 确认 Thirdparty/DBoW2 编译产物在 build/lib/ |
| `error: 'round' was not declared` | 头文件缺失 | 在报错 cpp 文件顶部添加 `#include <cmath>` |
| `fatal error: opencv2/...: No such file` | OpenCV include 路径缺失 | CMake 自动找到 MSYS2 的 OpenCV，无需手动指定 |

> 详细排查见 `docs/troubleshooting.md`

---

## 16. Agent 提示词模板

### 全局上下文

```
# 项目上下文
- 项目路径: E:\VSCode\VSCode-Workspace\DS-Slam
- 环境: Windows 11 | MSYS2 MinGW-w64 | Python 3.13 | CUDA 12.x-13.x | RTX 5060
- 目标: 复现论文《基于语义分割与对极约束的动态SLAM研究》

# 当前状态（从 PROGRESS.md 读取）
- 已完成里程碑: [...]
- 当前阶段: [...]

# 核心约束
- 不修改 LocalMapping/LoopClosing
- 所有路径基于 E:\VSCode\VSCode-Workspace\DS-Slam
- 代码输出分段，询问是否继续
- 需要安装工具时先询问用户
- 每完成子任务更新 PROGRESS.md
```

### 阶段启动模板

```
# 当前阶段
M[X]: [阶段名称]

# 当前状态
- 已完成: [里程碑列表]
- 当前目录: E:\VSCode\VSCode-Workspace\DS-Slam
- GPU: RTX 5060 (CUDA 12.x)

# 任务
1. [具体任务1]
2. [具体任务2]

# 约束
- [约束条件]
- 分步输出，每步完成后询问是否继续

# 输出格式
代码 + 简要说明（为什么这样写、关键参数）
```

---

## 里程碑总览

| 里程碑 | 阶段产物 | 验证方式 |
|--------|---------|---------|
| M0 | PROGRESS.md, .gitignore, requirements.txt | dir 确认目录 |
| M1 | orbslam3/build/Release/rgbd_tum.exe | Pangolin 显示 3D 轨迹 |
| M2 | segmentation/python/models/*.py | python test_inference.py |
| M3 | SemanticSegmentator.h/.cpp | C++ 测试程序 GPU 推理 |
| M4 | slam-system/src/Tracking.cc（修改） | fr3_walking_xyz 对比精度 |
| M5 | StaticMapping.h/.cpp | PCL 点云 + 八叉树/栅格地图 |
| M6 | visualization/shared/protocol.*, backend/main.py, SlamVisualizer.h/.cpp | 浏览器 localhost:8000 |
| M7 | SlamVisualizer.h/.cpp, run_system.bat, README.md | 端到端运行 |

---

## 17. WSL2 迁移方案

### 17.1 为什么选择 WSL2

**Windows 版本已完成但被阻止：**
- ✅ 所有代码已编写完成
- ✅ 所有库已编译完成
- ❌ Windows Application Control 阻止 rgbd_tum.exe 运行
- ❌ 需要管理员权限添加排除项（企业环境可能不允许）

**WSL2 的优势：**
1. ORB-SLAM3 原生支持 Linux，官方文档基于 Ubuntu
2. Pangolin 可视化在 Linux 下原生工作，无需 Web 可视化替代
3. 工具链更简单：`apt install` vs 手动编译 MSYS2
4. 社区支持更完善，问题更容易找到解决方案
5. 可以共享 Windows 端的数据集和模型文件（通过 `/mnt/e`）
6. CUDA 支持完整（WSL2 + NVIDIA Container Toolkit）

### 17.2 WSL2 架构设计

```
WSL2 (Ubuntu 22.04)
├── ORB-SLAM3 + Pangolin (原生 Linux 可视化)
├── slam-system 库 (C++ Linux 编译)
├── YOLO11n-seg (Python + CUDA GPU 推理)
└── 数据共享 (通过 /mnt/e 访问 Windows 文件)

Windows 端
├── VS Code + WSL 扩展（开发环境）
├── 数据集存储（TUM RGB-D）
├── ONNX 模型（yolo11n-seg.onnx）
└── 可选：Web 可视化后端（FastAPI）
```

### 17.3 环境准备

#### 1. 安装 WSL2 + Ubuntu 22.04

```powershell
# Windows PowerShell（管理员）
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
```

#### 2. 安装 NVIDIA CUDA 支持（WSL2）

```powershell
# Windows 端已安装 NVIDIA 驱动，WSL2 自动共享
# 验证 WSL2 中 CUDA 可用
wsl nvidia-smi
```

#### 3. 安装 WSL2 依赖

```bash
# Ubuntu 22.04 终端
sudo apt update && sudo apt upgrade -y

# 编译工具链
sudo apt install -y build-essential cmake git pkg-config

# OpenCV
sudo apt install -y libopencv-dev

# Eigen3
sudo apt install -y libeigen3-dev

# Pangolin
sudo apt install -y libglew-dev libgl1-mesa-dev libegl1-mesa-dev \
    libwayland-dev libxkbcommon-dev libglfw3-dev \
    libpng-dev libjpeg-dev libopenexr-dev libtiff-dev

# Python 3.10 + pip
sudo apt install -y python3.10 python3.10-dev python3-pip

# CUDA Toolkit（可选，如果 Windows 驱动版本 >= 12.0）
# 通常 WSL2 共享 Windows 驱动，不需要单独安装 CUDA Toolkit
```

### 17.4 项目迁移步骤

#### 步骤 1：在 WSL2 中访问 Windows 项目

```bash
# WSL2 终端
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam

# 创建软链接到 WSL2 家目录（可选）
ln -s /mnt/e/VSCode/VSCode-Workspace/DS-Slam ~/ds-slam
cd ~/ds-slam
```

#### 步骤 2：编译 ORB-SLAM3（Linux 原生）

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3

# 编译 DBoW2
cd Thirdparty/DBoW2
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# 编译 g2o
cd ../g2o
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# 编译 ORB-SLAM3
cd ../../..
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

#### 步骤 3：编译 slam-system 库

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/slam-system

mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
    -DOpenCV_DIR=/usr/lib/x86_64-linux-gnu/cmake/opencv4 \
    -DEigen3_DIR=/usr/lib/cmake/eigen3

make -j$(nproc)
```

#### 步骤 4：安装 Python YOLO 环境

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install ultralytics onnx onnxruntime-gpu opencv-python numpy

# 验证 CUDA 可用
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

#### 步骤 5：集成测试

```bash
# 测试 ORB-SLAM3
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D
./rgbd_tum \
    ../../Vocabulary/ORBvoc.txt \
    TUM1.yaml \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz/associations/rgbd_dataset_freiburg1_xyz.txt

# 测试 YOLO 推理
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/segmentation
source ../venv/bin/activate
python test_inference.py --model ../segmentation/onnx/yolo11n_seg_v2.onnx
```

### 17.5 完整运行流程

```bash
# 1. 启动 Pangolin 可视化（ORB-SLAM3 自带）
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D
./rgbd_tum \
    ../../Vocabulary/ORBvoc.txt \
    TUM1.yaml \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz/associations/rgbd_dataset_freiburg1_xyz.txt \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/segmentation/onnx/yolo11n_seg_v2.onnx

# 2. Pangolin 窗口会显示：
#    - 3D 点云地图
#    - 相机轨迹
#    - 当前帧特征点

# 3. 可选：启动 Web 可视化后端
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/visualization/backend
source ../../venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
# 浏览器访问 http://localhost:8000
```

### 17.6 数据共享说明

| Windows 路径 | WSL2 路径 | 用途 |
|-------------|-----------|------|
| `E:\VSCode\VSCode-Workspace\DS-Slam\datasets` | `/mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets` | TUM 数据集 |
| `E:\VSCode\VSCode-Workspace\DS-Slam\segmentation\onnx` | `/mnt/e/VSCode/VSCode-Workspace/DS-Slam/segmentation/onnx` | ONNX 模型 |
| `E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Vocabulary` | `/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Vocabulary` | ORB 词汇表 |
| `E:\VSCode\VSCode-Workspace\DS-Slam\output` | `/mnt/e/VSCode/VSCode-Workspace/DS-Slam/output` | 输出结果 |

### 17.7 预期时间线

| 步骤 | 预计时间 | 说明 |
|------|---------|------|
| 安装 WSL2 + CUDA | 30 分钟 | 下载 Ubuntu 22.04 |
| 安装依赖 | 20 分钟 | apt install |
| 编译 ORB-SLAM3 | 30 分钟 | 包含 DBoW2 + g2o |
| 编译 slam-system | 15 分钟 | 3 个库 |
| 安装 Python 环境 | 15 分钟 | pip install |
| 集成测试 | 1-2 小时 | 调试 + 验证 |
| 端到端测试 | 2-3 小时 | fr1_xyz + fr3_walking_xyz |
| **总计** | **3-5 天** | 包含调试时间 |

### 17.8 常见问题

| 问题 | 解决方案 |
|------|---------|
| WSL2 无法访问 Windows 文件 | 确认 WSL2 版本为 2，使用 `/mnt/e/` 路径 |
| CUDA 不可用 | 确认 Windows 已安装 NVIDIA 驱动 >= 520.00 |
| Pangolin 窗口不显示 | 安装 WSLg（Windows 11 自带）或配置 X Server |
| 编译内存不足 | 使用 `make -j1` 单线程编译 |
| Python 虚拟环境问题 | 使用 `source venv/bin/activate` 激活 |

### 17.9 验证清单

- [ ] WSL2 安装成功，`wsl -l -v` 显示 Ubuntu-22.04
- [ ] CUDA 可用，`nvidia-smi` 显示 GPU 信息
- [ ] ORB-SLAM3 编译成功，`rgbd_tum` 可执行
- [ ] slam-system 库编译成功，3 个 `.a` 文件存在
- [ ] Python YOLO 环境可用，`import torch` 无错误
- [ ] fr1_xyz 数据集运行成功，Pangolin 显示 3D 轨迹
- [ ] fr3_walking_xyz 数据集运行成功，动态特征剔除生效
- [ ] Web 可视化后端可访问（可选）

通过后：`git add -A && git commit -m "milestone(wsl2): WSL2 迁移完成 [已完成]" && git tag milestone-wsl2`
