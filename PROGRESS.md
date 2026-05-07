# DS-SLAM Progress

Project path: `E:\VSCode\VSCode-Workspace\DS-Slam`

Last reviewed: 2026-05-07

## Current Stage

项目已推进至 M3 ONNX + C++ 接口集成阶段。M0-M2 全部完成，M3 编译通过但运行时需要进一步调试。

## Milestone Status

| Milestone | Status | Notes |
| --- | --- | --- |
| M0 环境预检 | ✅ 完成 | Git 仓库、脚本、依赖、项目骨架就位 |
| M1 ORB-SLAM3 编译运行 | ✅ 完成 | DLL 方案成功：libORB_SLAM3.dll (6.4MB) + rgbd_tum.exe，TUM fr1/xyz 794帧 exit 0，61 关键帧 |
| M2 语义分割验证 | ✅ 完成 | YOLO11nSeg 模型验证通过，ONNX 导出成功 (173KB opset18)，CPU 推理 25ms |
| M3 ONNX + C++ 集成 | 🔧 调试中 | SemanticSegmentator C++ 实现完成，编译成功，独立测试 35.6ms/帧；ORB-SLAM3 集成版本编译通过，但运行时 exe 静默退出（onnxruntime.dll 未被链接进 libORB_SLAM3.dll） |
| M4 动态特征剔除 | ⬜ 未开始 | 等待 M3 运行时验证 |
| M5 静态密建图 | ⬜ 未开始 | |
| M6 Web 可视化 | ⬜ 脚手架 | FastAPI 后端 + 前端最小原型存在，完整 Three.js 可视化待做 |
| M7 系统集成测试 | ⬜ 未开始 | |

## M1 详细结果

- **构建方案**：SHARED/DLL（libORB_SLAM3.dll + libg2o.dll + libDBoW2.a）
- **编译参数**：`-O0 -j1 -std=c++17 -Wa,-mbig-obj -DEIGEN_DONT_ALIGN_STATICALLY=1 -DEIGEN_MAX_ALIGN_BYTES=0`
- **TUM fr1/xyz 结果**：794 帧全部处理，61 关键帧，837 地图点，跟踪 20ms/帧，exit 0
- **TUM fr3/walking_xyz 基线**：827 帧，189 关键帧，53s，ATE RMSE=0.37m（目标 <0.05m，动态物体严重干扰）

## M2 详细结果

- **模型**：YOLO11nSeg (1,524,311 参数)，架构 UIB backbone → DWR neck → LSCD head
- **ONNX 导出**：yolo11n_seg.onnx (173.2KB)，opset 18，动态轴
- **Python 环境**：Python 3.12.10 + torch 2.11.0+cpu + onnxruntime-gpu 1.25.1
- **ORT Providers**：TensorrtExecutionProvider, CUDAExecutionProvider, CPUExecutionProvider

## M3 详细结果

- **SemanticSegmentator C++ 类**：输入 BGR cv::Mat → 预处理 → ORT 推理 → softmax + 阈值 0.3 + 3×3 max pooling 膨胀 → 输出 uint8 mask
- **独立测试**：test_segmentator.exe 编译成功，walking_xyz 首帧推理 35.6ms（CPU，目标 <50ms ✅）
- **ORB-SLAM3 集成**：修改 System.h/cc、Tracking.cc、rgbd_tum.cc、CMakeLists.txt
- **集成策略**：GrabImageRGBD 入口调用 Segment() → mask 遮盖深度图动态区域 → ORB 特征提取跳过动态对象

## 当前阻塞项

**onnxruntime.dll 未链接进 libORB_SLAM3.dll**：
- `objdump -p libORB_SLAM3.dll` 显示 DLL 依赖列表中没有 onnxruntime.dll
- CMakeLists.txt 中引用了 `${DS_SLAM_LIB_DIR}/libonnxruntime.dll.a`，但链接未生效
- 原因：libonnxruntime.dll.a 只导出 2 个符号，链接器可能未拉入
- 可能修复：CMake 中使用 `-Wl,--no-as-needed` 强制链接，或改用 `target_link_options`
- 修复后需重编译并验证 rgbd_tum.exe 能否正常启动和推理

## 关键技术教训

1. **Eigen 跨 DLL 传递必须禁用静态对齐**：`-DEIGEN_DONT_ALIGN_STATICALLY=1 -DEIGEN_MAX_ALIGN_BYTES=0`
2. **16GB 内存编译大型 C++ 项目需 `-O0 -j1`**：否则 SIGKILL
3. **`-Wa,-mbig-obj`**：MinGW 编译 ORB-SLAM3 大模板文件的必需品
4. **CMakeLists.txt 标志叠加陷阱**：多次 `set(CMAKE_CXX_FLAGS ...)` 累积而非替换
5. **RTX 5060 (Blackwell sm_120)**：PyTorch ≤2.5 CUDA 不支持，使用 CPU PyTorch + ONNX Runtime GPU 路线
6. **ORT C++ 头文件需 C++17**：noexcept on typedef 在 C++14 下不允许
7. **Windows DLL 符号导出**需显式配置 `WINDOWS_EXPORT_ALL_SYMBOLS`

## 关键文件

| 文件 | 用途 |
|------|------|
| `AGENTS.md` | 项目计划（~1015 行，MinGW 迁移后版本） |
| `orbslam3/CMakeLists.txt` | 经多次修改（C++17、mbig-obj、ORT、对齐标志） |
| `orbslam3/include/pangolin/pangolin.h` | Pangolin stub header（禁用可视化） |
| `orbslam3/include/LoopClosing.h` | 修复 bool→int（C++17 禁止 bool++） |
| `slam-system/include/SemanticSegmentator.h` | C++ ORT 语义分割类声明 |
| `slam-system/src/SemanticSegmentator.cpp` | C++ ORT 语义分割类实现 |
| `slam-system/test_segmentator.cpp` | 独立测试程序 |
| `segmentation/onnx/yolo11n_seg.onnx` | YOLO11nSeg ONNX 模型 |
| `libs/onnxruntime/` | ONNX Runtime 预编译库（Win-x64） |
| `datasets/tum/` | TUM 测试数据集（fr1/xyz, fr3/walking_xyz） |
| `orbslam3/build_cmake.bat` | CMake 构建批处理脚本 |
| `orbslam3/run_rgbd.bat` | 运行测试批处理脚本 |

## Immediate Next Steps

1. 修复 onnxruntime.dll 链接问题（`-Wl,--no-as-needed` 或 CMake target_link_options）
2. 重编译 ORB-SLAM3 集成版本
3. 验证 rgbd_tum.exe 能正常启动并执行语义分割
4. 重跑 walking_xyz，验证 ATE 从 0.37m 降至 <0.05m
5. M3 通过后进入 M4 动态特征剔除