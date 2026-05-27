# Windows Application Control 解决方案

## 问题描述

您的系统启用了 **Windows Application Control**（应用程序控制策略），阻止了未签名的可执行文件运行。

错误信息：
```
程序"rgbd_camera.exe"无法运行: An Application Control policy has blocked this file
```

## 解决方案（3选1）

### 方案1：添加Windows Defender排除项（推荐，最简单）

**步骤**：
1. 按 `Win + I` 打开Windows设置
2. 导航到：**隐私和安全性** → **Windows安全中心** → **打开Windows安全中心**
3. 点击 **病毒和威胁防护**
4. 在"病毒和威胁防护设置"下点击 **管理设置**
5. 滚动到 **排除项**，点击 **添加或删除排除项**
6. 点击 **+ 添加排除项** → 选择 **文件夹**
7. 添加：`E:\VSCode\VSCode-Workspace\DS-Slam`
8. 确认后重新运行程序

**验证**：
```powershell
# 在PowerShell中运行以下命令验证排除项是否添加成功
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

### 方案2：使用PowerShell管理员模式添加排除项

**步骤**：
1. 右键点击开始菜单 → 选择 **终端管理员** 或 **Windows PowerShell (管理员)**
2. 运行以下命令：
```powershell
Add-MpPreference -ExclusionPath "E:\VSCode\VSCode-Workspace\DS-Slam"
```
3. 验证：
```powershell
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```

### 方案3：使用WSL2运行（绕过Windows策略）

WSL2是Linux环境，不受Windows Application Control限制。

**步骤**：
1. 在WSL2中编译项目：
```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3
mkdir -p build_linux && cd build_linux
cmake .. -DCMAKE_BUILD_TYPE=Release
make rgbd_camera -j4
```

2. 运行程序：
```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/build_linux/Examples/RGB-D
./rgbd_camera ../../Vocabulary/ORBvoc.txt ../../Examples/RGB-D/Astra_Pro.yaml 0
```

## 运行摄像头测试

### Windows端（添加排除项后）

```powershell
cd E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Examples\RGB-D
$env:PATH = "E:\msys64\mingw64\bin;E:\VSCode\VSCode-Workspace\DS-Slam\slam-system\build;" + $env:PATH
.\rgbd_camera.exe ..\..\Vocabulary\ORBvoc.txt Astra_Pro.yaml 0
```

### WSL2端

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/build_linux/Examples/RGB-D
./rgbd_camera ../../Vocabulary/ORBvoc.txt ../../Examples/RGB-D/Astra_Pro.yaml 0
```

## 控制说明

程序运行后：
- 按 `q` 或 `ESC` - 退出程序
- 按 `s` - 保存点云地图
- 按 `p` - 暂停/恢复跟踪

## 输出文件

程序退出后，会在项目根目录生成以下文件：
- `output_YYYYMMDD_HHMMSS/CameraTrajectory.txt` - 相机轨迹
- `output_YYYYMMDD_HHMMSS/KeyFrameTrajectory.txt` - 关键帧轨迹
- `output_YYYYMMDD_HHMMSS/static_map.ply` - 静态点云地图
- `output_YYYYMMDD_HHMMSS/grid_map.png` - 2D栅格地图

## 故障排除

### 问题1：摄像头无法打开

**检查**：
```powershell
# 列出所有摄像头设备
Get-PnpDevice -Class Camera
```

**解决**：
- 确保摄像头已连接
- 尝试不同的摄像头索引（0, 1, 2...）

### 问题2：词汇文件未找到

**检查**：
```powershell
Test-Path E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Vocabulary\ORBvoc.txt
```

**解决**：
- 确保词汇文件存在
- 检查路径是否正确

### 问题3：配置文件未找到

**检查**：
```powershell
Test-Path E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Examples\RGB-D\Astra_Pro.yaml
```

**解决**：
- 确保配置文件存在
- 检查路径是否正确

## 相机标定

Astra_Pro.yaml中的内参是默认值。为了获得更好的SLAM效果，建议进行相机标定。

### 使用OpenCV标定

1. 打印棋盘格（9x6内角点，方格大小25mm）
2. 采集20-30张不同角度的棋盘格图像
3. 使用OpenCV标定工具计算内参

### 标定结果示例

```yaml
Camera1.fx: 525.0  # 替换为您的标定结果
Camera1.fy: 525.0
Camera1.cx: 320.0
Camera1.cy: 240.0
Camera1.k1: 0.0
Camera1.k2: 0.0
Camera1.p1: 0.0
Camera1.p2: 0.0
```

## 性能优化

### 提高帧率

1. 降低分辨率（640x480 → 320x240）
2. 减少ORB特征点数量（1000 → 500）
3. 禁用语义分割（如果不需要）

### 提高建图质量

1. 增加ORB特征点数量（1000 → 2000）
2. 使用更高分辨率（640x480 → 1280x720）
3. 确保环境光照充足
4. 避免快速移动摄像头

## 联系支持

如果问题仍未解决，请提供以下信息：
1. Windows版本：`winver`
2. PowerShell版本：`$PSVersionTable`
3. 错误日志：运行程序时的完整输出
