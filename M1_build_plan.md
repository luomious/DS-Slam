# M1: ORB-SLAM3 Windows + MSYS2 MinGW-w64 构建方案

## 目标

在 `E:\VSCode\VSCode-Workspace\DS-Slam` 中使用 **MSYS2 MinGW-w64** 编译并运行 ORB-SLAM3 RGB-D 示例，完成 `fr1_xyz` 静态序列的基础验证。

本阶段不使用 Visual Studio 2022 / vcpkg 作为默认路线。

## 当前状态

- ORB-SLAM3 源码已就绪：`orbslam3/`
- Thirdparty 已就绪：DBoW2、g2o、Sophus
- 系统路线已确定：Windows 11 + MSYS2 MinGW-w64
- Python、Git 已可用
- 待确认：MSYS2 pacman C++ 依赖、ORBvoc、TUM 数据集、MinGW 编译结果

## 参考项目分析

- `huashu996/ORB_SLAM3_Dense_YOLO` 主要面向 Ubuntu 20.04 + ROS，不能直接照搬到当前 Windows MinGW 路线。
- 可借鉴其“动态剔除 + 静态建图”的系统分层思想。
- 当前项目原则：M1 只完成 ORB-SLAM3 基线运行；后续 M4/M5 再在独立模块中加入动态特征剔除和静态建图，不修改 `LocalMapping` / `LoopClosing`。

## MinGW 构建要点

### 1. 工具链

所有 C++ 编译依赖优先通过 MSYS2 MinGW64 环境安装：

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

编译入口使用 `E:\msys64\mingw64.exe`，不要混用 Anaconda、MSVC 或其他 MinGW 安装路径。

### 2. ORB-SLAM3 CMake 适配

`orbslam3/CMakeLists.txt` 需要增加 Windows / MinGW 兼容设置：

```cmake
cmake_minimum_required(VERSION 3.10)
if(WIN32)
    add_definitions(-DWIN32_LEAN_AND_MEAN -DNOMINMAX -D_CRT_SECURE_NO_WARNINGS)
    add_definitions(-D_SILENCE_ALL_CXX17_DEPRECATION_WARNINGS)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wa,-mbig-obj")
endif()
```

### 3. Thirdparty 适配

`Thirdparty/g2o/CMakeLists.txt`：

```cmake
if(MINGW)
    add_definitions(-DG2O_SHARED_LIBS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-libgcc -static-libstdc++")
endif()
```

`Thirdparty/DBoW2/CMakeLists.txt`：

```cmake
if(MINGW)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-libgcc -static-libstdc++")
endif()
```

### 4. Pangolin 策略

Pangolin 不在 MSYS2 pacman 仓库中：

- 若需要本地 3D 窗口，可从源码编译 Pangolin 并安装到 `/mingw64`。
- 若只验证核心跟踪流程，可先跳过本地可视化，后续统一接入 `visualization/` Web 可视化系统。

### 5. 词袋与数据集

- ORBvoc 必须准备到 `orbslam3/Vocabulary/`。
- M1 首个测试序列为 TUM `fr1_xyz`。
- 使用 `scripts\2_download_data.bat` 查看 ORBvoc 和 TUM 下载链接，并用 `scripts\associate.py` 生成 RGB-D associations 文件。

## 推荐构建命令

在 MSYS2 MinGW64 shell 中执行：

```bash
cd /e/VSCode/VSCode-Workspace/DS-Slam/orbslam3
mkdir -p build
cd build
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
mingw32-make -j4
```

或在 Windows 中运行：

```powershell
.\scripts\3_build_orbslam3.bat
```

## 运行验证

在 ORB-SLAM3 编译成功并准备好 ORBvoc / TUM 数据后运行：

```bash
cd /e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/build
./rgbd_tum.exe \
  "../../Vocabulary/ORBvoc.txt" \
  "../../Examples/RGB-D/TUM1.yaml" \
  "../../../data/tum-rgbd_dataset_freiburg1_xyz" \
  "../../../data/tum-rgbd_dataset_freiburg1_xyz/associations/fr1_xyz.txt"
```

成功标准：

- 程序能加载 ORBvoc 和 TUM RGB-D 数据。
- RGB-D 跟踪流程正常运行，无启动即崩溃。
- 若 Pangolin 可用，能看到基础轨迹窗口。

## TODO

- [ ] 安装并确认 MSYS2 pacman C++ 依赖。
- [ ] 准备 `orbslam3/Vocabulary/ORBvoc.txt`。
- [ ] 下载 TUM `fr1_xyz` 数据集并生成 associations 文件。
- [ ] 适配 `orbslam3/CMakeLists.txt` 的 Windows / MinGW 编译参数。
- [ ] 适配 `Thirdparty/g2o` 与 `Thirdparty/DBoW2` 的 MinGW 编译参数。
- [ ] 编译 Thirdparty 依赖。
- [ ] 编译 ORB-SLAM3 主库与 RGB-D 示例。
- [ ] 运行 `fr1_xyz` 完成 M1 基线验证。
