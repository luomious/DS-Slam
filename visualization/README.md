# DS-SLAM 三维可视化系统

简化版可视化工具，用于显示 ORB-SLAM3 运行结果的三维轨迹。

## 功能

- **三维轨迹显示**: 显示相机运动轨迹（蓝色线条+点）
- **关键帧显示**: 显示关键帧位置（橙色点）
- **动画播放**: 自动播放相机运动过程
- **交互控制**: 鼠标旋转、缩放、平移视角

## 快速开始

### 1. 启动后端服务器

双击运行 `start_visualizer.bat`，或手动执行：

```bash
cd E:\VSCode\VSCode-Workspace\DS-Slam
.venv\Scripts\uvicorn.exe visualization.backend.main:app --host 0.0.0.0 --port 8000
```

### 2. 打开浏览器访问

```
http://localhost:8000
```

### 3. 查看 SLAM 结果

确保以下文件存在：
- `orbslam3/Examples/RGB-D/CameraTrajectory.txt` - 相机轨迹
- `orbslam3/Examples/RGB-D/KeyFrameTrajectory.txt` - 关键帧轨迹

## 界面说明

| 元素 | 说明 |
|------|------|
| 蓝色线条 | 相机运动轨迹 |
| 蓝色点 | 相机位姿 |
| 橙色点 | 关键帧位置 |
| 红色点 | 当前播放位置 |
| 网格 | 地面参考网格 |
| 坐标轴 | X(红) Y(绿) Z(蓝) |

## 控制按钮

- **相机轨迹**: 显示/隐藏相机轨迹
- **关键帧**: 显示/隐藏关键帧
- **播放动画**: 自动播放运动过程
- **重置视角**: 回到初始视角

## 鼠标操作

- **左键拖动**: 旋转视角
- **右键拖动**: 平移视角
- **滚轮**: 缩放

## 技术栈

- **后端**: Python + FastAPI + WebSocket
- **前端**: HTML5 + Three.js
- **数据格式**: TUM 轨迹格式 (timestamp tx ty tz qx qy qz qw)
