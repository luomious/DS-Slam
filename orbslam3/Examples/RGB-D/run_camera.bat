@echo off
echo ========================================
echo   DS-SLAM USB Camera Real-time Mapping
echo ========================================
echo.

REM Set environment variables
set PATH=E:\msys64\mingw64\bin;%PATH%
set BOOST_ROOT=E:/msys64/mingw64

echo Starting USB Camera SLAM...
echo.
echo Controls:
echo   Press 'q' or ESC - Quit
echo   Press 's'         - Save map
echo   Press 'p'         - Pause/Resume
echo.

cd /d "%~dp0"

REM Check if vocabulary file exists
if not exist "..\..\Vocabulary\ORBvoc.txt" (
    echo [ERROR] Vocabulary file not found: ..\..\Vocabulary\ORBvoc.txt
    pause
    exit /b 1
)

REM Check if camera config file exists
if not exist "Astra_Pro.yaml" (
    echo [ERROR] Camera config file not found: Astra_Pro.yaml
    pause
    exit /b 1
)

echo [1/3] Vocabulary: ..\..\Vocabulary\ORBvoc.txt
echo [2/3] Camera Config: Astra_Pro.yaml
echo [3/3] Camera Index: 0
echo.

REM Run rgbd_camera with Astra Pro config
rgbd_camera.exe ..\..\Vocabulary\ORBvoc.txt Astra_Pro.yaml 0

echo.
echo Program exited.
pause
