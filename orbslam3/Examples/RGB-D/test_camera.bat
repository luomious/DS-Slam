@echo off
echo ========================================
echo   USB Camera Test
echo ========================================
echo.

REM Set OpenCV path
set PATH=E:\msys64\mingw64\bin;%PATH%

echo Starting camera test...
echo Press 'q' or ESC to exit
echo.

cd /d "%~dp0"
test_usb_camera.exe

pause
