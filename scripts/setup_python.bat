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
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        pause
        exit /b 1
    )
) else (
    echo [1/2] .venv already exists.
)

call ".venv\Scripts\Activate.bat"

echo [2/2] Installing Python dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Python environment setup finished.
pause
