# DS-SLAM 项目进度跟踪

> 最后更新：2026-05-27 16:00

## 📊 当前状态

**最新 Git 提交**: 项目清理与跨平台编译修复
**远程仓库**: https://github.com/luomious/DS-Slam

**当前阶段**: 阶段 8 - 系统整合与产品化

## ✅ 已完成

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| M0 环境预检 | ✅ | 项目结构、依赖配置完成 |
| M1 ORB-SLAM3 编译 | ✅ | Windows MinGW 编译成功，TUM fr1/xyz 794帧 exit 0 |
| M2 语义分割网络 | ✅ | YOLO11n-seg ONNX 导出完成，CPU 推理 25ms |
| M3 ONNX C++ 集成 | ✅ | SemanticSegmentator PIMPL 实现，6个bug已修 |
| M4 动态特征剔除 | ✅ | 极线约束（ATE 0.37→0.20m，改善45%） |
| M5 静态稠密建图 | ✅ | 纯 OpenCV 实现，PLY 627万点 + 栅格地图 |
| M6 Web 可视化 | ✅ | Three.js + FastAPI + WebSocket + WinHTTP C++客户端 |
| M7 系统集成 | ✅ | SlamVisualizer 集成到 Tracking.cc，统一启动脚本 |
| WSL2 适配 | ✅ | 3个核心文件已修复，支持 Linux 编译 |
| **阶段 8.1 项目清理** | ✅ | 删除编译产物、备份文件、临时脚本 |
| **阶段 8.2 Git历史清理** | ✅ | 从历史中移除大文件（Ubuntu2204.appx 297MB） |
| **阶段 8.3 CMakeLists.txt修复** | ✅ | 移除Windows绝对路径，使用相对路径和环境变量 |
| **阶段 8.4 调试输出优化** | ✅ | 移除每帧调试输出，提升性能 |
| **阶段 8.5 depthForMapping空指针修复** | ✅ | 添加fallback逻辑，避免空矩阵传递 |
| 前后端测试 | ✅ | FastAPI 后端运行正常，API + WebSocket 测试通过 |
| 网页效果测试 | ✅ | 浏览器预览正常，19个WebSocket客户端连接成功 |
| **阶段 5.1 SLAM 基础测试** | ✅ | fr1_xyz 静态数据集，794帧，exit 0 |
| **阶段 5.2 编译产物验证** | ✅ | 所有库文件和可执行文件完整 |
| **阶段 5.3 DS-SLAM 完整测试** | ✅ | fr3_walking_xyz 动态场景，语义分割正常 |
| **阶段 5.4 EVO 精度评估** | ✅ | 静态 RMSE 1.06cm，动态 RMSE 1.58cm |
| **阶段 6.1 GUI 数据集切换** | ✅ | 前端选择器 + 后端 API + 跨平台路径支持 |
| **阶段 6.2 GitHub 推送** | ✅ | 代码提交 + tag 创建 + 远程推送 |
| **阶段 6.3 多数据集支持** | ✅ | 4个 TUM 数据集已解压就绪 |
| **阶段 7.3 多数据集测试** | ✅ | 4数据集全测完，M3+M4组合动态场景改善94-96% |
| **编译修复** | ✅ | SlamVisualizer自动禁用+WinHTTP超时+M4参数调优+rgbd_tum路径修复 |
| **编译脚本** | ✅ | build_ds_slam.sh 解决 WSL2+NTFS 编译卡住问题 |
| **前端 GUI 6 问题修复** | ✅ | 按钮无反应/dynamic_coverage/栅格图变形/进度条位置/相机居中 |
| **前端编码乱码修复** | ✅ | 面板标题emoji乱码/切换数据集同步/动态场景支持 |
| **动态场景信息显示** | ✅ | FPS/动态覆盖率/数据集名称实时显示 |

## 🔧 动态场景信息显示（2026-05-20 15:30）

### 新增功能

| 指标 | 位置 | 说明 |
|------|------|------|
| **FPS** | Header 统计区 | 实时帧率显示，基于 performance.now() 计算 |
| **Dynamic %** | Header 统计区 | 动态场景覆盖率，橙色高亮显示 |
| **Dataset Badge** | Header 右侧 | 当前选中数据集名称，渐变徽章 |

### 修改文件
- `visualization/frontend/index.html` - 添加 dynamic-coverage 和 dataset-badge 元素
- `visualization/frontend/static/js/app_loader.js` - FPS计算逻辑 + 动态覆盖率更新
- `visualization/frontend/static/css/style.css` - 动态统计项样式 + 数据集徽章样式

