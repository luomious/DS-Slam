@echo off
chcp 65001 >nul
echo ==========================================
echo DS-SLAM 三维可视化系统
echo ==========================================
echo.

set VENV=E:\VSCode\VSCode-Workspace\DS-Slam\.venv\Scripts
set WORKDIR=E:\VSCode\VSCode-Workspace\DS-Slam\visualization

if not exist "%VENV%\uvicorn.exe" (
    echo 错误: 未找到 uvicorn，请先安装依赖
    echo 运行: pip install fastapi uvicorn websockets
    pause
    exit /b 1
)

cd /d "%WORKDIR%"

echo 启动后端服务器...
echo 访问地址: http://localhost:8080
echo.
echo 按 Ctrl+C 停止服务器
echo ==========================================

"%VENV%\uvicorn.exe" simple_backend:app --host 0.0.0.0 --port 8080
