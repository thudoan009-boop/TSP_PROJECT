
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Starting OSRM..."
docker compose up -d osrm

if ($LASTEXITCODE -ne 0) {
    throw "Cannot start OSRM."
}

Write-Host "Waiting for OSRM..."

$ready = $false

for ($i = 0; $i -lt 60; $i++) {
    try {
        $url = "http://localhost:5001/route/v1/driving/106.7009,10.7769;106.7218,10.7950?overview=false"
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 5

        if ($response.code -eq "Ok") {
            $ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    throw "OSRM is not ready. Check Docker logs."
}

Write-Host "Running Python application..."
docker compose run --build --rm python-app

if ($LASTEXITCODE -ne 0) {
    throw "Python application failed."
}

$mapPath = Join-Path $PSScriptRoot "tsp_osrm_demo\output\route_map.html"

if (Test-Path $mapPath) {
    Start-Process $mapPath
}

Write-Host "COMPLETED SUCCESSFULLY!"