## 🔧 前端编码乱码修复记录（2026-05-20 15:00）

### 修复的 3 个问题

| # | 问题 | 严重度 | 根因 | 修复方案 |
|---|------|--------|------|----------|
| 1 | 面板标题乱码 | **P1** | HTML文件编码损坏 | 重写index.html，修复所有emoji和中文 |
| 2 | 切换数据集不同步 | **P1** | scene_reset未清空2D面板 | 添加清空RGB/YOLO画布和显示placeholder逻辑 |
| 3 | 动态场景功能 | **P2** | 已有完整YOLO检测逻辑 | 验证支持freiburg3_walking_xyz等动态数据集 |

### 修改文件
- `visualization/frontend/index.html` - 修复乱码，重写整个文件
- `visualization/frontend/static/js/app_loader.js` - scene_reset增加2D面板清空

### 可用数据集
- **静态场景**: `rgbd_dataset_freiburg1_xyz`, `rgbd_dataset_freiburg3_sitting_static`
- **动态场景**: `rgbd_dataset_freiburg3_walking_xyz`, `rgbd_dataset_freiburg3_walking_halfsphere`

## 🔧 前端 GUI 修复记录（2026-05-20 14:30）

### 修复的 6 个问题

| # | 问题 | 严重度 | 根因 | 修复方案 |
|---|------|--------|------|----------|
| 1 | 所有按钮无反应 | **P0** | IIFE 闭包内函数未暴露到 window | 将 6 个按钮函数移到 IIFE 顶部立即暴露 |
| 2 | dynamic_coverage=100% | **P1** | YOLO 叠加图背景误算 | 严格阈值 R>100, B<50, G<50 检测红色动态区域 |
| 3 | YOLO 面板无显示 | **P1** | Test Frame 按钮无效（同 #1） | 同 #1 修复 |
| 4 | 栅格图比例变形 | **P2** | 正方形栅格图在非正方形 canvas 上拉伸 | CSS 强制保持正方形比例 |
| 5 | 进度条位置不对 | **P2** | padding-bottom=50px 缺少 1px 边框补偿 | 改为 51px |
| 6 | 3D 点云相机居中 | **P2** | _autoScaleGrid 只检查轨迹数据 | 同时检查轨迹和稠密点云数据 |

### 修改文件
- `visualization/frontend/static/js/app_loader.js` - 按钮函数暴露 + 相机居中逻辑
- `visualization/backend/main.py` - dynamic_coverage 检测阈值
- `visualization/frontend/static/css/style.css` - 栅格图比例样式
- `visualization/frontend/index.html` - 进度条 padding-bottom

## 🔧 本次修复记录（2026-05-18）

### 1. app_loader.js 修复
- **Three.js 渲染器 z-index 问题**：添加 `position: absolute` + `zIndex: 0` 确保 3D 画布正确显示
- **dense_points_update 消息处理**：新增稠密点云数据接收与渲染逻辑
- **gridmap_update 消息处理**：新增 2D 栅格地图 base64 图片渲染逻辑
- **updateProgress 函数**：确认完整可用

### 2. backend/main.py 修复
- **WebSocket 路由重复注册**：删除第 717 行的重复 `@app.websocket(WS_PATH)` 装饰器（根因）
- **WebSocket 处理器位置错误**：原代码中 ws_slam 的 body 被放在 `list_datasets` 之后成为不可达代码，已修复
- **YOLO 模型路径**：从硬编码 `/mnt/e/.../models/` 改为 `PROJECT_ROOT / "segmentation" / "onnx" / "yolo11n_seg_v2.onnx"`
- **WebSocket 错误处理增强**：添加详细日志和异常捕获
- **dense_points_update 触发 gridmap 更新**：设置 `gridmap_dirty = True`

### 3. 依赖版本修复
- **websockets**: 16.0 → 13.1（兼容 FastAPI/Starlette）
- **starlette**: 1.0.0 → 0.39.2
- **fastapi**: 0.136.1 → 0.115.2
- **uvicorn**: 0.46.0 → 0.29.0

### 4. 测试结果
- ✅ API `/api/status` 正常响应
- ✅ API `/api/push_test_frame` 正常推送测试帧
- ✅ API `/api/latest_frame` 返回帧数据
- ✅ API `/api/datasets` 返回 2 个可用数据集
- ✅ WebSocket TestClient ping/pong 测试通过
- ✅ WebSocket 路由注册验证：1 条 APIWebSocketRoute

