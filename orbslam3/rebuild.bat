@echo off
set PATH=E:\msys64\mingw64\bin;E:\msys64\usr\bin;%PATH%
cd /d E:\VSCode\VSCode-Workspace\DS-Slam\orbslam3\build
set ORT_DIR=E:\VSCode\VSCode-Workspace\DS-Slam\libs\onnxruntime
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=g++ -DONNXRUNTIME_INCLUDE_DIR="%ORT_DIR%\include" -DONNXRUNTIME_LIBRARY="%ORT_DIR%\lib\onnxruntime.lib"
if %ERRORLEVEL% NEQ 0 (
    echo CMake configure failed
    exit /b 1
)
mingw32-make -j1
if %ERRORLEVEL% NEQ 0 (
    echo Build failed
    exit /b 1
)
echo === Copying DLLs ===
copy /y build\libORB_SLAM3.dll Examples\RGB-D\
copy /y E:\VSCode\VSCode-Workspace\DS-Slam\libs\onnxruntime\bin\onnxruntime.dll Examples\RGB-D\
for %%f in (libgfortran-5.dll libgomp-1.dll libquadmath-0.dll libstdc++-6.dll libgcc_s_seh-1.dll libwinpthread-1.dll libg2o.dll libDBoW2.dll) do (
    if exist build\%%f copy /y build\%%f Examples\RGB-D\
    if exist E:\msys64\mingw64\bin\%%f copy /y E:\msys64\mingw64\bin\%%f Examples\RGB-D\
)
echo === Build complete ===
