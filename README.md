# DS-SLAM: 动态场景语义 SLAM

> 基于论文《基于语义分割与对极约束的动态SLAM研究》的动态场景语义 SLAM 复现项目。

项目路径：`E:\VSCode\VSCode-Workspace\DS-Slam`

## 快速开始

本项目当前以 **Windows 11 + MSYS2 MinGW-w64** 为主线，不再使用 Visual Studio 2022 / vcpkg 作为 M1 阶段的默认构建路线。

```powershell
# 1. 初始化项目结构
.\scripts\0_init_project.bat

# 2. 安装 C++ 依赖（MSYS2 pacman）
.\scripts\1_install_cpp_deps.bat

# 3. 查看 ORBvoc 与 TUM 数据集下载链接
.\scripts\2_download_data.bat

# 4. 编译 ORB-SLAM3（MinGW）
.\scripts\3_build_orbslam3.bat

# 5. 运行 RGB-D 测试
.\scripts\4_run_test.bat
```

## 项目结构

```text
DS-Slam/
├── AGENTS.md                  # 开发指南（主文档）
├── PROGRESS.md                # 里程碑进度跟踪
├── README.md                  # 项目概览
├── M1_build_plan.md           # M1 ORB-SLAM3 MinGW 构建计划
├── data/                      # 测试数据与输出数据
├── datasets/                  # 数据集目录
├── docs/                      # 补充文档与问题记录
├── libs/                      # 预编译依赖
├── orbslam3/                  # ORB-SLAM3 源码（M1）
├── scripts/                   # 初始化、依赖安装、构建、测试脚本
├── segmentation/              # 语义分割模块（M2-M3）
├── slam-system/               # 改进 SLAM 系统（M3-M5）
└── visualization/             # Web 可视化系统（M6）
```

## 里程碑

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M0 | 环境预检与项目初始化 | ✅ 已完成 |
| M1 | ORB-SLAM3 编译运行 | ✅ 已完成 |
| M2 | 轻量语义分割网络验证 | ✅ 已完成 |
| M3 | ONNX 部署与 C++ 接口集成 | 🔧 编译通过，运行时调试中 |
| M4 | 动态特征剔除与几何校验 | ⬜ 未开始 |
| M5 | 静态密建图 | ⬜ 未开始 |
| M6 | Web 可视化系统 | ⬜ 未开始 |
| M7 | 系统集成与测试 | ⬜ 未开始 |

## 环境要求

| 组件 | 要求 |
|------|------|
| 系统 | Windows 11 |
| C++ 工具链 | MSYS2 MinGW-w64 (GCC 15.2.0) |
| CMake | 3.20+ |
| Python | 3.12+ |
| CUDA | 12.x（ONNX Runtime GPU 推理可选） |
| GPU | RTX 5060 Laptop (Blackwell sm_120) |
| Git | 最新稳定版 |

推荐在 `E:\msys64\mingw64.exe` 中安装并使用 C++ 依赖：

```bash
pacman -Sy --noconfirm \
  mingw-w64-x86_64-gcc \
  mingw-w64-x86_64-cmake \
  mingw-w64-x86_64-make \
  mingw-w64-x86_64-eigen3 \
  mingw-w64-x86_64-opencv \
  mingw-w64-x86_64-boost \
  mingw-w64-x86_64-ninja
```

## 核心功能

- 基于 ORB-SLAM3 的 RGB-D SLAM 基线运行
- 通过语义分割识别动态物体区域，输出二值动态掩码
- 使用语义先验与对极几何约束剔除动态特征点
- 复用静态特征与深度信息生成静态点云、八叉树地图和 2D 栅格地图
- 使用 FastAPI + WebSocket + Three.js 统一显示相机画面、语义掩码、轨迹、点云和栅格地图

## 测试数据集

| 序列 | 用途 |
|------|------|
| `fr1_xyz` | 静态基础测试，用于 M1 编译运行验证 |
| `fr3_walking_xyz` | 动态场景核心测试，用于 M4 精度对比 |
| `fr3_sitting_xyz` | 静态对照测试 |

数据集下载入口见 `scripts\2_download_data.bat` 或 `AGENTS.md` 的测试数据集章节。

## 开发规范

- 以 `AGENTS.md` 为最高优先级开发说明
- 分里程碑推进，每个阶段完成后更新 `PROGRESS.md`
- M1 主路线为 MSYS2 MinGW-w64；Visual Studio 2022 / vcpkg 不是当前默认路线
- 不修改 `LocalMapping` 和 `LoopClosing` 线程
- 依赖安装、下载大文件、提交和打标签前先确认当前阶段状态

## 已知问题

- **16GB 内存编译 ORB-SLAM3 需 `-O0 -j1`**：大模板文件（G2oTypes.cc、Optimizer.cc）编译时内存不足会被 SIGKILL
- **Eigen 跨 DLL 对齐**：MinGW 下 Eigen 默认 16/32 字节对齐在 DLL 边界传递时崩溃，需 `-DEIGEN_DONT_ALIGN_STATICALLY=1 -DEIGEN_MAX_ALIGN_BYTES=0`
- **RTX 5060 (sm_120) 不支持 PyTorch ≤2.5 CUDA**：使用 CPU PyTorch + ONNX Runtime GPU 推理路线
- **CMakeLists.txt 标志叠加陷阱**：多次 `set(CMAKE_CXX_FLAGS ...)` 会累积而非替换
- **`-Wa,-mbig-obj`**：MinGW 编译 ORB-SLAM3 大模板文件的必需品