### 5. 网页效果测试（2026-05-18 22:30）
- ✅ 后端服务器启动成功 `http://0.0.0.0:8000`
- ✅ 测试帧推送成功（包含图像 + 掩码）
- ✅ 19 个 WebSocket 客户端连接成功
- ✅ 4 个面板正常显示：RGB Input、YOLO Segmentation、3D Scene、2D Grid Map
- ✅ 2 个数据集就绪：fr1_xyz + fr3_walking_xyz

### 6. 阶段 5 完整测试（2026-05-19 17:00）

#### 5.1 SLAM 基础测试
- ✅ ORB-SLAM3 编译完成（100%，生成 `libORB_SLAM3.a` + `rgbd_tum`）
- ✅ fr1_xyz 静态数据集：794 帧全部处理，837 地图点
- ✅ 中位跟踪时间：72ms，平均：74ms
- ✅ 轨迹文件生成：`CameraTrajectory.txt`（82KB，794 帧）

#### 5.2 编译产物验证
- ✅ `libORB_SLAM3.a`：ORB-SLAM3 核心库
- ✅ `libSemanticSegmentator.a`（36K）：语义分割模块
- ✅ `libStaticMapper.a`（20K）：静态稠密建图模块
- ✅ `libSlamVisualizer.a`（109K）：Web 可视化客户端
- ✅ `rgbd_tum`（50M）：RGB-D SLAM 可执行文件
- ✅ `test_segmentator`（38K）：分割测试程序
- ✅ `libonnxruntime.so.1.16.3`（17M）：ONNX Runtime 共享库

#### 5.3 DS-SLAM 完整功能测试
- ✅ 语义分割模型加载：`yolo11n_seg_v2.onnx`
- ✅ fr3_walking_xyz 动态场景：827 帧全部处理
- ✅ 动态物体检测正常：掩码占比 23-34%
- ✅ 静态点云生成：6,476,441 个点（827 关键帧）
- ✅ 中位跟踪时间：79ms，平均：84ms

#### 5.4 EVO 精度评估
- ✅ EVO 工具安装成功（v1.36.4）
- ✅ fr1_xyz 静态场景评估：
  - RMSE: 0.0106 m (1.06 cm)
  - Mean: 0.0091 m
  - Median: 0.0078 m
  - Max: 0.0302 m
  - 匹配帧数：792/794
- ✅ fr3_walking_xyz 动态场景评估：
  - RMSE: 0.0158 m (1.58 cm)
  - Mean: 0.0139 m
  - Median: 0.0126 m
  - Max: 0.0722 m
  - 匹配帧数：826/827
- ✅ 精度对比：动态场景误差略高（预期），语义分割有效过滤动态物体

## 🖥️ WSL2 环境状态

| 组件 | 状态 | 版本 |
|------|------|------|
| Ubuntu-22.04 | ✅ 运行中 | WSL2 |
| GCC | ✅ | 11.4.0 |
| CMake | ✅ | 3.22.1 |
| OpenCV | ✅ | 4.5.4 |
| Eigen3 | ✅ | 3.4.0 |
| Python3 | ✅ | 3.10.12 |
| **Pangolin** | ✅ 已编译安装 | 最新 |
| **ONNX Runtime Linux** | ✅ 已下载 | v1.16.3 |
| **ORB-SLAM3 编译** | ✅ 编译完成 | 100% |
| **slam-system 编译** | ✅ 编译完成 | 100% |
| **EVO 评估工具** | ✅ 已安装 | v1.36.4 |

## 🎯 下一步计划

### 阶段 7：多数据集测试 + 文档完善

| 子阶段 | 状态 | 说明 |
|--------|------|------|
| 7.1 GUI 界面测试 | ✅ 完成 | 后端运行正常，4个数据集检测成功，WebSocket 连接正常 |
| 7.2 GitHub 推送 | ✅ 完成 | 提交 f6fdccb，已推送到 origin/main |
| 7.3 多数据集测试 | ✅ 完成 | 4数据集全测完，M3+M4组合效果极佳 |
| 7.4 SLAM 精度优化 | ✅ 完成 | M4参数调优：ratio 0.85→0.75, threshold 3.0→1.5px, min_inliers<30直接return |
| 7.5 系统效果测试 | 🔄 进行中 | GUI 运行效果测试 |

### 阶段 6 完成总结（已完成）

