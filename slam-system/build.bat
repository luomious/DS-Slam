@echo off
cd /d E:\VSCode\VSCode-Workspace\DS-Slam\slam-system\build
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ..
if %ERRORLEVEL% NEQ 0 (
    echo CMake failed
    exit /b 1
)
mingw32-make -j1
