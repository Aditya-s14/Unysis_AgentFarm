#!/usr/bin/env pwsh
# One-time OSRM map preparation for AgentFarm Optimizer (Windows / PowerShell).
#
# Downloads South + West India OpenStreetMap data (covers Karnataka, Tamil Nadu,
# Kerala, Andhra Pradesh, Telangana, Pondicherry, Maharashtra, Gujarat, Goa,
# Daman & Diu, Dadra & Nagar Haveli), merges them into a single PBF with
# osmium-tool, and runs OSRM's three pre-processing steps. Idempotent.
#
# After this completes:   docker compose up -d
# To force re-prep:       docker volume rm osrm_data ; then re-run this script.

$ErrorActionPreference = "Stop"

$SOUTH_URL = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"
$SOUTH_PBF = "southern-zone-latest.osm.pbf"
$WEST_URL  = "https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf"
$WEST_PBF  = "western-zone-latest.osm.pbf"
$MERGED_PBF = "india-south-west.osm.pbf"
$OSRM_NAME  = "india-south-west.osrm"
$VOLUME     = "osrm_data"
$OSRM_IMG   = "osrm/osrm-backend:latest"
$OSMIUM_IMG = "debian:bookworm-slim"

function Test-DockerRunning {
    docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker is not running. Start Docker Desktop first." -ForegroundColor Red
        exit 1
    }
}

function Test-VolumeFile($path) {
    $result = docker run --rm -v "${VOLUME}:/data" alpine sh -c "test -f /data/$path && echo YES || echo NO"
    return ($result -match "YES")
}

function Get-Pbf($url, $name) {
    if (Test-VolumeFile $name) {
        Write-Host "==> $name already downloaded. Skipping." -ForegroundColor Green
        return
    }
    Write-Host "==> Downloading $name..." -ForegroundColor Cyan
    docker run --rm -v "${VOLUME}:/data" alpine sh -c "cd /data && wget -O $name $url"
    if ($LASTEXITCODE -ne 0) { Write-Host "Download failed: $name" -ForegroundColor Red; exit 1 }
}

Write-Host "==> Checking Docker..." -ForegroundColor Cyan
Test-DockerRunning

Write-Host "==> Ensuring volume $VOLUME exists..." -ForegroundColor Cyan
docker volume create $VOLUME | Out-Null

if (Test-VolumeFile "$OSRM_NAME.fileIndex") {
    Write-Host "==> OSRM data already prepared. Skipping." -ForegroundColor Green
    Write-Host "    To re-prep from scratch: docker volume rm $VOLUME"
    exit 0
}

Get-Pbf $SOUTH_URL $SOUTH_PBF
Get-Pbf $WEST_URL  $WEST_PBF

if (-not (Test-VolumeFile $MERGED_PBF)) {
    Write-Host "==> Merging South + West zones into $MERGED_PBF..." -ForegroundColor Cyan
    docker run --rm -v "${VOLUME}:/data" $OSMIUM_IMG bash -c "apt-get update -qq && apt-get install -y -qq --no-install-recommends osmium-tool && osmium merge /data/$SOUTH_PBF /data/$WEST_PBF -o /data/$MERGED_PBF"
    if ($LASTEXITCODE -ne 0) { Write-Host "osmium merge failed." -ForegroundColor Red; exit 1 }
} else {
    Write-Host "==> Merged PBF already present. Skipping." -ForegroundColor Green
}

if (-not (Test-VolumeFile $OSRM_NAME)) {
    Write-Host "==> Running osrm-extract (car profile)..." -ForegroundColor Cyan
    docker run --rm -v "${VOLUME}:/data" $OSRM_IMG osrm-extract -p /opt/car.lua "/data/$MERGED_PBF"
    if ($LASTEXITCODE -ne 0) { Write-Host "osrm-extract failed." -ForegroundColor Red; exit 1 }
} else {
    Write-Host "==> Extract already done. Skipping." -ForegroundColor Green
}

if (-not (Test-VolumeFile "$OSRM_NAME.partition")) {
    Write-Host "==> Running osrm-partition..." -ForegroundColor Cyan
    docker run --rm -v "${VOLUME}:/data" $OSRM_IMG osrm-partition "/data/$OSRM_NAME"
    if ($LASTEXITCODE -ne 0) { Write-Host "osrm-partition failed." -ForegroundColor Red; exit 1 }
} else {
    Write-Host "==> Partition already done. Skipping." -ForegroundColor Green
}

Write-Host "==> Running osrm-customize..." -ForegroundColor Cyan
docker run --rm -v "${VOLUME}:/data" $OSRM_IMG osrm-customize "/data/$OSRM_NAME"
if ($LASTEXITCODE -ne 0) { Write-Host "osrm-customize failed." -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "==> OSRM data prepared (South + West India)." -ForegroundColor Green
Write-Host "    Start the stack: docker compose up -d"