✅ **阶段 6.1**：GUI 数据集切换功能实现（前端选择器 + 后端 API）
✅ **阶段 6.2**：代码推送到 GitHub（tag: milestone-slam-testing）
✅ **阶段 6.3**：4个 TUM 数据集解压就绪
✅ **阶段 6.4**：文档完善中

## 📁 重要文件位置

| 文件 | 路径 |
|------|------|
| 项目根目录 | `E:\VSCode\VSCode-Workspace\DS-Slam` |
| ORB-SLAM3 源码 | `orbslam3/` |
| slam-system 源码 | `slam-system/` |
| 可视化系统 | `visualization/` |
| WSL2 脚本 | `scripts/wsl2_*.sh` |
| ONNX Runtime (Win) | `libs/onnxruntime/` |
| 数据集 | `datasets/` (需要确认) |
| 输出文件 | `orbslam3/Examples/RGB-D/output/` |

## 🚀 快速启动命令

### Windows 端
```powershell
# 启动可视化后端
cd .venv\Scripts
.\python.exe ..\..\visualization\backend\main.py

# 访问前端
# http://localhost:8000/
```

### WSL2 端
```bash
# 进入项目目录
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam

# 安装依赖
./scripts/wsl2_setup.sh

# 编译项目
./scripts/wsl2_build.sh

# 运行 SLAM
./scripts/wsl2_run.sh <数据集路径>
```

## ⚠️ 注意事项

1. **永远不要删除 cmake 生成文件**（build.make 等）
2. **编译前检查可用内存 ≥ 5GB**
3. **WSL2 通过 /mnt/e 访问 Windows 文件**
4. **ONNX Runtime Linux 已下载到** `libs/onnxruntime-linux/`
5. **Pangolin 已编译安装到** `/usr/local/`

## 🔴 断点记录（2026-05-20 10:45）

**当前断点：阶段 7.5 系统效果测试（GUI 运行）**

### 7.3-7.4 完成总结（2026-05-19 晚）

#### 核心修复
1. **SlamVisualizer 自动禁用**：连续5次POST失败后设 m_disabled=true
2. **WinHTTP 超时**：CONNECT=200ms, SEND=500ms, RECEIVE=500ms
3. **M4 极线约束参数调优**：ratio 0.85→0.75, threshold 3.0→1.5px, min_inliers<30直接return
4. **rgbd_tum.cc M3 路径修复**：从 argv[0] 推导可执行文件目录，自动拼接 ONNX 绝对路径
5. **SendMapPoints 日志限频**：每50次输出一次
6. **编译脚本**：`build_ds_slam.sh` 解决 WSL2+NTFS 编译卡住问题

#### 4 数据集完整精度对比（M3+M4 组合）
| 数据集 | 场景 | ATE RMSE | 基线 ORB-SLAM3 | 改善 |
|--------|------|----------|----------------|------|
| fr1_xyz | 静态 | 0.0102m | ~0.010m | 持平 |
| fr3_sitting_static | 弱动态 | 0.0072m | ~0.007m | 持平 |
| fr3_walking_xyz | 强动态 | 0.0138m | ~0.37m | **96%** |
| fr3_walking_halfsphere | 强动态 | 0.0245m | ~0.42m | **94%** |

#### M4 参数调优效果
- M4-only：1.017m（恶化175%）→ 0.239m（改善35%）
- M3+M4组合：进一步降至 0.014m

#### 编译关键教训
- make 链接失败执行 `Deleting file` 清空目标二进制 → 0 字节
- WSL2+NTFS 下 ld 链接 707MB 静态库需 10-15 分钟
- 必须设 exec timeout ≥ 1800s
- `make -j1` 避免 OOM

### 当前待办
- ⬜ git commit 本轮修复（4项修改 + 编译脚本）
- ⬜ git push 到远程
- ⬜ GUI 运行效果测试（启动后端+前端，跑 SLAM 看实时效果）
- ⬜ 更新 README 论文数据表

### 下一步执行
```bash
# 1. 运行 fr3_sitting_static 数据集测试
wsl -d Ubuntu-22.04 bash -c "cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D && ./rgbd_tum ../../Vocabulary/ORBvoc.txt TUM3.yaml /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_sitting_static /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_sitting_static/associations.txt"

# 2. 运行 fr3_walking_halfsphere 数据集测试
wsl -d Ubuntu-22.04 bash -c "cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D && ./rgbd_tum ../../Vocabulary/ORBvoc.txt TUM3.yaml /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_halfsphere /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_halfsphere/associations.txt"

# 3. 启动可视化后端（Windows 端）
e:\VSCode\VSCode-Workspace\DS-Slam\.venv\Scripts\python.exe e:\VSCode\VSCode-Workspace\DS-Slam\visualization\backend\main.py

# 4. 访问前端查看实时数据
# http://localhost:8000/
```

