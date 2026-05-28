@echo off
chcp 65001 >nul
echo ==========================================
echo DS-SLAM Point Cloud Generation
echo ==========================================
echo.

set DATASET_NAME=%1
if "%DATASET_NAME%"=="" (
    echo Usage: %0 ^<dataset_name^>
    echo.
    echo Available datasets:
    dir /b e:\VSCode\VSCode-Workspace\DS-Slam\datasets\TUM\
    exit /b 1
)

set DATASET_PATH=e:\VSCode\VSCode-Workspace\DS-Slam\datasets\TUM\%DATASET_NAME%
set VOCAB_PATH=e:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Vocabulary\ORBvoc.txt
set SETTINGS_PATH=e:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Examples\RGB-D\TUM3.yaml
set ASSOC_PATH=%DATASET_PATH%\associations.txt
set SLAM_BIN=e:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Examples\RGB-D\rgbd_tum.exe
set OUTPUT_DIR=%DATASET_PATH%

echo Dataset: %DATASET_NAME%
echo Output: %OUTPUT_DIR%
echo.

REM Check if dataset exists
if not exist "%DATASET_PATH%" (
    echo ERROR: Dataset not found: %DATASET_PATH%
    exit /b 1
)

REM Check if association file exists
if not exist "%ASSOC_PATH%" (
    echo ERROR: Association file not found: %ASSOC_PATH%
    exit /b 1
)

REM Create output directory
mkdir "%OUTPUT_DIR%\maps" 2>nul

REM Run SLAM
echo Running SLAM...
cd /d e:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\Examples\RGB-D
%SLAM_BIN% %VOCAB_PATH% %SETTINGS_PATH% %DATASET_PATH% %ASSOC_PATH%

echo.
echo ==========================================
echo SLAM Complete, checking output files...
echo ==========================================
if exist "%OUTPUT_DIR%\CameraTrajectory.txt" (
    echo [OK] Trajectory file generated
) else (
    echo [FAIL] Trajectory file not generated
)

if exist "%OUTPUT_DIR%\maps\static_map.ply" (
    for %%F in ("%OUTPUT_DIR%\maps\static_map.ply") do (
        set /a size=%%~zF/1048576
        echo [OK] Point cloud file generated (!size! MB)
    )
) else (
    echo [FAIL] Point cloud file not generated
)

if exist "%OUTPUT_DIR%\maps\grid_map.png" (
    echo [OK] Grid map generated
) else (
    echo [FAIL] Grid map not generated
)

echo.
pause
