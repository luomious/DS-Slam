@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ========================================================================
:: DS-SLAM 系统统一启动脚本
:: 启动可视化后端 + SLAM 系统（端到端运行）
:: ========================================================================

echo ========================================
echo    DS-SLAM 系统启动
echo ========================================
echo.

:: 配置路径
set PROJECT_DIR=%~dp0
set VIZ_DIR=%PROJECT_DIR%visualization
set ORB_DIR=%PROJECT_DIR%orbslam3
set VENV=%PROJECT_DIR%.venv\Scripts
set SLAM_EXE=%ORB_DIR%\Examples\RGB-D\rgbd_tum.exe
set VOCAB=%ORB_DIR%\Vocabulary\ORBvoc.txt

:: 参数检查
if "%1"=="" (
    echo 用法: start_system.bat ^<数据集路径^> ^[关联文件^] ^[ONNX模型^]
    echo.
    echo 示例:
    echo   start_system.bat datasets\tum\rgbd_dataset_freiburg1_xyz
    echo   start_system.bat datasets\tum\rgbd_dataset_freiburg3_walking_xyz associations\fr3_office.txt
    echo.
    echo 可选参数:
    echo   ^<数据集路径^>     TUM 数据集根目录（相对或绝对路径）
    echo   ^[关联文件^]       关联文件路径（默认: associations\fr1_xyz.txt）
    echo   ^[ONNX模型^]       YOLO11n-seg ONNX 模型（可选）
    echo.
    pause
    exit /b 1
)

set DATASET=%1
set ASSOC=%~2
if "%ASSOC%"=="" set ASSOC=associations\fr1_xyz.txt
set ONNX_MODEL=%~3

:: 检查关键文件
if not exist "%VENV%\uvicorn.exe" (
    echo [错误] 未找到 Python 虚拟环境
    echo 请运行: pip install fastapi uvicorn websockets opencv-python
    pause
    exit /b 1
)

if not exist "%SLAM_EXE%" (
    echo [错误] 未找到 SLAM 可执行文件: %SLAM_EXE%
    echo 请先编译 ORB-SLAM3
    pause
    exit /b 1
)

if not exist "%VOCAB%" (
    echo [错误] 未找到词汇表文件: %VOCAB%
    pause
    exit /b 1
)

:: 确定配置文件
set CONFIG=TUM1.yaml
echo %DATASET% | findstr /i "freiburg2" >nul
if !errorlevel! equ 0 set CONFIG=TUM2.yaml
echo %DATASET% | findstr /i "freiburg3" >nul
if !errorlevel! equ 0 set CONFIG=TUM3.yaml

echo [配置] 使用 %CONFIG%
echo [数据集] %DATASET%
echo [关联] %ASSOC%
if not "%ONNX_MODEL%"=="" echo [ONNX] %ONNX_MODEL%
echo.

:: [1/2] 启动可视化后端
echo [1/2] 启动可视化后端...
start "DS-SLAM 可视化后端" cmd /k "cd /d %VIZ_DIR% && %VENV%\uvicorn.exe visualization.backend.main:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

:: [2/2] 启动 SLAM 系统
echo [2/2] 启动 SLAM 系统...
cd /d "%ORB_DIR%\Examples\RGB-D"

if not "%ONNX_MODEL%"=="" (
    start "DS-SLAM 系统" cmd /k "%SLAM_EXE% %VOCAB% %CONFIG% %DATASET% %ASSOC% %ONNX_MODEL%"
) else (
    start "DS-SLAM 系统" cmd /k "%SLAM_EXE% %VOCAB% %CONFIG% %DATASET% %ASSOC%"
)

echo.
echo ========================================
echo    系统已启动
echo ========================================
echo.
echo 可视化界面: http://localhost:8000
echo WebSocket:    ws://localhost:8000/ws/slam
echo.
echo 提示: 关闭所有窗口以停止系统
echo.
pause
