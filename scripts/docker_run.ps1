<#
.SYNOPSIS
    docker_run.ps1 — Build and run the Visitor Counter app with Docker Compose.

.DESCRIPTION
    1. Checks Docker is installed and running
    2. Builds the visitor-counter image
    3. Starts flask-app + redis with docker-compose
    4. Waits for health checks to pass
    5. Prints the access URL

.USAGE
    .\scripts\docker_run.ps1
    .\scripts\docker_run.ps1 -Down    # Stop and remove containers
    .\scripts\docker_run.ps1 -Rebuild # Force rebuild image
#>

param(
    [switch]$Down,
    [switch]$Rebuild
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Visitor Counter — Docker Compose Runner" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Check Docker ──────────────────────────────────────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker not found. Please install Docker Desktop:" -ForegroundColor Red
    Write-Host "   https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker daemon is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker is running." -ForegroundColor Green

# ── Tear down if requested ────────────────────────────────────────────────────
if ($Down) {
    Write-Host ""
    Write-Host "⚠️  Stopping and removing containers..." -ForegroundColor Yellow
    docker compose down
    Write-Host "✅ Containers stopped." -ForegroundColor Green
    exit 0
}

# ── Build image ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "🔨 Building visitor-counter Docker image..." -ForegroundColor Cyan
if ($Rebuild) {
    docker compose build --no-cache
} else {
    docker compose build
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed. Check the output above." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image built successfully." -ForegroundColor Green

# ── Start services ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "🚀 Starting services (flask-app + redis)..." -ForegroundColor Cyan
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ docker compose up failed." -ForegroundColor Red
    exit 1
}

# ── Wait for health checks ────────────────────────────────────────────────────
Write-Host ""
Write-Host "⏳ Waiting for containers to become healthy..." -ForegroundColor Yellow
$maxWait = 60
$elapsed = 0
$allHealthy = $false

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds 3
    $elapsed += 3

    $redisHealth = docker inspect --format='{{.State.Health.Status}}' visitor-counter-redis 2>$null
    $flaskHealth = docker inspect --format='{{.State.Health.Status}}' visitor-counter-app 2>$null

    Write-Host "  Redis: $redisHealth | Flask: $flaskHealth  (${elapsed}s)" -ForegroundColor Gray

    if ($redisHealth -eq "healthy" -and $flaskHealth -eq "healthy") {
        $allHealthy = $true
        break
    }
}

Write-Host ""
if ($allHealthy) {
    Write-Host "✅ All services are healthy!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Services may still be starting. Check with: docker compose logs" -ForegroundColor Yellow
}

# ── Print status ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Application is available at:" -ForegroundColor Green
Write-Host "  🌐  http://localhost:5000" -ForegroundColor Green
Write-Host "  🔍  Health:  http://localhost:5000/health" -ForegroundColor Green
Write-Host "  📊  Stats:   http://localhost:5000/stats" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Container status:" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "To view logs:   docker compose logs -f" -ForegroundColor Gray
Write-Host "To stop:        .\scripts\docker_run.ps1 -Down" -ForegroundColor Gray