### 数据集位置
- TUM fr1_xyz: `datasets/tum/rgbd_dataset_freiburg1_xyz/` ✅
- TUM fr3_walking_xyz: `datasets/tum/rgbd_dataset_freiburg3_walking_xyz/` ✅

### 关键文件位置
- 可执行文件: `orbslam3/Examples/RGB-D/rgbd_tum`
- ORB-SLAM3 构建目录: `orbslam3/build/`
- slam-system 构建目录: `slam-system/build/`
- ONNX 模型: `segmentation/onnx/yolo11n_seg_v2.onnx`
- ORBvoc.txt: `orbslam3/Vocabulary/ORBvoc.txt`
- 配置文件: `orbslam3/Examples/RGB-D/TUM1.yaml` / `TUM3.yaml`

## 📝 待办事项

- [x] 安装 WSL2 Pangolin
- [x] 下载 ONNX Runtime Linux
- [x] 编译 WSL2 项目
- [x] 测试 SLAM 系统运行（4 数据集全通过）
- [x] EVO 精度对比测试（M3+M4 动态场景改善 94-96%）
- [x] 编译修复（SlamVisualizer 自动禁用 + WinHTTP 超时 + M4 调优 + 路径修复）
- [ ] git commit + push 本轮修复
- [ ] GUI 运行效果测试
- [ ] 完善 README 论文数据表

## 📊 详细技术结果

### M1 详细结果

- **构建方案**：SHARED/DLL（libORB_SLAM3.dll + libg2o.dll + libDBoW2.a）
- **编译参数**：`-O0 -j1 -std=c++17 -Wa,-mbig-obj -DEIGEN_DONT_ALIGN_STATICALLY=1 -DEIGEN_MAX_ALIGN_BYTES=0`
- **TUM fr1/xyz 结果**：794 帧全部处理，61 关键帧，837 地图点，跟踪 20ms/帧，exit 0
- **TUM fr3/walking_xyz 基线**：827 帧，189 关键帧，53s，ATE RMSE=0.37m（目标 <0.05m，动态物体严重干扰）

### M2 详细结果

- **模型**：YOLO11nSeg (1,524,311 参数)，架构 UIB backbone → DWR neck → LSCD head
- **ONNX 导出**：yolo11n_seg_v2.onnx (11.7MB)，opset 18，动态轴
- **Python 环境**：Python 3.12.10 + torch 2.11.0+cpu + onnxruntime-gpu 1.25.1
- **ORT Providers**：TensorrtExecutionProvider, CUDAExecutionProvider, CPUExecutionProvider

### M3 详细结果

- **SemanticSegmentator C++ 类**：输入 BGR cv::Mat → 预处理 → ORT 推理 → softmax + 阈值 0.3 + 3×3 max pooling 膨胀 → 输出 uint8 mask
- **独立测试**：test_segmentator.exe 编译成功，walking_xyz 首帧推理 35.6ms（CPU，目标 <50ms ✅）
- **ORB-SLAM3 集成**：修改 System.h/cc、Tracking.cc、rgbd_tum.cc、CMakeLists.txt
- **集成策略**：GrabImageRGBD 入口调用 Segment() → mask 遮盖深度图动态区域 → ORB 特征提取跳过动态对象

### M3+M4 测试结果 (2026-05-12)

- **Dataset**: TUM fr3/walking_xyz, 827 帧
- **ATE RMSE**: 0.2027m (Sim(3) Umeyama alignment)
- **Baseline**: 0.3700m → **改善 45.2%**
- **跟踪性能**: 中位 69.4ms/帧，均值 70.5ms/帧
- **语义分割**: 每帧遮盖 25-35% 像素
- **极线过滤**: 每50帧移除 31-43 个动态特征
- **目标**: <0.05m，目前仍超出，需进一步优化

### M5 详细结果 (2026-05-12)

- **技术方案**：纯 OpenCV（替代原 PCL+OctoMap 方案，MSYS2 无 PCL 预编译包且 16GB 内存不够编译）
- **StaticMapper 类**：深度图+RGB+mask+Tcw → 3D 点云 → 世界坐标累积 → PLY 导出 + 2D 栅格地图
- **数据结构**：SimplePoint3D（x,y,z,r,g,b），零外部依赖
- **测试结果**：fr3/walking_xyz 827 帧全部处理，6,270,192 个静态点，PLY 225MB
- **栅格地图**：0.05m 分辨率，5m 范围，俯视图 PNG
- **集成方式**：Tracking.cc GrabImageRGBD 中保存原始深度 → Track 后喂给 StaticMapper
- **关键修复**：Eigen::Matrix → cv::Mat 转换需用 Converter::toCvMat()

