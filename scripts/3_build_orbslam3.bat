@echo off
chcp 65001 >nul 2>&1
setlocal

echo ================================================
echo  DS-SLAM ORB-SLAM3 build (MinGW)
echo ================================================
echo.

set "MSYS2_EXE=E:\msys64\mingw64.exe"
set "PROJECT_DIR=/e/VSCode/VSCode-Workspace/DS-Slam"

if not exist "%MSYS2_EXE%" (
    echo [ERROR] MSYS2 was not found: %MSYS2_EXE%
    echo Run scripts\1_install_cpp_deps.bat first.
    pause
    exit /b 1
)

if not exist "orbslam3\CMakeLists.txt" (
    echo [ERROR] orbslam3 source tree is missing.
    pause
    exit /b 1
)

start "MSYS2 Build" "%MSYS2_EXE%" -defterm -here -no-start -mingw64 -c "cd %PROJECT_DIR%/orbslam3; mkdir -p build-mingw; cmake -S . -B build-mingw -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release; cmake --build build-mingw -j4; echo; echo Build finished. Expected executable: Examples/RGB-D/rgbd_tum.exe; read _"

echo MSYS2 build window has started.
echo Expected executable after build:
echo   orbslam3\Examples\RGB-D\rgbd_tum.exe
pause
