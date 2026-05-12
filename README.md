# DS-SLAM: 动态场景语义 SLAM

> 基于论文《基于语义分割与对极约束的动态SLAM研究》的动态场景语义 SLAM 实现。
>
> 在 ORB-SLAM3 基础上，融合 **语义分割（M3）** 与 **对极几何约束（M4）** 过滤动态场景中的特征点，提升动态环境下的定位精度与建图质量。

## 项目结构

```
DS-Slam/
├── orbslam3/                  # ORB-SLAM3 源码（改进版）
│   ├── src/Tracking.cc        # 核心：M3 语义分割 + M4 对极过滤
│   ├── src/System.cc          # 语义分割器初始化
│   ├── Examples/RGB-D/        # RGB-D 运行配置（TUM 数据集）
│   └── build_clang/           # 编译输出（clang++ 工具链）
├── slam-system/               # 语义分割模块
│   ├── src/SemanticSegmentator.cpp  # ONNX Runtime 推理（PIMPL 模式）
│   └── include/SemanticSegmentator.h
├── segmentation/              # ONNX 模型文件
│   └── onnx/                  # YOLO11-seg 模型（n/s/m 三种规格）
├── visualization/             # Web 可视化系统（Three.js + FastAPI）
│   ├── simple_backend.py      # FastAPI + WebSocket 后端
│   ├── simple_frontend.html   # Three.js 三维场景渲染
│   └── start_visualizer.bat   # 一键启动脚本
├── datasets/                  # TUM RGB-D 数据集
├── scripts/                   # 构建、评估脚本
│   └── eval_ate.py            # ATE 轨迹评估（SE3 对齐）
└── docs/                      # 问题记录与修复报告
```

## 核心机制

### M3：语义分割（动态区域掩码）

- **模型**：YOLO11n-seg（ONNX，11.7MB），推理速度 ~44ms/帧
- **流程**：每帧 RGB 图像 → YOLO 推理 → 输出 person 类二值掩码 → 灰度图对应区域置零
- **效果**：掩码覆盖 1-10% 像素（典型 3-5%），从 ORB 特征提取阶段排除动态区域

### M4：对极几何约束（动态特征过滤）

- **原理**：BFMatcher 特征匹配 + Lowe's ratio test + RANSAC 极线约束
- **流程**：当前帧特征与上一帧匹配 → RANSAC 筛选极线内点 → 非内点标记为 dynamic outlier
- **配置**：ratio=0.85（ORB 二进制描述子推荐值），RANSAC 阈值=3.0px

### M3+M4 协同效应

实验发现 M3 和 M4 各自单独使用都会恶化结果，但组合使用产生正向效果：

| 配置 | ATE RMSE | vs 基线 | 推理耗时 |
|------|----------|---------|----------|
| 无过滤基线 | 0.641m | 基准 | 0.018s |
| M3-only（语义） | 0.716m | +11.7% | 0.060s |
| M4-only（极线） | 1.017m | +58.6% | 0.022s |
| **M3+M4（组合）** | **0.628m** | **-2.0%** | **0.065s** |

原因：M3 掩码遮蔽动态区域后，阻止 M4 对这些区域进行特征匹配，减少了 M4 对静态特征的误杀范围。两个有缺陷的模块互相抵消了对方的副作用。

测试数据集：TUM fr3/walking_xyz（827 帧，含行走人物）

## 快速开始

### 环境要求

| 组件 | 要求 |
|------|------|
| 系统 | Windows 10/11 |
| C++ 工具链 | MSYS2 MinGW-w64 + Clang 19.x |
| CMake | 3.20+ |
| Python | 3.12+（评估脚本） |

### 编译

```powershell
cd orbslam3\build_clang
cmake -G "MinGW Makefiles" -DCMAKE_CXX_COMPILER=E:/msys64/mingw64/bin/clang++.exe ..
mingw32-make -j1 ORB_SLAM3
```

> ⚠️ 16GB 内存机器必须使用 `-j1`，大模板文件（G2oTypes.cc、Optimizer.cc）多线程编译会 OOM。

### 运行 RGB-D 测试

```powershell
cd orbslam3\build_clang
.\rgbd_tum.exe ..\Examples\RGB-D\TUM3.yaml ..\Vocabulary\ORBvoc.txt ..\..\datasets\tum\rgbd_dataset_freiburg3_walking_xyz
```

### 评估 ATE

```powershell
python scripts\eval_ate.py datasets\tum\rgbd_dataset_freiburg3_walking_xyz\groundtruth.txt orbslam3\Examples\RGB-D\CameraTrajectory.txt
```

### 启动可视化系统

```powershell
cd visualization
.\start_visualizer.bat
# 浏览器访问 http://localhost:8080
```

## 已知问题

- **PowerShell 编码陷阱**：`>` 重定向写 UTF-16 LE with BOM，g++ 无法读取。写 C++ 源文件必须用 `write` 工具或 `Out-File -Encoding utf8NoBOM`
- **M4 FilterEpipolar 需优化**：当前 M4-only 比基线差 58.6%，参数调优进行中
- **YAML 嵌套格式**：OpenCV FileStorage 的 `node["child"]` 读取方式要求 YAML 使用嵌套格式而非平面键名

## 参考论文

- Mur-Artal, R., & Tardós, J. D. (2017). ORB-SLAM2: An Open-Source SLAM System for Monocular, Stereo, and RGB-D Cameras. *IEEE Transactions on Robotics*, 33(5), 1255-1262.
- 基于语义分割与对极约束的动态 SLAM 研究