### M3 Bug修复记录 (2026-05-12)

| Bug | 严重度 | 描述 | 修复 |
|-----|--------|------|------|
| BUG-1 | 🔴致命 | Mask class index反转：bestClass==0当背景，==1当动态，但COCO person=0 | 重写Segment()支持Ultralytics 80-class格式 |
| BUG-2 | 🔴致命 | 缺少softmax导致class概率错误 | 添加numerically stable softmax |
| BUG-3 | 🔴致命 | 代码假设3输出custom模型，实际yolo11n_seg_v2是2输出Ultralytics格式 | 双模式：outputs.size()==2 Ultralytics / >=3 custom |
| BUG-4 | 🟡中 | Depth map未被mask遮盖，动态物体深度值仍参与优化 | 添加`imDepth.setTo(0, segMask)` |
| BUG-5 | 🟡中 | 形态学膨胀被注释掉 | 启用5×5 kernel dilate |
| BUG-6 | 🟡中 | ONNX路径不一致 | 统一为yolo11n_seg_v2.onnx |

## 🔧 关键技术教训

1. **Eigen 跨 DLL 传递必须禁用静态对齐**：`-DEIGEN_DONT_ALIGN_STATICALLY=1 -DEIGEN_MAX_ALIGN_BYTES=0`
2. **16GB 内存编译大型 C++ 项目需 `-O0 -j1`**：否则 SIGKILL
3. **`-Wa,-mbig-obj`**：MinGW 编译 ORB-SLAM3 大模板文件的必需品
4. **CMakeLists.txt 标志叠加陷阱**：多次 `set(CMAKE_CXX_FLAGS ...)` 累积而非替换
5. **RTX 5060 (Blackwell sm_120)**：PyTorch ≤2.5 CUDA 不支持，使用 CPU PyTorch + ONNX Runtime GPU 路线
6. **ORT C++ 头文件需 C++17**：noexcept on typedef 在 C++14 下不允许
7. **Windows DLL 符号导出**需显式配置 `WINDOWS_EXPORT_ALL_SYMBOLS`

## 📁 关键文件

| 文件 | 用途 | 最后更新 |
|------|------|----------|
| `AGENTS.md` | 项目计划（~1015 行，MinGW 迁移后版本） | - |
| `orbslam3/CMakeLists.txt` | 经多次修改（C++17、mbig-obj、ORT、对齐标志） | - |
| `orbslam3/include/pangolin/pangolin.h` | Pangolin stub header（禁用可视化） | - |
| `orbslam3/include/LoopClosing.h` | 修复 bool→int（C++17 禁止 bool++） | - |
| `slam-system/include/SemanticSegmentator.h` | C++ ORT 语义分割类声明 | - |
| `slam-system/src/SemanticSegmentator.cpp` | C++ ORT 语义分割类实现 | - |
| `slam-system/include/StaticMapper.h` | M5 静态稠密建图类声明 | - |
| `slam-system/src/StaticMapper.cpp` | M5 静态稠密建图类实现 | - |
| `slam-system/src/SlamVisualizer.cpp` | HTTP 可视化客户端（WinHTTP） | 2026-05-17 18:04 |
| `visualization/backend/main.py` | FastAPI + WebSocket 服务端 (34KB) | 2026-05-18 20:05 |
| `visualization/frontend/static/js/app_loader.js` | Three.js 3D 可视化前端 (33KB) | 2026-05-18 21:52 |
| `visualization/frontend/index.html` | 前端入口页面 (8.5KB) | 2026-05-18 21:48 |
| `slam-system/test_segmentator.cpp` | 独立测试程序 | - |
| `segmentation/onnx/yolo11n_seg_v2.onnx` | YOLO11nSeg ONNX 模型 (11.7MB) | - |
| `segmentation/onnx/yolo11m-seg.onnx` | YOLO11mSeg ONNX 模型 (89.9MB) | - |
| `segmentation/onnx/yolo11s-seg.onnx` | YOLO11sSeg ONNX 模型 (40.7MB) | - |
| `libs/onnxruntime/` | ONNX Runtime 预编译库（Win-x64） | - |
| `datasets/tum/` | TUM 测试数据集（fr1/xyz, fr3/walking_xyz） | - |
| `dist/ds-slam/` | 构建产出目录（rgbd_tum.exe + DLL） | 2026-05-17 |
| `CameraTrajectory.txt` | 轨迹输出（794帧） | 2026-05-17 19:29 |
| `KeyFrameTrajectory.txt` | 关键帧轨迹（72帧） | 2026-05-17 19:29 |
| `start_system.bat` | 统一启动脚本（后端 + 前端 + SLAM） | - |
| `scripts/wsl2_*.sh` | WSL2 迁移脚本 | 2026-05-14 |

