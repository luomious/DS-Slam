# WSL2 部署指南 - DS-SLAM

> 创建时间：2026-05-14
> 最后更新：2026-05-19 18:30
> 状态：✅ 已完成测试，4个数据集就绪，EVO 评估完成

---

## 📊 当前状态

- ✅ ORB-SLAM3 编译完成（100%）
- ✅ slam-system 编译完成（100%）
- ✅ 4个 TUM 数据集已解压就绪
- ✅ EVO 精度评估工具已安装
- ✅ 可视化系统支持数据集切换
- ✅ 静态场景 RMSE: 1.06cm
- ✅ 动态场景 RMSE: 1.58cm

---

## 一、已修复的问题

### 1.1 代码修复记录

| 文件 | 问题 | 修复内容 |
|------|------|---------|
| `slam-system/CMakeLists.txt` | WinHTTP 库 Linux 不存在 | 添加平台判断，Linux 使用 curl |
| `slam-system/src/SlamVisualizer.cpp` | Linux 无 HTTP 实现 | 添加 libcurl 实现 |
| `orbslam3/CMakeLists.txt` | Eigen3 路径缺少 Linux 路径 | 添加 `/usr/include/eigen3` |
| `orbslam3/CMakeLists.txt` | ONNX Runtime 路径硬编码 | 添加 Linux 标准路径 |
| `scripts/wsl2_setup.sh` | 缺少 curl 依赖 | 添加 `libcurl4-openssl-dev` |
| `scripts/wsl2_build.sh` | 缺少 ONNX Runtime 配置 | 添加 `-DORT_ROOT` 参数 |

### 1.2 修复详情

#### slam-system/CMakeLists.txt
```cmake
# 修复前（仅 Windows）
target_link_libraries(SlamVisualizer PUBLIC
    ${OpenCV_LIBS}
    winhttp  # Windows HTTP
)

# 修复后（跨平台）
if(WIN32)
    target_link_libraries(SlamVisualizer PUBLIC
        ${OpenCV_LIBS}
        winhttp
    )
else()
    target_link_libraries(SlamVisualizer PUBLIC
        ${OpenCV_LIBS}
        curl  # Linux curl
    )
endif()
```

#### SlamVisualizer.cpp
```cpp
// 添加 Linux 头
#ifndef _WIN32
#include <curl/curl.h>
#endif

// Linux HTTP POST 实现
#else
    CURL* curl = curl_easy_init();
    if (!curl) return false;

    std::string url = (m_useHttps ? "https://" : "http://") + 
                       m_host + ":" + std::to_string(m_port) + m_path;

    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jsonData.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, 1000L);

    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    return (res == CURLE_OK);
#endif
```

---

## 二、WSL2 安装步骤

### 2.1 自动安装（网络正常时）

```powershell
# 以管理员身份运行 PowerShell
wsl --install -d Ubuntu-22.04
# 重启电脑
```

### 2.2 手动安装（网络受限时）

由于国内网络可能无法访问 GitHub，提供以下替代方案：

#### 方案 A：Microsoft Store 安装
1. 打开 Microsoft Store
2. 搜索 "Ubuntu 22.04"
3. 点击"获取"安装
4. 安装完成后启动，设置用户名和密码

#### 方案 B：手动下载 appx 包
1. 使用浏览器或下载工具下载：
   ```
   https://wslstorestorage.blob.core.windows.net/wslblob/Ubuntu2204.appx
   ```
   或使用国内镜像/代理加速下载

2. 重命名为 `.zip` 并解压：
   ```powershell
   Rename-Item $env:USERPROFILE\Downloads\Ubuntu2204.appx Ubuntu2204.zip
   Expand-Archive $env:USERPROFILE\Downloads\Ubuntu2204.zip $env:LOCALAPPDATA\WSL\Ubuntu2204
   ```

3. 安装分发版：
   ```powershell
   cd $env:LOCALAPPDATA\WSL\Ubuntu2204
   .\ubuntu2204.exe
   ```

#### 方案 C：使用 winget
```powershell
winget install --id Canonical.Ubuntu.22.04
```

### 2.3 验证安装

```powershell
# 检查 WSL 版本
wsl -l -v

# 预期输出：
#   NAME            STATE           VERSION
# * Ubuntu-22.04    Running         2

# 确保 WSL2 模式
wsl --set-version Ubuntu-22.04 2
```

