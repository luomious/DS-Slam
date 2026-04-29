@echo off
chcp 65001 >nul 2>&1
setlocal

echo ================================================
echo  DS-SLAM C++ dependency install (MSYS2 pacman)
echo ================================================
echo.

set "MSYS2_EXE=E:\msys64\mingw64.exe"
if not exist "%MSYS2_EXE%" (
    echo [ERROR] MSYS2 was not found: %MSYS2_EXE%
    echo Install MSYS2 first, for example:
    echo   winget install MSYS2.MSYS2 --location E:\msys64
    pause
    exit /b 1
)

echo This will install/update MinGW packages with pacman.
set /p CONFIRM="Continue? [y/N]: "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled.
    pause
    exit /b 0
)

start "MSYS2 Install" "%MSYS2_EXE%" -defterm -here -no-start -mingw64 -c "pacman -Sy --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-make mingw-w64-x86_64-eigen3 mingw-w64-x86_64-opencv mingw-w64-x86_64-boost mingw-w64-x86_64-ninja mingw-w64-x86_64-glib2 mingw-w64-x86_64-gettext mingw-w64-x86_64-winpthreads-git; echo; echo Install finished. Press Enter to close.; read _"

echo MSYS2 install window has started. Wait for pacman to finish.
pause
