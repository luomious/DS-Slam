@echo off
set PATH=E:\msys64\mingw64\bin;E:\msys64\usr\bin;%PATH%
cd /d E:\VSCode\VSCode-Workspace\DS-Slam\slam-system\build
cmake -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release ..
if %ERRORLEVEL% NEQ 0 exit /b 1
mingw32-make -j1
