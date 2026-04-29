@echo off
chcp 65001 >nul 2>&1
setlocal

echo ================================================
echo  DS-SLAM EVO ATE evaluation
echo ================================================
echo.

python -m pip show evo >nul 2>&1
if errorlevel 1 (
    echo EVO is not installed in the active Python environment.
    set /p INSTALL_EVO="Install evo now? [y/N]: "
    if /i "%INSTALL_EVO%"=="y" (
        python -m pip install evo
    ) else (
        echo Cancelled.
        pause
        exit /b 1
    )
)

echo Usage:
echo   python -m evo_ape tum groundtruth.txt CameraTrajectory.txt -va
echo.
echo Example:
echo   python -m evo_ape tum data\tum-rgbd_dataset_freiburg1_xyz\groundtruth.txt orbslam3\Examples\RGB-D\CameraTrajectory.txt -va
echo.
pause
