@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ================================================
echo  DS-SLAM RGB-D test runner (config driven)
echo ================================================
echo.

set "PROFILE=%DS_SLAM_PROFILE%"
if "%PROFILE%"=="" set "PROFILE=dev"
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

for /f "usebackq tokens=1,* delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$cfg = & '%PYTHON_EXE%' scripts/print_config.py --profile '%PROFILE%' --format json | ConvertFrom-Json; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; 'MSYS2_EXE=' + $cfg._resolved.toolchain.mingw64_shell.win; 'EXE_WIN=' + $cfg._resolved.orbslam3.rgbd_exe.win; 'EXE_MSYS=' + $cfg._resolved.orbslam3.rgbd_exe.msys; 'VOCAB_WIN=' + $cfg._resolved.orbslam3.vocabulary.win; 'VOCAB_MSYS=' + $cfg._resolved.orbslam3.vocabulary.msys"`) do (
    set "%%A=%%B"
)

if not defined MSYS2_EXE (
    echo [ERROR] Could not load configuration.
    pause
    exit /b 1
)

if not exist "%MSYS2_EXE%" (
    echo [ERROR] MSYS2 was not found: %MSYS2_EXE%
    pause
    exit /b 1
)

if not exist "%EXE_WIN%" (
    echo [ERROR] rgbd_tum.exe was not found:
    echo   %EXE_WIN%
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

echo Profile: %PROFILE%
echo Select sequence:
echo   [1] fr1_xyz             static baseline
echo   [2] fr3_walking_xyz     dynamic benchmark
echo   [3] fr3_sitting_xyz     static control
echo.
set /p choice="Enter choice [1-3]: "

if "%choice%"=="1" set "DATASET_KEY=fr1_xyz"
if "%choice%"=="2" set "DATASET_KEY=fr3_walking_xyz"
if "%choice%"=="3" set "DATASET_KEY=fr3_sitting_xyz"

if not defined DATASET_KEY (
    echo [ERROR] Invalid choice.
    pause
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$cfg = & '%PYTHON_EXE%' scripts/print_config.py --profile '%PROFILE%' --format json | ConvertFrom-Json; $d = $cfg._resolved.datasets.'%DATASET_KEY%'; 'DATASET_WIN=' + $d.root.win; 'DATASET_MSYS=' + $d.root.msys; 'ASSOC_WIN=' + $d.association.win; 'ASSOC_MSYS=' + $d.association.msys; 'CAMERA_WIN=' + $d.camera.win; 'CAMERA_MSYS=' + $d.camera.msys"`) do (
    set "%%A=%%B"
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
    echo   "%PYTHON_EXE%" scripts\associate.py "!DATASET_WIN!"
    pause
    exit /b 1
)

if not exist "!CAMERA_WIN!" (
    echo [ERROR] Camera config was not found:
    echo   !CAMERA_WIN!
    pause
    exit /b 1
)

echo Running dataset: %DATASET_KEY%
echo Dataset: !DATASET_WIN!
echo.

start "DS-SLAM RGB-D" "%MSYS2_EXE%" -defterm -here -no-start -mingw64 -c "'%EXE_MSYS%' '%VOCAB_MSYS%' '!CAMERA_MSYS!' '!DATASET_MSYS!' '!ASSOC_MSYS!'; echo; echo Run finished. Press Enter to close.; read _"

echo SLAM window has started.
pause
