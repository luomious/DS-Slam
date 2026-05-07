param(
    [string]$Profile = "dev"
)

$ErrorActionPreference = "Continue"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

function Status($Name, $Ok, $Detail = "") {
    $mark = if ($Ok) { "[OK]" } else { "[--]" }
    if ($Detail) {
        "{0} {1} - {2}" -f $mark, $Name, $Detail
    } else {
        "{0} {1}" -f $mark, $Name
    }
}

function Test-PortOpen($HostName, $Port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($HostName, [int]$Port, $null, $null)
        $ok = $async.AsyncWaitHandle.WaitOne(250, $false)
        if ($ok) { $client.EndConnect($async) }
        $client.Close()
        return $ok
    } catch {
        return $false
    }
}

Write-Host "DS-SLAM config check"
Write-Host "Root: $Root"
Write-Host "Profile: $Profile"
Write-Host ""

$json = & $Python scripts/print_config.py --profile $Profile --format json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Could not load configuration."
    Write-Host $json
    Write-Host ""
    Write-Host "If PyYAML is missing, run: scripts\setup_python.bat"
    exit 1
}

$cfg = $json | ConvertFrom-Json
$resolved = $cfg._resolved

Status "Project root" (Test-Path -LiteralPath $resolved.project_root.win) $resolved.project_root.win
Status "MSYS2 MinGW64 shell" (Test-Path -LiteralPath $resolved.toolchain.mingw64_shell.win) $resolved.toolchain.mingw64_shell.win
Status "ORB-SLAM3 source" (Test-Path -LiteralPath (Join-Path $resolved.orbslam3.root.win "CMakeLists.txt")) $resolved.orbslam3.root.win
Status "ORB vocabulary" (Test-Path -LiteralPath $resolved.orbslam3.vocabulary.win) $resolved.orbslam3.vocabulary.win
Status "RGB-D executable" (Test-Path -LiteralPath $resolved.orbslam3.rgbd_exe.win) $resolved.orbslam3.rgbd_exe.win

Write-Host ""
Write-Host "Datasets"
foreach ($name in $cfg.datasets.PSObject.Properties.Name) {
    $dataset = $resolved.datasets.$name
    Status "$name root" (Test-Path -LiteralPath $dataset.root.win) $dataset.root.win
    Status "$name association" (Test-Path -LiteralPath $dataset.association.win) $dataset.association.win
    Status "$name camera" (Test-Path -LiteralPath $dataset.camera.win) $dataset.camera.win
}

Write-Host ""
Status "Segmentation ONNX model" (Test-Path -LiteralPath $resolved.segmentation.model_path.win) $resolved.segmentation.model_path.win
foreach ($name in $cfg.output.PSObject.Properties.Name) {
    $path = $resolved.output.$name.win
    $exists = Test-Path -LiteralPath $path
    Status "Output $name" $exists $path
}

Write-Host ""
$hostName = $cfg.visualization.host
$port = [int]$cfg.visualization.port
$portBusy = Test-PortOpen $hostName $port
$portDetail = "{0}:{1}" -f $hostName, $port
Status "Visualizer port available" (-not $portBusy) $portDetail
Status "Visualizer static dir" (Test-Path -LiteralPath $resolved.visualization.static_dir.win) $resolved.visualization.static_dir.win

Write-Host ""
Write-Host "Runtime config preview:"
Write-Host "  `"$Python`" scripts/print_config.py --profile $Profile --write-runtime build/runtime_config.json"
