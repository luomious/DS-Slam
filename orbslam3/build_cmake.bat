@echo off
set PATH=E:\msys64\mingw64\bin;E:\msys64\usr\bin;%PATH%
cd /d E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\build
set ORT_DIR=E:\VSCode\VSCode-Workspace\DS-Slam\libs\onnxruntime
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=g++ -DONNXRUNTIME_INCLUDE_DIR="%ORT_DIR%\include" -DONNXRUNTIME_LIBRARY="%ORT_DIR%\lib\onnxruntime.lib"