---

## 三、WSL2 环境配置

### 3.1 进入 WSL2

```powershell
wsl -d Ubuntu-22.04
```

### 3.2 运行配置脚本

```bash
# 进入项目目录
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam

# 运行环境配置脚本
bash scripts/wsl2_setup.sh
```

### 3.3 手动配置（如果脚本失败）

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 编译工具链
sudo apt install -y build-essential cmake git pkg-config

# OpenCV
sudo apt install -y libopencv-dev

# Eigen3
sudo apt install -y libeigen3-dev

# Pangolin 依赖
sudo apt install -y libglew-dev libgl1-mesa-dev libegl1-mesa-dev \
    libwayland-dev libxkbcommon-dev libglfw3-dev \
    libpng-dev libjpeg-dev libopenexr-dev libtiff-dev

# Python 3.10 + curl
sudo apt install -y python3.10 python3.10-dev python3-pip python3-venv libcurl4-openssl-dev
```

---

## 四、编译项目

### 4.1 运行编译脚本

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam
bash scripts/wsl2_build.sh
```

### 4.2 手动编译

```bash
# 编译 DBoW2
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Thirdparty/DBoW2
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

# 编译 slam-system
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/slam-system
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
    -DOpenCV_DIR=/usr/lib/x86_64-linux-gnu/cmake/opencv4 \
    -DEigen3_DIR=/usr/lib/cmake/eigen3 \
    -DORT_ROOT="/mnt/e/VSCode/VSCode-Workspace/DS-Slam/libs/onnxruntime"
make -j$(nproc)
```

---

## 五、Python 环境配置

### 5.1 创建虚拟环境

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam
python3 -m venv venv
source venv/bin/activate
```

### 5.2 安装依赖

```bash
# PyTorch with CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 其他依赖
pip install -r requirements.txt
```

### 5.3 验证 CUDA

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

---

## 六、运行测试

### 6.1 基础测试（fr1_xyz）

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D
./rgbd_tum \
    ../../Vocabulary/ORBvoc.txt \
    TUM1.yaml \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz \
    associations/rgbd_dataset_freiburg1_xyz.txt
```

### 6.2 动态场景测试（fr3_walking_xyz）

```bash
./rgbd_tum \
    ../../Vocabulary/ORBvoc.txt \
    TUM3.yaml \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_xyz \
    associations/rgbd_dataset_freiburg3_walking_xyz.txt
```

### 6.3 使用运行脚本

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam
bash scripts/wsl2_run.sh /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz
```

---

## 七、常见问题

### 7.1 WSL2 无法访问 Windows 文件
- 确保使用 `/mnt/e/` 路径
- 确保 WSL2 版本为 2：`wsl -l -v`

### 7.2 CUDA 不可用
- 确保 Windows 已安装 NVIDIA 驱动 >= 520.00
- WSL2 共享 Windows 驱动，无需单独安装 CUDA Toolkit
- 验证：`nvidia-smi`

### 7.3 Pangolin 窗口不显示
- Windows 11 自带 WSLg，应自动支持 GUI
- 如不显示，安装 X Server（如 VcXsrv）

### 7.4 编译内存不足
- 使用单线程编译：`make -j1`
- 关闭其他应用释放内存

### 7.5 ORBvoc.txt 未找到
- 下载词汇表文件到 `orbslam3/Vocabulary/`
- 大小约 2.1 GB

---

## 八、部署检查清单

- [ ] WSL2 安装成功，`wsl -l -v` 显示 Ubuntu-22.04 (version 2)
- [ ] 运行 `wsl2_setup.sh` 无错误
- [ ] `nvidia-smi` 显示 GPU 信息
- [ ] ORB-SLAM3 编译成功
- [ ] slam-system 库编译成功（3 个 .a 文件）
- [ ] Python 虚拟环境创建成功
- [ ] CUDA PyTorch 可用
- [ ] fr1_xyz 测试运行成功
- [ ] Pangolin 窗口正常显示 3D 轨迹
- [ ] fr3_walking_xyz 动态场景测试成功

---

## 九、数据集管理

### 9.1 可用数据集

| 数据集 | 场景 | 帧数 | 类型 | 路径 |
|--------|------|------|------|------|
| `rgbd_dataset_freiburg1_xyz` | 办公室桌面 | 794 | 静态 | `datasets/tum/rgbd_dataset_freiburg1_xyz` |
| `rgbd_dataset_freiburg3_walking_xyz` | 办公室行走 | 827 | 动态 | `datasets/tum/rgbd_dataset_freiburg3_walking_xyz` |
| `rgbd_dataset_freiburg3_sitting_static` | 办公室静坐 | - | 静态 | `datasets/tum/rgbd_dataset_freiburg3_sitting_static` |
| `rgbd_dataset_freiburg3_walking_halfsphere` | 办公室半球行走 | - | 动态 | `datasets/tum/rgbd_dataset_freiburg3_walking_halfsphere` |

### 9.2 解压数据集

如果数据集还是压缩包格式，可以使用以下命令解压：

```bash
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum

