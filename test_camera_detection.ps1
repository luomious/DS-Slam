# USB Camera Detection Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  USB Camera Detection" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get camera devices
$cameras = Get-PnpDevice -Class Camera
if ($cameras.Count -eq 0) {
    Write-Host "[ERROR] No camera devices found!" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Found $($cameras.Count) camera device(s):" -ForegroundColor Green
Write-Host ""

foreach ($camera in $cameras) {
    Write-Host "Camera: $($camera.FriendlyName)" -ForegroundColor Yellow
    Write-Host "  Status: $($camera.Status)" -ForegroundColor $(if($camera.Status -eq 'OK'){'Green'}else{'Red'})
    Write-Host "  InstanceId: $($camera.InstanceId)" -ForegroundColor Gray
    Write-Host ""
    
    # Get device properties
    try {
        $props = Get-PnpDeviceProperty -InstanceId $camera.InstanceId
        $desc = ($props | Where-Object { $_.KeyName -like '*DeviceDesc*' }).Data
        if ($desc) { Write-Host "  Description: $desc" -ForegroundColor Gray }
        
        $manufacturer = ($props | Where-Object { $_.KeyName -like '*Manufacturer*' }).Data
        if ($manufacturer) { Write-Host "  Manufacturer: $manufacturer" -ForegroundColor Gray }
        
        $hwId = ($props | Where-Object { $_.KeyName -like '*HardwareID*' }).Data
        if ($hwId) { Write-Host "  HardwareID: $hwId" -ForegroundColor Gray }
    } catch {
        Write-Host "  (Could not retrieve device properties)" -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Host "----------------------------------------" -ForegroundColor DarkGray
    Write-Host ""
}

Write-Host "Detection complete!" -ForegroundColor Green
