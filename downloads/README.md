# DS-SLAM 项目资源下载清单

> 更新时间：2026-05-14
> 所有下载文件统一存放于：`E:\VSCode\VSCode-Workspace\DS-Slam\downloads\`

---

## 一、必需文件清单

### 1. WSL2 Ubuntu-22.04 分发版

| 项目 | 详情 |
|------|------|
| **大小** | 约 500 MB |
| **用途** | WSL2 Linux 环境 |
| **下载链接** | https://aka.ms/wslubuntu2204 |
| **备用链接** | https://wslstorestorage.blob.core.windows.net/wslblob/Ubuntu2204.appx |
| **存放位置** | `downloads/Ubuntu2204.appx` |
| **安装方式** | 下载后双击安装，或 `Add-AppxPath downloads/Ubuntu2204.appx` |

### 2. TUM RGB-D 数据集

| 项目 | 详情 |
|------|------|
| **大小** | 每个序列约 200-500 MB |
| **用途** | SLAM 测试数据 |
| **存放位置** | `datasets/tum/` |

#### 必需序列

| 序列 | 用途 | 下载链接 |
|------|------|---------|
| fr1_xyz | 基础测试（静态） | https://vision.in.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz |
| fr3_walking_xyz | 动态场景测试 | https://vision.in.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_walking_xyz.tgz |
| fr3_sitting_xyz | 静态对照 | https://vision.in.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_sitting_xyz.tgz |

### 3. ONNX Runtime GPU（Linux）

| 项目 | 详情 |
|------|------|
| **大小** | 约 100 MB |
| **用途** | Linux 下 YOLO 语义分割推理 |
| **版本** | 1.16.3 |
| **下载链接** | https://github.com/microsoft/onnxruntime/releases/download/v1.16.3/onnxruntime-linux-x64-gpu-1.16.3.tgz |
| **存放位置** | `downloads/onnxruntime-linux-x64-gpu-1.16.3.tgz` |
| **解压位置** | `libs/onnxruntime-linux/` |

> 注意：Windows 版 ONNX Runtime 已存在于 `libs/onnxruntime/`，无需重新下载。

### 4. YOLO11n-seg ONNX 模型

| 项目 | 详情 |
|------|------|
| **大小** | 约 10 MB |
| **用途** | 语义分割推理模型 |
| **存放位置** | `segmentation/onnx/yolo11n_seg_v2.onnx` |
| **获取方式** | 通过 M2 阶段训练导出，或从预训练模型转换 |

---

## 二、当前状态

| 文件 | 状态 | 位置 |
|------|------|------|
| ORBvoc.txt | ✅ 已存在 | `orbslam3/Vocabulary/ORBvoc.txt` (138 MB) |
| ONNX Runtime (Windows) | ✅ 已存在 | `libs/onnxruntime/` |
| WSL2 Ubuntu-22.04 | ❌ 需下载 | `downloads/Ubuntu2204.appx` |
| TUM 数据集 | ❓ 需检查 | `datasets/tum/` |
| ONNX Runtime (Linux) | ❌ 需下载 | `downloads/onnxruntime-linux-x64-gpu-1.16.3.tgz` |
| YOLO 模型 | ❓ 需检查 | `segmentation/onnx/` |

---

## 三、下载命令

### 3.1 WSL2 Ubuntu-22.04

```powershell
# 方式 1：使用 Invoke-WebRequest
Invoke-WebRequest -Uri "https://aka.ms/wslubuntu2204" -OutFile "downloads/Ubuntu2204.appx"

# 方式 2：使用浏览器下载后移动到 downloads/ 目录
```

### 3.2 ONNX Runtime Linux GPU

```powershell
Invoke-WebRequest -Uri "https://github.com/microsoft/onnxruntime/releases/download/v1.16.3/onnxruntime-linux-x64-gpu-1.16.3.tgz" -OutFile "downloads/onnxruntime-linux-x64-gpu-1.16.3.tgz"
```

### 3.3 TUM 数据集

```powershell
# fr1_xyz
Invoke-WebRequest -Uri "https://vision.in.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz" -OutFile "downloads/rgbd_dataset_freiburg1_xyz.tgz"

# fr3_walking_xyz
Invoke-WebRequest -Uri "https://vision.in.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_walking_xyz.tgz" -OutFile "downloads/rgbd_dataset_freiburg3_walking_xyz.tgz"
```

---

## 四、下载后操作

### 4.1 安装 WSL2 Ubuntu-22.04

```powershell
# 安装分发版
Add-AppxPackage downloads/Ubuntu2204.appx

# 启动并设置用户名密码
ubuntu2204.exe
```

### 4.2 解压 ONNX Runtime Linux

```bash
# 在 WSL2 中执行
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam
mkdir -p libs/onnxruntime-linux
tar -xzf downloads/onnxruntime-linux-x64-gpu-1.16.3.tgz -C libs/onnxruntime-linux --strip-components=1
```

### 4.3 解压 TUM 数据集

```powershell
# 创建目录
New-Item -ItemType Directory -Path "datasets/tum" -Force

# 解压（需要 7-Zip 或 tar）
tar -xzf downloads/rgbd_dataset_freiburg1_xyz.tgz -C datasets/tum/
tar -xzf downloads/rgbd_dataset_freiburg3_walking_xyz.tgz -C datasets/tum/
```

---

## 五、一键下载脚本

运行 `scripts/download_resources.ps1` 可自动下载所有资源。