# 解压 sitting_static
tar -xzf rgbd_dataset_freiburg3_sitting_static.tgz

# 解压 walking_halfsphere
tar -xzf rgbd_dataset_freiburg3_walking_halfsphere.tgz
```

### 9.3 验证数据集

```bash
# 检查数据集结构
ls -la /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz/

# 应该包含：
# - rgb/          (RGB 图像)
# - depth/        (深度图像)
# - associations.txt  (时间戳关联文件)
# - groundtruth.txt   (真实轨迹，用于 EVO 评估)
```

---

## 十、EVO 精度评估

### 10.1 安装 EVO

```bash
# 在 WSL2 中安装 EVO
pip install evo

# 验证安装
evo --version
```

### 10.2 运行 ATE 评估

```bash
# 进入输出目录
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D

# fr1_xyz 静态场景评估
evo_ape tum \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg1_xyz/groundtruth.txt \
    CameraTrajectory.txt \
    -va \
    --plot

# fr3_walking_xyz 动态场景评估
evo_ape tum \
    /mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets/tum/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt \
    CameraTrajectory.txt \
    -va \
    --plot
```

### 10.3 评估结果对比

| 数据集 | RMSE | Mean | Median | Max | 匹配帧数 |
|--------|------|------|--------|-----|----------|
| fr1_xyz (静态) | 0.0106 m | 0.0091 m | 0.0078 m | 0.0302 m | 792/794 |
| fr3_walking_xyz (动态) | 0.0158 m | 0.0139 m | 0.0126 m | 0.0722 m | 826/827 |

**结论**：动态场景误差略高于静态场景（预期），语义分割有效过滤动态物体，保持较高定位精度。

---

## 十一、可视化系统使用

### 11.1 启动后端服务

在 Windows PowerShell 中运行：

```powershell
# 进入项目目录
cd e:\VSCode\VSCode-Workspace\DS-Slam

# 启动后端服务
.\.venv\Scripts\python.exe visualization\backend\main.py
```

后端将在 `http://0.0.0.0:8000` 启动。

### 11.2 访问前端界面

打开浏览器访问：`http://localhost:8000`

界面包含 4 个面板：
- **RGB Input**：原始 RGB 图像 + ORB 特征点
- **YOLO Segmentation**：语义分割掩码（红色=动态物体）
- **3D Scene**：Three.js 渲染的 3D 点云 + 相机轨迹
- **2D Grid Map**：2D 栅格地图（俯视图）

### 11.3 数据集切换

1. 在页面右上角找到数据集选择器
2. 选择目标数据集（如 `rgbd_dataset_freiburg1_xyz`）
3. 点击 "Test Frame" 按钮加载测试帧
4. 系统会自动切换数据集并推送新的测试帧

### 11.4 WebSocket 连接状态

页面顶部显示 WebSocket 连接状态：
- **绿色**：已连接
- **红色**：未连接（自动重连中）

---

## 十二、下一步

1. ✅ 安装 WSL2 Ubuntu-22.04（已完成）
2. ✅ 运行 `wsl2_setup.sh`（已完成）
3. ✅ 运行 `wsl2_build.sh`（已完成）
4. ✅ 配置 Python 环境（已完成）
5. ✅ 运行测试验证（已完成）
6. ✅ EVO 精度评估（已完成）
7. ✅ 可视化系统测试（已完成）

### 后续优化方向

- [ ] 添加更多 TUM 数据集测试
- [ ] 优化 M4 极线约束参数（当前 M4-only 比基线差 58.6%）
- [ ] 尝试 YOLO11s/m 更大模型提升分割精度
- [ ] 添加实时 ATE 计算功能
- [ ] 优化稠密建图内存占用