## 🎯 下一步：系统整合与产品化方案

### 目标
将DS-SLAM打造为一个**完整、易用、可分发**的SLAM系统，降低使用门槛，提升用户体验。

### 核心问题
1. **编译复杂**：需要手动编译多个依赖库（DBoW2、g2o、slam-system、ORB_SLAM3）
2. **配置分散**：YAML配置文件、环境变量、硬编码路径混杂
3. **启动繁琐**：需要手动启动后端、SLAM系统、打开浏览器
4. **缺乏监控**：无法实时了解系统状态、性能指标、错误信息
5. **无安装包**：新用户需要手动配置环境、下载依赖

### 整合方案架构

```
DS-Slam/
├── 📦 installer/                    # 安装包构建
│   ├── windows/                     # Windows安装包（NSIS/Inno Setup）
│   │   ├── setup.iss                # Inno Setup脚本
│   │   └── install.bat              # 一键安装脚本
│   └── linux/                       # Linux安装包（deb/rpm）
│       ├── debian/                  # Debian包配置
│       └── install.sh               # 一键安装脚本
│
├── 🔧 build/                        # 统一构建系统
│   ├── CMakeLists.txt               # 顶层CMake配置
│   ├── build_all.ps1                # Windows统一构建脚本
│   ├── build_all.sh                 # Linux统一构建脚本
│   └── toolchains/                  # 交叉编译工具链
│       ├── mingw64.cmake
│       └── clang.cmake
│
├── ⚙️ config/                       # 统一配置管理
│   ├── ds_slam.yaml                 # 主配置文件
│   ├── profiles/                    # 预设配置
│   │   ├── tum_rgbd.yaml            # TUM RGB-D数据集
│   │   ├── euroc.yaml               # EuRoC数据集
│   │   └── kitti.yaml               # KITTI数据集
│   └── schema.json                  # 配置验证schema
│
├── 🚀 launcher/                     # 系统启动器
│   ├── ds_slam_launcher.py          # Python启动器（跨平台）
│   ├── ds_slam_gui.py               # GUI启动器（可选）
│   └── templates/                   # 启动模板
│       ├── backend.template.yaml
│       └── slam.template.yaml
│
├── 📊 monitor/                      # 系统监控
│   ├── status_monitor.py            # 状态监控服务
│   ├── metrics_collector.py         # 性能指标收集
│   └── dashboard/                   # Web监控面板
│       ├── index.html
│       └── js/
│
├── 📚 docs/                         # 文档系统
│   ├── user_guide.md                # 用户指南
│   ├── developer_guide.md           # 开发者指南
│   ├── api_reference.md             # API参考
│   └── troubleshooting.md           # 故障排除
│
└── 🧪 tests/                        # 测试系统
    ├── unit/                        # 单元测试
    ├── integration/                 # 集成测试
    └── benchmark/                   # 性能基准测试
```

### 实施步骤

#### 阶段 8.6：统一构建系统（1-2天）
1. 创建顶层CMakeLists.txt，统一管理所有子项目
2. 编写build_all.ps1和build_all.sh脚本
3. 支持一键编译所有依赖和主程序
4. 添加编译进度显示和错误处理

**详细实现**：
```powershell
# build_all.ps1 伪代码
param(
    [string]$BuildType = "Release",
    [int]$Jobs = 4
)

$stages = @(
    @{Name="DBoW2"; Dir="orbslam3/Thirdparty/DBoW2"},
    @{Name="g2o"; Dir="orbslam3/Thirdparty/g2o"},
    @{Name="slam-system"; Dir="slam-system"},
    @{Name="ORB_SLAM3"; Dir="orbslam3"}
)

foreach ($stage in $stages) {
    Write-Host "Building $($stage.Name)..."
    Push-Location $stage.Dir
    cmake -B build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=$BuildType
    cmake --build build -j$Jobs
    Pop-Location
}
```

