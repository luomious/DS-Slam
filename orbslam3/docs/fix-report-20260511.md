# DS-SLAM 项目修复报告 — 2026-05-11 22:00

## 修复结果
**状态：✅ 项目从阻塞状态恢复**

rgbd_tum.exe 完整运行 fr1/xyz 数据集 (794帧)，exit code=0。
- 语义分割器加载成功
- M4 极线过滤正常工作
- 轨迹文件已保存 (CameraTrajectory.txt: 794行, KeyFrameTrajectory.txt: 68行)
- 中位跟踪时间 99ms/帧

## 发现的漏洞与修复

### 1. 🔴 DBoW2 静态/动态库混用（根因）

**问题**：DBoW2 CMakeLists.txt 声明为 STATIC 库，但 Thirdparty/DBoW2/lib/ 目录残留了之前构建的 `libDBoW2.dll` (209KB) + `libDBoW2.dll.a` (84KB)。cmake `find_library` 优先找到 `.dll.a` 导入库，导致 libORB_SLAM3.dll 的导入表仍然依赖 `libDBoW2.dll`。运行时找不到该 DLL，程序崩溃。

**表现**：STATUS_ACCESS_VIOLATION (0xC000000B)，掩盖了真实原因（缺失 DLL）。

**修复**：
- CMakeLists.txt: `find_library` 改为直接指定静态库路径 `set(DBOW2_LIB "...libDBoW2.a")`
- 删除 Thirdparty/DBoW2/lib/ 下的 .dll 和 .dll.a 文件

### 2. 🟡 CMakeLists.txt 编译标志累积

**问题**：所有 `set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ...")` 在 cmake 缓存基础上累加。导致 `-O1 + -O2 + -O3` 叠加、`-Wa,-mbig-obj` 重复。

**修复**：用 `CACHE STRING "" FORCE` 覆盖缓存值，避免累积。

### 3. 🟡 未提交的修改文件

当前有 6 个修改文件 + 10 个未跟踪文件。核心修改：
- CMakeLists.txt（标志修复 + DBoW2 静态链接）
- Tracking.cc（M3 + M4 代码）
- SemanticSegmentator.cpp（注释添加）
- ORBmatcher.cc, FORB.cpp（stdint.h 修复）

### 4. 🟢 关联文件路径

TUM 数据集关联文件在 `E:\VSCode\VSCode-Workspace\DS-Slam\datasets\tum\rgbd_dataset_freiburg1_xyz\associations.txt`，不在 `E:\datasets\`。

## 根本原因分析：项目为什么反复卡住？

核心问题：**ORB-SLAM3 是为 Linux/GCC 设计的，在 Windows/MinGW/clang 环境下构建系统行为不可预测。**

叠加因素：
1. **遗留构建产物污染**：多次 cmake configure 之间，旧的 .dll、.dll.a 文件未清理，导致 `find_library` 找到错误版本
2. **CMakeLists.txt 标志管理不严谨**：用 append 而非 replace，导致标志在多次构建间累积恶化
3. **16GB RAM 限制**：迫使使用手动逐文件编译（绕过 cmake），引入 `ar` 操作不彻底、符号重复等新问题
4. **错误码掩盖真实原因**：Windows 的 0xC000000B 看起来像内存错误，实际上是 DLL 加载失败

## 建议

### 短期（本次会话可做）
1. **提交当前修复**：git commit CMakeLists.txt 和 DBoW2 清理
2. **运行 ATE 评估**：验证 fr1/xyz 的精度是否正常
3. **测试 walking_xyz 动态场景**

### 中期
4. **清理旧文件**：Tracking.cc.new, Tracking.cc.tmp, Tracking_m4only.cc, temp_edit.ps1
5. **统一 .bat 构建脚本**：更新 build_cmake.bat 使用新的 cmake 命令

### 长期
6. **考虑迁移到 WSL2**：ORB-SLAM3 在 Linux 下原生编译，避免 MinGW 兼容性问题
7. **或者使用 MSVC**：cl.exe 编译 ORB-SLAM3，不依赖 MinGW

## 关键文件

| 文件 | 修改内容 |
|------|---------|
| orbslam3/CMakeLists.txt | 标志 FORCE 覆盖 + DBoW2 静态链接 |
| orbslam3/Thirdparty/DBoW2/lib/ | 删除 libDBoW2.dll 和 .dll.a |
| orbslam3/src/Tracking.cc | M3 (segMask) + M4 (FilterEpipolar) |
