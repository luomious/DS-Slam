# DS-SLAM USB Camera Real-time Mapping Launcher
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DS-SLAM USB Camera Real-time Mapping" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set environment variables
$env:BOOST_ROOT = "E:/msys64/mingw64"
$env:PATH = "E:\msys64\mingw64\bin;" + $env:PATH

# Change to script directory
Set-Location $PSScriptRoot

# Check files
$vocabFile = "..\..\Vocabulary\ORBvoc.txt"
$configFile = "Astra_Pro.yaml"

if (-not (Test-Path $vocabFile)) {
    Write-Host "[ERROR] Vocabulary file not found: $vocabFile" -ForegroundColor Red
    pause
    exit 1
}

if (-not (Test-Path $configFile)) {
    Write-Host "[ERROR] Camera config file not found: $configFile" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[1/3] Vocabulary: $vocabFile" -ForegroundColor Green
Write-Host "[2/3] Camera Config: $configFile" -ForegroundColor Green
Write-Host "[3/3] Camera Index: 0" -ForegroundColor Green
Write-Host ""
Write-Host "Controls:" -ForegroundColor Yellow
Write-Host "  Press 'q' or ESC - Quit" -ForegroundColor Yellow
Write-Host "  Press 's'         - Save map" -ForegroundColor Yellow
Write-Host "  Press 'p'         - Pause/Resume" -ForegroundColor Yellow
Write-Host ""
Write-Host "Starting camera..." -ForegroundColor Green
Write-Host ""

# Run rgbd_camera
& .\rgbd_camera.exe $vocabFile $configFile 0

Write-Host ""
Write-Host "Program exited." -ForegroundColor Yellow
pause
