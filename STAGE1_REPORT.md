# 阶段 1 执行报告 - 实时摄像头SLAM优化

> 执行日期：2026-06-03
> 执行人：AI Assistant

## 📊 执行摘要

### ✅ 已完成任务

| 任务 | 状态 | 说明 |
|------|------|------|
| 1.1 代码配置检查 | ✅ | rgbd_camera.cc 和 CMakeLists.txt 配置完整 |
| 1.2 WSL2编译 | ✅ | rgbd_camera 编译成功（50MB） |
| 1.3 依赖验证 | ✅ | libonnxruntime.so + libcurl.so 完整链接 |
| 1.4 SlamVisualizer集成 | ✅ | SendFrame/SendMapPoints/SendDensePoints 已在 Tracking.cc 实现 |
| 1.5 后端服务验证 | ✅ | 后端运行正常（http://127.0.0.1:8300），2个WebSocket客户端连接 |

### ⚠️ 发现问题

#### 问题 1：rgbd_tum core dump

**现象**：
- 运行 TUM 数据集时，SLAM 初始化地图后立即崩溃
- 错误信息：`timeout: the monitored command dumped core`
- 崩溃点：`Creation of new map with last KF id: 0` 之后

**可能原因**：
1. SlamVisualizer HTTP POST 连接超时导致段错误
2. 深度图因子配置问题（TUM3.yaml 中 `DepthMapFactor: 5000.0`）
3. 内存访问越界（Eigen矩阵转换问题）
4. WSL2 + NTFS 文件系统兼容性问题

**建议解决方案**：
- 禁用 SlamVisualizer 测试基础SLAM功能
- 检查深度图因子配置
- 添加更多错误处理和日志
- 使用 valgrind 或 gdb 调试

#### 问题 2：WSL2 无法访问 USB 摄像头

**现象**：
- WSL2 中 `/dev/video*` 设备不存在
- `lsusb` 命令不可用
- WSL2 NAT 模式不支持直接 USB 设备访问

**已实施的解决方案**：
- 创建 `camera_bridge.py` Windows 端摄像头捕获脚本
- 支持模拟深度图生成
- 支持 HTTP POST 推送到后端
- 支持保存 RGB-D 帧到共享目录

---

## 🔧 技术细节

### SlamVisualizer 集成状态

**已实现功能**（Tracking.cc:1625-1672）：
```cpp
// 每帧推送
mpSystem->GetVisualizer()->SendFrame(
    imRGB, segMask, TcwMat, timestamp,
    kfCount, mapPtCount);

// 每10帧推送地图点
mpSystem->GetVisualizer()->SendMapPoints(coords);

// 每5关键帧推送稠密点云
mpSystem->GetVisualizer()->SendDensePoints(coords, colors, totalPoints);
```

**HTTP POST 配置**（SlamVisualizer.cpp）：
- 连接超时：500ms
- 发送/接收超时：3000ms
- 自动禁用：连续5次失败后自动禁用
- 恢复机制：每5秒尝试一次恢复

### 后端服务状态

- **URL**: http://127.0.0.1:8300
- **WebSocket**: /ws/slam
- **状态**: 运行中
- **客户端**: 2个连接
- **API**: /api/status, /api/frame, /api/datasets 等

---

## 📁 新增文件

| 文件 | 路径 | 说明 |
|------|------|------|
| camera_bridge.py | scripts/camera_bridge.py | Windows摄像头捕获桥接脚本 |
| test_rgbd_tum.sh | scripts/test_rgbd_tum.sh | rgbd_tum测试脚本 |

---

## 🎯 下一步计划

### 短期（1-2天）

1. **修复 rgbd_tum core dump**
   - 禁用 SlamVisualizer 测试基础功能
   - 使用 gdb 定位崩溃点
   - 修复内存访问问题

2. **测试 camera_bridge.py**
   - 验证 Windows 摄像头捕获
   - 测试 HTTP POST 推送
   - 验证模拟深度图质量

### 中期（1周）

3. **实现完整实时SLAM流程**
   - Windows 摄像头 → 共享目录 → WSL2 SLAM
   - 或 Windows 摄像头 → HTTP POST → 后端 → 前端

4. **优化关键帧策略**
   - 自适应关键帧选择
   - 减少30-50%关键帧数量

### 长期（2-3周）

5. **集成回环检测**
   - DBoW2 词袋模型
   - 消除累积漂移

6. **地图点管理优化**
   - 局部地图融合
   - 冗余点剔除
   - 点云质量提升40%+

---

## 📝 经验教训

1. **WSL2 USB 限制**：WSL2 无法直接访问 USB 设备，需要 Windows 端桥接
2. **HTTP POST 超时**：SlamVisualizer 的超时设置需要与后端端口匹配
3. **Core dump 调试**：需要使用 gdb 或 valgrind 定位内存问题
4. **深度图因子**：TUM 数据集使用 5000.0 因子，需要正确配置

---

## 🚀 快速启动命令

### 测试 Windows 摄像头桥接
```powershell
# 启动摄像头桥接（Windows端）
python scripts/camera_bridge.py --camera-index 0 --backend-url http://127.0.0.1:8300/api/frame
```

### 测试 rgbd_tum（带正确URL）
```bash
wsl -d Ubuntu-22.04 bash -c "cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D && DS_SLAM_BACKEND_URL=http://127.0.0.1:8300/api/frame ./rgbd_tum ../../Vocabulary/ORBvoc.txt TUM3.yaml /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz/associations.txt"
```

### 启动可视化后端
```powershell
.venv\Scripts\uvicorn.exe visualization.backend.main:app --host 0.0.0.0 --port 8300
```

---

**报告生成时间**: 2026-06-03 18:45
**下次更新**: 修复 rgbd_tum core dump 后
