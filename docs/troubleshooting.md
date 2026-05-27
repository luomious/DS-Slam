# DS-SLAM 问题解决方案

## 问题清单

### 1. Windows Application Control 阻止 rgbd_tum.exe 运行

**症状：**
```
An Application Control policy has blocked this file from running.
```

**原因：**
- Windows 企业安全策略阻止未签名的可执行文件
- rgbd_tum.exe 是本地编译的未签名程序

**解决方案（按推荐顺序）：**

#### 方案 A：WSL2 迁移（推荐）
- 绕过 Windows 安全策略限制
- ORB-SLAM3 原生支持 Linux
- Pangolin 可视化原生工作
- 工具链更简单
- **预计时间：3-5 天**

**实施步骤：**
1. 安装 WSL2 + Ubuntu 22.04
2. 运行 `scripts/wsl2_setup.sh` 配置环境
3. 运行 `scripts/wsl2_build.sh` 编译项目
4. 运行 `scripts/wsl2_run.sh <数据集路径>` 执行 SLAM

#### 方案 B：添加 Windows Defender 排除项
```powershell
# 以管理员身份运行
Add-MpPreference -ExclusionPath "E:\VSCode\VSCode-Workspace\DS-Slam"
```

**或使用提供的脚本：**
```powershell
# 以管理员身份运行
.\add_defender_exclusion.ps1
```

#### 方案 C：数字签名（企业环境）
- 使用企业代码签名证书对 rgbd_tum.exe 签名
- 需要 IT 部门协助

---

### 2. 批处理脚本编码问题

**症状：**
```
'组件和配置是否就绪' is not recognized as an internal or external command
```

**原因：**
- Windows 批处理文件使用 UTF-8 编码但缺少 BOM
- 中文字符在 cmd.exe 中解析错误

**解决方案：**
- 使用 PowerShell 脚本替代批处理脚本
- 或将批处理文件保存为 ANSI 编码

---

### 3. CMake 配置错误

**症状：**
```
CMake Error: Could not find OpenCV
```

**解决方案：**
```powershell
# 确认 OpenCV 已安装
pacman -Q | grep opencv

# 重新配置 CMake
cd build
rm -rf CMakeCache.txt CMakeFiles/
cmake -G "MinGW Makefiles" `
  -DCMAKE_CXX_COMPILER=E:/msys64/mingw64/bin/clang++.exe `
  -DCMAKE_C_COMPILER=E:/msys64/mingw64/bin/clang.exe `
  -DOpenCV_DIR=E:/msys64/mingw64/lib/cmake/opencv4 ..
```

---

### 4. 编译内存不足

**症状：**
```
g++: fatal error: Killed signal terminated program cc1plus
```

**解决方案：**
```bash
# 使用单线程编译
make -j1

# 或增加交换空间
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### 5. Pangolin 窗口不显示（WSL2）

**症状：**
- SLAM 运行但无可视化窗口

**解决方案：**
```bash
# 确认 WSLg 已启用（Windows 11 自带）
echo $DISPLAY

# 如果为空，设置显示变量
export DISPLAY=:0

# 或安装 X Server（Windows 10）
# 推荐：VcXsrv 或 Xming
```

---

## 推荐工作流

### 开发阶段（Windows）
1. 使用 VS Code + WSL 扩展编辑代码
2. 代码存储在 Windows 文件系统（`E:\VSCode\...`）
3. 版本控制使用 Git

### 编译和运行阶段（WSL2）
1. 在 WSL2 终端中访问 Windows 文件（`/mnt/e/...`）
2. 使用 Linux 原生工具链编译
3. Pangolin 可视化通过 WSLg 显示

### 测试阶段
1. 使用 TUM RGB-D 数据集
2. 运行 `scripts/wsl2_run.sh` 执行 SLAM
3. 使用 EVO 工具评估精度

---

## 快速参考

### WSL2 常用命令
```bash
# 启动 WSL2
wsl

# 查看已安装发行版
wsl -l -v

# 停止 WSL2
wsl --shutdown

# 访问 Windows 文件
cd /mnt/e/VSCode/VSCode-Workspace/DS-Slam
```

### 项目路径映射
| Windows | WSL2 |
|---------|------|
| `E:\VSCode\VSCode-Workspace\DS-Slam` | `/mnt/e/VSCode/VSCode-Workspace/DS-Slam` |
| `E:\VSCode\VSCode-Workspace\DS-Slam\datasets` | `/mnt/e/VSCode/VSCode-Workspace/DS-Slam/datasets` |
| `E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3` | `/mnt/e/VSCode/VSCode-Workspace/DS-Slam/orbslam3` |

### 编译命令
```bash
# 环境配置
./scripts/wsl2_setup.sh

# 编译项目
./scripts/wsl2_build.sh

# 运行 SLAM
./scripts/wsl2_run.sh <数据集路径>
```

---

## 联系和支持

- 项目文档：`agents.md`
- 进度跟踪：`PROGRESS.md`
- WSL2 方案：`agents.md` 第 17 节
