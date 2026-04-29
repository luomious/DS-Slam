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
Write-Host ""

$hasGit = Test-Item ".git"
$hasVenv = Test-Item ".venv"
$hasOrb = Test-Item "orbslam3\CMakeLists.txt"
$hasVocab = Test-Item "orbslam3\Vocabulary\ORBvoc.txt"
$hasRgbdExe = Test-Item "orbslam3\Examples\RGB-D\rgbd_tum.exe"
$hasFr1 = Test-Item "data\tum-rgbd_dataset_freiburg1_xyz"
$hasFr3Walk = Test-Item "data\tum-rgbd_dataset_freiburg3_walking_xyz"
$hasSeg = Test-Item "segmentation\python\models\uib.py"
$hasOnnx = (Get-ChildItem -Path (Join-Path $Root "segmentation") -Filter "*.onnx" -Recurse | Select-Object -First 1) -ne $null
$hasVisualizer = Test-Item "visualization\backend\main.py"

Status "M0 project skeleton" ((Test-Item "requirements.txt") -and (Test-Item "scripts\0_init_project.bat")) "requirements and scripts present"
Status "M0 git repository" $hasGit "needed before milestone commits/tags"
Status "M0 Python venv" $hasVenv ".venv"
Status "M1 ORB-SLAM3 source" $hasOrb "orbslam3"
Status "M1 ORB vocabulary" $hasVocab "ORBvoc.txt"
Status "M1 RGB-D executable" $hasRgbdExe "build output"
Status "M1 fr1_xyz dataset" $hasFr1 "static baseline"
Status "M4 fr3_walking_xyz dataset" $hasFr3Walk "dynamic benchmark"
Status "M2 segmentation modules" $hasSeg "UIB/DWR/LSCD"
Status "M3 ONNX model" $hasOnnx "segmentation ONNX export"
Status "M6 visualizer backend" $hasVisualizer "FastAPI entry point"

Write-Host ""
if (-not $hasGit) {
    Write-Host "Current stage: M0 is not fully complete because .git is missing."
} elseif (-not $hasRgbdExe -or -not $hasFr1) {
    Write-Host "Current stage: M1 in progress. Build ORB-SLAM3 and run fr1_xyz next."
} elseif (-not $hasSeg) {
    Write-Host "Current stage: M2 not started."
} elseif (-not $hasOnnx) {
    Write-Host "Current stage: M3 not complete."
} elseif (-not $hasVisualizer) {
    Write-Host "Current stage: M4/M5 before visualization."
} else {
    Write-Host "Current stage: visualization/integration work is present. Verify runtime status manually."
}
