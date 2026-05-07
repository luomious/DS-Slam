@echo off
chcp 65001 >nul 2>&1
setlocal

echo ================================================
echo  DS-SLAM EVO ATE evaluation
echo ================================================
echo.

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" -m pip show evo >nul 2>&1
if errorlevel 1 (
    echo EVO is not installed in the DS-SLAM Python environment.
    set /p INSTALL_EVO="Install evo now? [y/N]: "
    if /i "%INSTALL_EVO%"=="y" (
        "%PYTHON_EXE%" -m pip install evo
    ) else (
        echo Cancelled.
        pause
        exit /b 1
    )
)

echo Usage:
echo   "%PYTHON_EXE%" -m evo_ape tum groundtruth.txt CameraTrajectory.txt -va
echo.
echo Example:
echo   "%PYTHON_EXE%" -m evo_ape tum data\tum-rgbd_dataset_freiburg1_xyz\groundtruth.txt orbslam3\Examples\RGB-D\CameraTrajectory.txt -va
echo.
pause
