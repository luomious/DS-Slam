# DS-SLAM Resource Download Script
# Downloads all required project files to downloads/ directory

$ErrorActionPreference = "Continue"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DownloadsDir = Join-Path $ProjectDir "downloads"

# Ensure downloads directory exists
if (-not (Test-Path $DownloadsDir)) {
    New-Item -ItemType Directory -Path $DownloadsDir -Force | Out-Null
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DS-SLAM Resource Download" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Download function
function Download-File {
    param(
        [string]$Url,
        [string]$OutputFile,
        [string]$Description
    )
    
    if (Test-Path $OutputFile) {
        Write-Host "[SKIP] $Description (already exists)" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "[DOWNLOAD] $Description..." -ForegroundColor Cyan
    Write-Host "  URL: $Url" -ForegroundColor Gray
    Write-Host "  Save to: $OutputFile" -ForegroundColor Gray
    
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutputFile -TimeoutSec 300
        if (Test-Path $OutputFile) {
            $size = [math]::Round((Get-Item $OutputFile).Length / 1MB, 2)
            Write-Host "[DONE] $Description ($size MB)" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[FAIL] $Description - file not created" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "[FAIL] $Description - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

Write-Host "--- 1. WSL2 Ubuntu-22.04 ---" -ForegroundColor Yellow
Download-File `
    -Url "https://aka.ms/wslubuntu2204" `
    -OutputFile "$DownloadsDir\Ubuntu2204.appx" `
    -Description "WSL2 Ubuntu-22.04"

Write-Host ""
Write-Host "--- 2. ONNX Runtime Linux GPU ---" -ForegroundColor Yellow
Download-File `
    -Url "https://github.com/microsoft/onnxruntime/releases/download/v1.16.3/onnxruntime-linux-x64-gpu-1.16.3.tgz" `
    -OutputFile "$DownloadsDir\onnxruntime-linux-x64-gpu-1.16.3.tgz" `
    -Description "ONNX Runtime Linux GPU"

Write-Host ""
Write-Host "--- 3. TUM Dataset fr1_xyz ---" -ForegroundColor Yellow
Download-File `
    -Url "https://vision.in.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz" `
    -OutputFile "$DownloadsDir\rgbd_dataset_freiburg1_xyz.tgz" `
    -Description "TUM fr1_xyz dataset"

Write-Host ""
Write-Host "--- 4. TUM Dataset fr3_walking_xyz ---" -ForegroundColor Yellow
Download-File `
    -Url "https://vision.in.tum.de/rgbd/dataset/freiburg3/rgbd_dataset_freiburg3_walking_xyz.tgz" `
    -OutputFile "$DownloadsDir\rgbd_dataset_freiburg3_walking_xyz.tgz" `
    -Description "TUM fr3_walking_xyz dataset"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Download Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check download results
$SuccessCount = 0
$TotalCount = 4

if (Test-Path "$DownloadsDir\Ubuntu2204.appx") { $SuccessCount++ }
if (Test-Path "$DownloadsDir\onnxruntime-linux-x64-gpu-1.16.3.tgz") { $SuccessCount++ }
if (Test-Path "$DownloadsDir\rgbd_dataset_freiburg1_xyz.tgz") { $SuccessCount++ }
if (Test-Path "$DownloadsDir\rgbd_dataset_freiburg3_walking_xyz.tgz") { $SuccessCount++ }

Write-Host "Results: $SuccessCount/$TotalCount successful" -ForegroundColor $(if ($SuccessCount -eq $TotalCount) { "Green" } else { "Yellow" })
Write-Host ""

if ($SuccessCount -lt $TotalCount) {
    Write-Host "Some downloads failed. Possible reasons:" -ForegroundColor Red
    Write-Host "  1. Network issues (GitHub/TUM may be slow in China)" -ForegroundColor Yellow
    Write-Host "  2. Proxy configuration needed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Re-run this script later to resume (existing files will be skipped)" -ForegroundColor Yellow
} else {
    Write-Host "All files downloaded successfully! Next steps:" -ForegroundColor Green
    Write-Host "  1. Install WSL2: Add-AppxPackage downloads\Ubuntu2204.appx" -ForegroundColor White
    Write-Host "  2. Extract datasets: tar -xzf downloads\*.tgz -C datasets\tum\" -ForegroundColor White
    Write-Host "  3. Run WSL2 setup: wsl bash scripts/wsl2_setup.sh" -ForegroundColor White
}

Write-Host ""
