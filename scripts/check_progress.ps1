param(
    [string]$Profile = "dev"
)

$ErrorActionPreference = "SilentlyContinue"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Test-Item($Path) {
    return Test-Path -LiteralPath (Join-Path $Root $Path)
}

function Status($Name, $Ok, $Detail = "") {
    $mark = if ($Ok) { "[OK]" } else { "[--]" }
    if ($Detail) {
        "{0} {1} - {2}" -f $mark, $Name, $Detail
    } else {
        "{0} {1}" -f $mark, $Name
    }
}

Write-Host "DS-SLAM progress check"
Write-Host "Root: $Root"
Write-Host "Profile: $Profile"
Write-Host ""

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "check_config.ps1") -Profile $Profile

Write-Host ""
Write-Host "Milestone artifacts"
Status "M0 project skeleton" ((Test-Item "requirements.txt") -and (Test-Item "scripts\0_init_project.bat")) "requirements and scripts present"
Status "M0 git repository" (Test-Item ".git") "needed before milestone commits/tags"
Status "M2 segmentation modules" ((Test-Item "segmentation\python\models\uib.py") -and (Test-Item "segmentation\python\models\dwr.py") -and (Test-Item "segmentation\python\models\lscd.py")) "UIB/DWR/LSCD"
$hasOnnx = (Get-ChildItem -Path (Join-Path $Root "segmentation") -Filter "*.onnx" -Recurse | Select-Object -First 1) -ne $null
Status "M3 ONNX model" $hasOnnx "segmentation ONNX export"
Status "M6 visualizer backend" (Test-Item "visualization\backend\main.py") "FastAPI entry point"

Write-Host ""
if (-not (Test-Item "orbslam3\Examples\RGB-D\rgbd_tum.exe")) {
    Write-Host "Current stage: M1 build/run is still the active checkpoint."
} elseif (-not $hasOnnx) {
    Write-Host "Current stage: M2/M3 work remains after the ORB-SLAM3 baseline."
} else {
    Write-Host "Current stage: later integration artifacts are present; verify runtime manually."
}