#### 阶段 8.7：统一配置管理（1-2天）
1. 创建ds_slam.yaml主配置文件
2. 支持环境变量覆盖
3. 添加配置验证和默认值
4. 编写配置迁移工具

**配置示例**：
```yaml
# ds_slam.yaml
system:
  name: "DS-SLAM"
  version: "1.0.0"
  
paths:
  vocabulary: "${PROJECT_ROOT}/orbslam3/Vocabulary/ORBvoc.txt"
  onnx_model: "${PROJECT_ROOT}/segmentation/onnx/yolo11n_seg_v2.onnx"
  output_dir: "${PROJECT_ROOT}/output"
  
slam:
  camera:
    type: "pinhole"
    fx: 535.4
    fy: 539.2
    cx: 320.1
    cy: 247.6
    width: 640
    height: 480
    fps: 30
    rgb: true
    depth_factor: 5000.0
  
  orb:
    n_features: 1000
    scale_factor: 1.2
    n_levels: 8
    ini_th_fast: 20
    min_th_fast: 7
  
  segmentation:
    enabled: true
    model_path: "${paths.onnx_model}"
    conf_threshold: 0.3
    
visualization:
  enabled: true
  backend_port: 8080
  websocket_url: "ws://localhost:${visualization.backend_port}/ws/slam"
```

#### 阶段 8.8：一键启动器（2-3天）
1. 开发Python启动器（跨平台）
2. 自动检测环境和依赖
3. 管理进程生命周期
4. 自动打开浏览器

**启动器功能**：
- 环境检查（Python、OpenCV、ONNX Runtime）
- 自动启动可视化后端
- 自动启动SLAM系统
- 进程监控和异常恢复
- 日志收集和显示
- 浏览器自动打开

#### 阶段 8.9：系统监控面板（2-3天）
1. 实时显示系统状态
2. 性能指标收集（FPS、内存、CPU）
3. 错误日志显示
4. 点云和地图可视化

**监控指标**：
- 系统运行状态（运行中/停止/错误）
- 当前帧率（FPS）
- 已处理帧数
- 点云数量
- 内存使用
- CPU使用率
- 语义分割耗时
- 跟踪耗时

#### 阶段 8.11：USB摄像头实时建模（3-5天）
1. 开发USB摄像头采集模块（OpenCV cv::VideoCapture）
2. 支持RGB+深度摄像头（RealSense D435i等）
3. 在线相机标定工具
4. 实时语义分割+点云生成
5. 点云地图保存和导出

**技术方案**：
- **纯RGB摄像头**：单目SLAM（无深度信息，仅轨迹估计）
- **RGB-D摄像头**：RGB-D SLAM（完整3D重建）
- **标定**：使用OpenCV相机标定工具，生成YAML配置文件
- **实时处理**：与数据集模式相同的处理流程，只是数据源改为摄像头

**硬件要求**：
- 普通USB摄像头：仅支持单目SLAM（无深度）
- Intel RealSense D435i/D455：RGB-D+IMU（完整功能）
- Azure Kinect：RGB-D（高质量深度）
- 其他RGB-D摄像头：需适配驱动

**实现步骤**：
1. 创建`rgbd_camera.cc` - USB摄像头采集入口
2. 添加相机标定配置文件生成工具
3. 修改`start_system.bat`支持摄像头模式
4. 添加点云地图保存功能（PLY格式）
5. 编写摄像头使用文档

#### 阶段 8.10：安装包构建（2-3天）
1. Windows安装包（Inno Setup）
2. Linux安装包（deb/rpm）
3. 自动下载依赖（ONNX Runtime、OpenCV）
4. 环境变量配置
5. 开始菜单快捷方式

### 预期效果

| 指标 | 当前 | 目标 |
|------|------|------|
| 编译步骤 | 4-5步手动编译 | 1键编译 |
| 配置复杂度 | 分散在多个文件 | 统一配置文件 |
| 启动步骤 | 3步手动启动 | 1键启动 |
| 新用户上手时间 | 2-3小时 | 10分钟 |
| 系统可观测性 | 无 | 实时监控面板 |

### 风险与挑战
1. **跨平台兼容性**：Windows/Linux/macOS差异
2. **依赖管理**：ONNX Runtime、OpenCV版本兼容
3. **性能开销**：监控面板对SLAM性能的影响
4. **安装包大小**：包含所有依赖后的体积

### 时间估算
- 阶段 8.6-8.10：总计 8-13 天
- 可分阶段交付，每阶段独立可用
