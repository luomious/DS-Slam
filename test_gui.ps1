# DS-SLAM GUI Test Script

param(
    [string]$BaseUrl = "http://localhost:8000"
)

Write-Host "=== DS-SLAM GUI Test ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Backend server
Write-Host "[Test 1] Backend server..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/status" -Method Get
    if ($response.status -eq "running") {
        Write-Host "  [PASS] Backend running" -ForegroundColor Green
        Write-Host "  Clients: $($response.clients)" -ForegroundColor Gray
        Write-Host "  Buffered frames: $($response.buffered_frames)" -ForegroundColor Gray
    } else {
        Write-Host "  [FAIL] Backend status abnormal" -ForegroundColor Red
    }
} catch {
    Write-Host "  [FAIL] Cannot connect to backend" -ForegroundColor Red
}

# Test 2: Frontend page
Write-Host "[Test 2] Frontend page..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  [PASS] Frontend accessible" -ForegroundColor Green
        if ($response.Content -match "DS-SLAM Visualizer") {
            Write-Host "  [PASS] Page title correct" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Page title may be incorrect" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [FAIL] Status code: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "  [FAIL] Cannot access frontend" -ForegroundColor Red
}

# Test 3: Static files
Write-Host "[Test 3] Static files..." -ForegroundColor Yellow
$staticFiles = @(
    "/static/css/style.css",
    "/static/js/app.js",
    "/static/js/websocket.js",
    "/static/js/renderer.js",
    "/static/js/three/three.module.js"
)

foreach ($file in $staticFiles) {
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl$file" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "  [PASS] $file" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $file - Code: $($response.StatusCode)" -ForegroundColor Red
        }
    } catch {
        Write-Host "  [FAIL] $file" -ForegroundColor Red
    }
}

# Test 4: API endpoints
Write-Host "[Test 4] API endpoints..." -ForegroundColor Yellow
$apiEndpoints = @(
    "/api/status",
    "/api/config",
    "/api/trajectory",
    "/api/pointcloud"
)

foreach ($endpoint in $apiEndpoints) {
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl$endpoint" -Method Get
        Write-Host "  [PASS] $endpoint" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $endpoint" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If all tests pass but browser shows 'Service Unavailable', try:" -ForegroundColor Yellow
Write-Host "1. Force refresh browser (Ctrl+F5)" -ForegroundColor Gray
Write-Host "2. Clear browser cache" -ForegroundColor Gray
Write-Host "3. Check browser console for JavaScript errors" -ForegroundColor Gray
Write-Host "4. Use external browser: http://localhost:8000" -ForegroundColor Gray
