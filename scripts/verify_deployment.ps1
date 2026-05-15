# DS-SLAM Deployment Verification Script
# Run in PowerShell

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Errors = 0
$Warnings = 0

function Check-File {
    param($Path, $Description)
    if (Test-Path $Path) {
        Write-Host "[OK] $Description" -ForegroundColor Green
    } else {
        Write-Host "[MISSING] $Description" -ForegroundColor Red
        $script:Errors++
    }
}

function Check-Dir {
    param($Path, $Description)
    if (Test-Path $Path) {
        Write-Host "[OK] $Description" -ForegroundColor Green
    } else {
        Write-Host "[MISSING] $Description" -ForegroundColor Red
        $script:Errors++
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DS-SLAM Deployment Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "--- Core Dependencies ---" -ForegroundColor Yellow
Check-File "$ProjectDir\libs\onnxruntime\include\onnxruntime_cxx_api.h" "ONNX Runtime Headers"
Check-File "$ProjectDir\libs\onnxruntime\lib\libonnxruntime.dll.a" "ONNX Runtime Import Lib"
Check-File "$ProjectDir\libs\onnxruntime\lib\onnxruntime.dll" "ONNX Runtime DLL"

Write-Host ""
Write-Host "--- ORB-SLAM3 ---" -ForegroundColor Yellow
Check-File "$ProjectDir\orbslam3\Vocabulary\ORBvoc.txt" "ORB Vocabulary"
Check-File "$ProjectDir\orbslam3\Examples\RGB-D\rgbd_tum.exe" "SLAM Executable"
Check-File "$ProjectDir\orbslam3\Examples\RGB-D\TUM1.yaml" "TUM1 Config"
Check-File "$ProjectDir\orbslam3\Examples\RGB-D\TUM3.yaml" "TUM3 Config"

Write-Host ""
Write-Host "--- SLAM System Libraries ---" -ForegroundColor Yellow
Check-File "$ProjectDir\slam-system\build\libSlamVisualizer.a" "SlamVisualizer Library"
Check-File "$ProjectDir\slam-system\build\libSemanticSegmentator.a" "SemanticSegmentator Library"
Check-File "$ProjectDir\slam-system\build\libStaticMapper.a" "StaticMapper Library"

Write-Host ""
Write-Host "--- Segmentation Model ---" -ForegroundColor Yellow
Check-File "$ProjectDir\segmentation\onnx\yolo11n_seg_v2.onnx" "YOLO11n-seg ONNX Model"

Write-Host ""
Write-Host "--- Visualization ---" -ForegroundColor Yellow
Check-File "$ProjectDir\visualization\backend\main.py" "FastAPI Backend"
Check-File "$ProjectDir\visualization\frontend\index.html" "Frontend HTML"
Check-File "$ProjectDir\visualization\frontend\static\js\app.js" "Frontend App JS"
Check-File "$ProjectDir\visualization\frontend\static\js\renderer.js" "Frontend Renderer JS"
Check-File "$ProjectDir\visualization\frontend\static\js\websocket.js" "Frontend WebSocket JS"
Check-File "$ProjectDir\visualization\frontend\static\css\style.css" "Frontend CSS"

Write-Host ""
Write-Host "--- Python Environment ---" -ForegroundColor Yellow
Check-File "$ProjectDir\.venv\Scripts\python.exe" "Python Virtual Env"
Check-File "$ProjectDir\.venv\Scripts\uvicorn.exe" "Uvicorn Server"
Check-File "$ProjectDir\.venv\Scripts\fastapi.exe" "FastAPI CLI"

Write-Host ""
Write-Host "--- Configuration ---" -ForegroundColor Yellow
Check-File "$ProjectDir\config\default.yaml" "Default Config"
Check-File "$ProjectDir\requirements.txt" "Python Requirements"
Check-File "$ProjectDir\start_system.bat" "System Startup Script"

Write-Host ""
Write-Host "--- Datasets ---" -ForegroundColor Yellow
Check-Dir "$ProjectDir\datasets\tum\rgbd_dataset_freiburg1_xyz" "TUM fr1_xyz Dataset"
Check-Dir "$ProjectDir\datasets\tum\rgbd_dataset_freiburg3_walking_xyz" "TUM fr3_walking_xyz Dataset"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($Errors -eq 0) {
    Write-Host "  Verification PASSED! All components ready" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "  1. Run add_defender_exclusion.ps1 as Administrator" -ForegroundColor White
    Write-Host "  2. Run start_system.bat <dataset_path>" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "  Verification FAILED! Found $Errors errors" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Please check missing files and re-run verification" -ForegroundColor White
    Write-Host ""
}

Read-Host "Press Enter to continue"
