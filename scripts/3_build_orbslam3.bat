@echo off
chcp 65001 >nul 2>&1
setlocal

echo ================================================
echo  DS-SLAM ORB-SLAM3 build (config driven)
echo ================================================
echo.

set "PROFILE=%DS_SLAM_PROFILE%"
if "%PROFILE%"=="" set "PROFILE=dev"
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

for /f "usebackq tokens=1,* delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$cfg = & '%PYTHON_EXE%' scripts/print_config.py --profile '%PROFILE%' --format json | ConvertFrom-Json; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; 'MSYS2_EXE=' + $cfg._resolved.toolchain.mingw64_shell.win; 'ORB_ROOT_WIN=' + $cfg._resolved.orbslam3.root.win; 'ORB_ROOT_MSYS=' + $cfg._resolved.orbslam3.root.msys; 'BUILD_DIR_WIN=' + $cfg._resolved.orbslam3.build_dir.win; 'BUILD_DIR_MSYS=' + $cfg._resolved.orbslam3.build_dir.msys; 'BUILD_TYPE=' + $cfg.toolchain.build_type; 'GENERATOR=' + $cfg.toolchain.cmake_generator; 'JOBS=' + $cfg.toolchain.parallel_jobs"`) do (
    set "%%A=%%B"
)

if not defined MSYS2_EXE (
    echo [ERROR] Could not load configuration.
    echo Run: "%PYTHON_EXE%" scripts\print_config.py --profile %PROFILE% --format json
    pause
    exit /b 1
)

if not exist "%MSYS2_EXE%" (
    echo [ERROR] MSYS2 was not found: %MSYS2_EXE%
    echo Update config\local.yaml or config\profiles\%PROFILE%.yaml.
    pause
    exit /b 1
)

if not exist "%ORB_ROOT_WIN%\CMakeLists.txt" (
    echo [ERROR] ORB-SLAM3 source tree is missing:
    echo   %ORB_ROOT_WIN%
    pause
    exit /b 1
)

echo Profile: %PROFILE%
echo MSYS2:   %MSYS2_EXE%
echo Source:  %ORB_ROOT_WIN%
echo Build:   %BUILD_DIR_WIN%
echo.

start "MSYS2 Build" "%MSYS2_EXE%" -defterm -here -no-start -mingw64 -c "cd '%ORB_ROOT_MSYS%'; mkdir -p '%BUILD_DIR_MSYS%'; cmake -S . -B '%BUILD_DIR_MSYS%' -G '%GENERATOR%' -DCMAKE_BUILD_TYPE=%BUILD_TYPE%; cmake --build '%BUILD_DIR_MSYS%' -j%JOBS%; echo; echo Build finished. Expected executable: Examples/RGB-D/rgbd_tum.exe; read _"

echo MSYS2 build window has started.
pause
