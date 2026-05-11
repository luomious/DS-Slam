@echo off
rd /s /q E:\VSCode\VSCode-Workspace\DS-Slam\slam-system\build 2>nul
mkdir E:\VSCode\VSCode-Workspace\DS-Slam\slam-system\build
cd /d E:\VSCode\VSCode-Workspace\DS-Slam\slam-system\build
set PATH=E:\msys64\mingw64\bin;%PATH%
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ..
if %ERRORLEVEL% NEQ 0 (
    echo CMake configure failed
    exit /b 1
)
mingw32-make -j1
