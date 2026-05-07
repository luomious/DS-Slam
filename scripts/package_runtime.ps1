param(
    [string]$Profile = "dev",
    [string]$Destination = "dist/ds-slam"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

function Copy-IfExists($Source, $TargetDir) {
    if (Test-Path -LiteralPath $Source) {
        New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
        Copy-Item -LiteralPath $Source -Destination $TargetDir -Force
        Write-Host "[COPY] $Source -> $TargetDir"
    } else {
        Write-Host "[SKIP] $Source"
    }
}

function Copy-DirectoryContents($SourceDir, $TargetDir) {
    if (Test-Path -LiteralPath $SourceDir) {
        New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
        Get-ChildItem -LiteralPath $SourceDir -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $TargetDir -Recurse -Force
        }
        Write-Host "[COPY] $SourceDir -> $TargetDir"
    } else {
        Write-Host "[SKIP] $SourceDir"
    }
}

function Copy-ConfigFiles($SourceDir, $TargetDir) {
    if (Test-Path -LiteralPath $SourceDir) {
        New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
        Get-ChildItem -LiteralPath $SourceDir -Force | Where-Object { $_.Name -ne "local.yaml" } | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $TargetDir -Recurse -Force
        }
        Write-Host "[COPY] $SourceDir -> $TargetDir (local.yaml excluded)"
    } else {
        Write-Host "[SKIP] $SourceDir"
    }
}

$json = & $Python scripts/print_config.py --profile $Profile --format json --write-runtime build/runtime_config.json
if ($LASTEXITCODE -ne 0) {
    Write-Host $json
    throw "Could not load configuration."
}
$cfg = $json | ConvertFrom-Json
$resolved = $cfg._resolved

$DestRoot = Join-Path $Root $Destination
New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null

Write-Host "Packaging DS-SLAM runtime"
Write-Host "Profile: $Profile"
Write-Host "Destination: $DestRoot"
Write-Host ""

Copy-IfExists ".\build\runtime_config.json" (Join-Path $DestRoot "build")
Copy-ConfigFiles ".\config" (Join-Path $DestRoot "config")
Copy-IfExists $resolved.orbslam3.rgbd_exe.win (Join-Path $DestRoot "orbslam3\Examples\RGB-D")
Copy-IfExists $resolved.orbslam3.vocabulary.win (Join-Path $DestRoot "orbslam3\Vocabulary")
Copy-IfExists $resolved.segmentation.model_path.win (Join-Path $DestRoot "segmentation\onnx")
Copy-DirectoryContents ".\visualization\backend" (Join-Path $DestRoot "visualization\backend")
Copy-DirectoryContents ".\visualization\frontend" (Join-Path $DestRoot "visualization\frontend")
Copy-DirectoryContents ".\visualization\shared" (Join-Path $DestRoot "visualization\shared")
Copy-IfExists ".\scripts\print_config.py" (Join-Path $DestRoot "scripts")
Copy-IfExists ".\scripts\config_loader.py" (Join-Path $DestRoot "scripts")
Copy-IfExists ".\requirements.txt" $DestRoot

$rgbdDir = Split-Path -Parent $resolved.orbslam3.rgbd_exe.win
if (Test-Path -LiteralPath $rgbdDir) {
    Get-ChildItem -LiteralPath $rgbdDir -Filter "*.dll" -File | ForEach-Object {
        Copy-IfExists $_.FullName (Join-Path $DestRoot "orbslam3\Examples\RGB-D")
    }
}

Write-Host ""
Write-Host "Package complete. No existing directories were deleted."
