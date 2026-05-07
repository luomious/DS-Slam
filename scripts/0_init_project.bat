@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0.."

echo ================================================
echo  DS-SLAM project initialization
echo ================================================
echo.

echo [1/4] Creating project directories...
for %%d in (data docs libs scripts segmentation slam-system visualization output) do (
    if not exist "%%d" mkdir "%%d"
)

echo.
echo [2/4] Checking Git repository...
if not exist ".git" (
    git --version >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Git was not found in PATH. Skipping git init.
    ) else (
        git init
        git config user.email "dev@ds-slam.local"
        git config user.name "DS-SLAM Dev"
    )
) else (
    echo Git repository already exists.
)

echo.
echo [3/4] Creating Python virtual environment...
if not exist ".venv" (
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv.
        echo Make sure Python 3.12 is installed and visible through the py launcher.
        pause
        exit /b 1
    )
) else (
    echo .venv already exists.
)

echo.
echo [4/4] Optional Python dependency install.
set /p INSTALL_PY="Install Python dependencies now? This can take a while. [y/N]: "
if /i "%INSTALL_PY%"=="y" (
    call scripts\setup_python.bat
) else (
    echo Skipped dependency install. Run scripts\setup_python.bat later if needed.
)

echo.
echo ================================================
echo  Initialization finished
echo ================================================
echo.
pause
