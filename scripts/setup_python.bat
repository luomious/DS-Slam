@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0.."

echo ================================================
echo  DS-SLAM Python environment setup
echo ================================================
echo.

if not exist ".venv" (
    echo [1/2] Creating .venv...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        echo Make sure Python 3.12 is installed and visible through the py launcher.
        pause
        exit /b 1
    )
) else (
    echo [1/2] .venv already exists.
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

echo [2/2] Installing Python dependencies from requirements.txt...
"%PYTHON_EXE%" -m pip install --upgrade pip setuptools wheel

if "%DS_SLAM_TORCH_INDEX%"=="" (
    set "DS_SLAM_TORCH_INDEX=https://download.pytorch.org/whl/cpu"
)

echo Installing PyTorch from %DS_SLAM_TORCH_INDEX%
"%PYTHON_EXE%" -m pip install torch torchvision torchaudio --index-url "%DS_SLAM_TORCH_INDEX%"
if errorlevel 1 (
    echo [ERROR] Failed to install PyTorch.
    echo For RTX 50-series CUDA testing, try:
    echo   set DS_SLAM_TORCH_INDEX=https://download.pytorch.org/whl/cu128
    echo   scripts\setup_python.bat
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install project dependencies.
    pause
    exit /b 1
)

echo.
echo Python environment setup finished.
echo Python: %PYTHON_EXE%
pause
