@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ================================================
echo  DS-SLAM RGB-D test runner
echo ================================================
echo.

set "MSYS2_EXE=E:\msys64\mingw64.exe"
set "PROJECT_WIN=E:\VSCode\VSCode-Workspace\DS-Slam"
set "PROJECT_MSYS=/e/VSCode/VSCode-Workspace/DS-Slam"
set "EXE_WIN=%PROJECT_WIN%\orbslam3\Examples\RGB-D\rgbd_tum.exe"
set "EXE_MSYS=%PROJECT_MSYS%/orbslam3/Examples/RGB-D/rgbd_tum.exe"
set "VOCAB_WIN=%PROJECT_WIN%\orbslam3\Vocabulary\ORBvoc.txt"
set "VOCAB_MSYS=%PROJECT_MSYS%/orbslam3/Vocabulary/ORBvoc.txt"

if not exist "%MSYS2_EXE%" (
    echo [ERROR] MSYS2 was not found: %MSYS2_EXE%
    pause
    exit /b 1
)

if not exist "%EXE_WIN%" (
    echo [ERROR] rgbd_tum.exe was not found.
    echo Build first with scripts\3_build_orbslam3.bat.
    pause
    exit /b 1
)

if not exist "%VOCAB_WIN%" (
    echo [ERROR] ORB vocabulary was not found:
    echo   %VOCAB_WIN%
    pause
    exit /b 1
)

echo Select sequence:
echo   [1] fr1_xyz             static baseline
echo   [2] fr3_walking_xyz     dynamic benchmark
echo   [3] fr3_sitting_xyz     static control
echo.
set /p choice="Enter choice [1-3]: "

if "%choice%"=="1" (
    set "CAMERA=%PROJECT_MSYS%/orbslam3/Examples/RGB-D/TUM1.yaml"
    set "DATASET_WIN=%PROJECT_WIN%\data\tum-rgbd_dataset_freiburg1_xyz"
    set "DATASET=%PROJECT_MSYS%/data/tum-rgbd_dataset_freiburg1_xyz"
    set "ASSOC_WIN=%PROJECT_WIN%\data\tum-rgbd_dataset_freiburg1_xyz\associations\rgbd_dataset_freiburg1_xyz.txt"
    set "ASSOC=%PROJECT_MSYS%/data/tum-rgbd_dataset_freiburg1_xyz/associations/rgbd_dataset_freiburg1_xyz.txt"
)
if "%choice%"=="2" (
    set "CAMERA=%PROJECT_MSYS%/orbslam3/Examples/RGB-D/TUM3.yaml"
    set "DATASET_WIN=%PROJECT_WIN%\data\tum-rgbd_dataset_freiburg3_walking_xyz"
    set "DATASET=%PROJECT_MSYS%/data/tum-rgbd_dataset_freiburg3_walking_xyz"
    set "ASSOC_WIN=%PROJECT_WIN%\data\tum-rgbd_dataset_freiburg3_walking_xyz\associations\rgbd_dataset_freiburg3_walking_xyz.txt"
    set "ASSOC=%PROJECT_MSYS%/data/tum-rgbd_dataset_freiburg3_walking_xyz/associations/rgbd_dataset_freiburg3_walking_xyz.txt"
)
if "%choice%"=="3" (
    set "CAMERA=%PROJECT_MSYS%/orbslam3/Examples/RGB-D/TUM3.yaml"
    set "DATASET_WIN=%PROJECT_WIN%\data\tum-rgbd_dataset_freiburg3_sitting_xyz"
    set "DATASET=%PROJECT_MSYS%/data/tum-rgbd_dataset_freiburg3_sitting_xyz"
    set "ASSOC_WIN=%PROJECT_WIN%\data\tum-rgbd_dataset_freiburg3_sitting_xyz\associations\rgbd_dataset_freiburg3_sitting_xyz.txt"
    set "ASSOC=%PROJECT_MSYS%/data/tum-rgbd_dataset_freiburg3_sitting_xyz/associations/rgbd_dataset_freiburg3_sitting_xyz.txt"
)

if not defined DATASET (
    echo [ERROR] Invalid choice.
    pause
    exit /b 1
)

if not exist "!DATASET_WIN!" (
    echo [ERROR] Dataset directory was not found:
    echo   !DATASET_WIN!
    pause
    exit /b 1
)

if not exist "!ASSOC_WIN!" (
    echo [ERROR] Association file was not found:
    echo   !ASSOC_WIN!
    echo Generate it with:
    echo   python scripts\associate.py "!DATASET_WIN!"
    pause
    exit /b 1
)

start "DS-SLAM RGB-D" "%MSYS2_EXE%" -defterm -here -no-start -mingw64 -c "'%EXE_MSYS%' '%VOCAB_MSYS%' '%CAMERA%' '%DATASET%' '%ASSOC%'; echo; echo Run finished. Press Enter to close.; read _"

echo SLAM window has started.
pause
