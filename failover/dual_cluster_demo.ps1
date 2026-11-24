<#
.SYNOPSIS
    dual_cluster_demo.ps1 — Hybrid-Cloud Failover Simulation on Two Minikube Profiles

.DESCRIPTION
    Creates two Minikube profiles (private-cluster, public-cluster),
    deploys the visitor counter to both, starts the failover gateway,
    demonstrates controlled failover, and shows recovery.

    ⚠️  SIMULATION WARNING:
    Both clusters run on THIS LAPTOP. This is NOT real hybrid cloud.
    You need ~6 GB RAM free to run both clusters simultaneously.
    If RAM is insufficient, use -SingleCluster mode (documented below).

.USAGE
    .\failover\dual_cluster_demo.ps1               # Full two-cluster demo
    .\failover\dual_cluster_demo.ps1 -Cleanup      # Delete both clusters
    .\failover\dual_cluster_demo.ps1 -Status       # Show cluster status only
    .\failover\dual_cluster_demo.ps1 -SingleCluster # One-cluster fallback
#>

param(
    [switch]$Cleanup,
    [switch]$Status,
    [switch]$SingleCluster
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Write-Banner($msg, $color="Cyan") {
    Write-Host ""
    Write-Host ("═" * 56) -ForegroundColor $color
    Write-Host "  $msg" -ForegroundColor $color
    Write-Host ("═" * 56) -ForegroundColor $color
    Write-Host ""
}

function Check-Prerequisites {
    foreach ($cmd in @("minikube", "kubectl", "python")) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
            Write-Host "❌ '$cmd' not found. Install it first." -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "✅ Prerequisites OK" -ForegroundColor Green
}

function Check-RAM {
    $freeGB = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)
    Write-Host "  Free RAM: ${freeGB} GB" -ForegroundColor Gray
    if ($freeGB -lt 5) {
        Write-Host "⚠️  Less than 5 GB free RAM detected." -ForegroundColor Yellow
        Write-Host "   Two-cluster mode requires ~6 GB. Use -SingleCluster if needed." -ForegroundColor Yellow
        return $false
    }
    return $true
}

function Deploy-ToCluster($profile, $nodePort, $imageTag) {
    Write-Host "  Deploying to profile: $profile ..." -ForegroundColor Cyan

    # Switch to this profile's docker env
    & minikube docker-env -p $profile --shell=powershell | Invoke-Expression

    # Build image
    Set-Location $ProjectRoot
    docker build -t ${imageTag}:latest . 2>&1 | Out-Null
    Write-Host "  ✅ Image built in $profile" -ForegroundColor Green

    # Apply manifests with patched nodePort
    $tempYaml = "$env:TEMP\k8s_${profile}.yaml"
    (Get-Content "$ProjectRoot\k8s.yaml") -replace "nodePort: 30080", "nodePort: $nodePort" | Set-Content $tempYaml
    kubectl apply -f $tempYaml --context "minikube-${profile}" 2>&1 | Out-Null
    kubectl apply -f "$ProjectRoot\hpa.yaml" --context "minikube-${profile}" 2>&1 | Out-Null

    # Wait for rollout
    kubectl rollout status deployment/flask-app -n visitor-counter `
        --context "minikube-${profile}" --timeout=180s

    $ip = minikube ip -p $profile
    Write-Host "  ✅ $profile deployed at http://${ip}:${nodePort}" -ForegroundColor Green
    return "http://${ip}:${nodePort}"
}

# ── Status ────────────────────────────────────────────────────────────────────
if ($Status) {
    Write-Banner "Cluster Status"
    foreach ($p in @("private-cluster", "public-cluster")) {
        Write-Host "  Profile: $p" -ForegroundColor Cyan
        minikube status -p $p 2>&1
        Write-Host ""
    }
    exit 0
}

# ── Cleanup ───────────────────────────────────────────────────────────────────
if ($Cleanup) {
    Write-Banner "⚠️  Cleanup: Deleting Both Clusters" "Red"
    Write-Host "  This will DELETE minikube profiles private-cluster and public-cluster." -ForegroundColor Red
    $confirm = Read-Host "  Type 'yes' to confirm"
    if ($confirm -ne "yes") { Write-Host "Cancelled."; exit 0 }

    minikube delete -p private-cluster 2>&1
    minikube delete -p public-cluster 2>&1
    Write-Host "✅ Both clusters deleted." -ForegroundColor Green
    exit 0
}

Check-Prerequisites

# ── Single-Cluster Fallback ───────────────────────────────────────────────────
if ($SingleCluster) {
    Write-Banner "Single-Cluster Failover Demo (RAM-Constrained Fallback)"
    Write-Host "  This demo simulates failover using TWO PORT-FORWARDED instances" -ForegroundColor Yellow
    Write-Host "  of the SAME cluster on different local ports (5000 and 5001)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Step 1: Run the app normally on port 5000:" -ForegroundColor Gray
    Write-Host "    .\scripts\docker_run.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "  Step 2: Run a second instance on port 5001 (simulated secondary):" -ForegroundColor Gray
    Write-Host "    docker run -d --name vc-secondary -p 5001:5000 -e REDIS_HOST=redis visitor-counter:latest" -ForegroundColor White
    Write-Host ""
    Write-Host "  Step 3: Start the gateway targeting both ports:" -ForegroundColor Gray
    Write-Host '    $env:PRIMARY_URL="http://localhost:5000"' -ForegroundColor White
    Write-Host '    $env:SECONDARY_URL="http://localhost:5001"' -ForegroundColor White
    Write-Host "    python failover/gateway.py" -ForegroundColor White
    Write-Host ""
    Write-Host "  Step 4: Stop the primary to trigger failover:" -ForegroundColor Gray
    Write-Host "    docker stop visitor-counter-app" -ForegroundColor White
    Write-Host "    # Gateway will switch to port 5001 within ~10 seconds" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Step 5: Restore primary:" -ForegroundColor Gray
    Write-Host "    docker start visitor-counter-app" -ForegroundColor White
    Write-Host "    # Gateway will return to port 5000 after 3 successful health checks" -ForegroundColor Gray
    exit 0
}

# ── Full Two-Cluster Demo ─────────────────────────────────────────────────────
Write-Banner "Hybrid-Cloud Failover Simulation (Two Minikube Clusters)"

$ramOk = Check-RAM
if (-not $ramOk) {
    Write-Host ""
    Write-Host "  Recommendation: Use -SingleCluster mode instead." -ForegroundColor Yellow
    Write-Host "  .\failover\dual_cluster_demo.ps1 -SingleCluster" -ForegroundColor White
    $proceed = Read-Host "  Proceed anyway with two clusters? (yes/no)"
    if ($proceed -ne "yes") { exit 0 }
}

# Create and start both clusters
Write-Host "🚀 Creating private-cluster..." -ForegroundColor Cyan
minikube start -p private-cluster --driver=docker --memory=2048 --cpus=2

Write-Host ""
Write-Host "🚀 Creating public-cluster..." -ForegroundColor Cyan
minikube start -p public-cluster --driver=docker --memory=2048 --cpus=2

# Deploy to both
Write-Banner "Deploying to private-cluster"
$primaryUrl = Deploy-ToCluster "private-cluster" 30080 "visitor-counter"

Write-Banner "Deploying to public-cluster"
$secondaryUrl = Deploy-ToCluster "public-cluster" 30081 "visitor-counter"

# Start failover gateway
Write-Banner "Starting Failover Gateway"
Write-Host "  Primary:   $primaryUrl" -ForegroundColor Green
Write-Host "  Secondary: $secondaryUrl" -ForegroundColor Yellow
Write-Host ""

$env:PRIMARY_URL   = $primaryUrl
$env:SECONDARY_URL = $secondaryUrl

$gatewayJob = Start-Job -ScriptBlock {
    param($primary, $secondary, $root)
    $env:PRIMARY_URL   = $primary
    $env:SECONDARY_URL = $secondary
    python "$root/failover/gateway.py"
} -ArgumentList $primaryUrl, $secondaryUrl, $ProjectRoot

Write-Host "  Gateway running on http://localhost:8080" -ForegroundColor Green
Write-Host "  Status: http://localhost:8080/gateway-status" -ForegroundColor Gray
Start-Sleep -Seconds 5

# Failover demonstration
Write-Banner "Controlled Failover Demonstration" "Magenta"
Write-Host "  STEP 1: Check baseline — visit http://localhost:8080 in your browser." -ForegroundColor Gray
Write-Host "  Press Enter when ready..." -ForegroundColor Yellow
Read-Host

Write-Host ""
Write-Host "  STEP 2: Simulating primary failure..." -ForegroundColor Red
Write-Host "  Scaling private-cluster flask-app to 0 replicas (simulates outage)." -ForegroundColor Gray
kubectl scale deployment flask-app --replicas=0 -n visitor-counter --context minikube-private-cluster

Write-Host "  Waiting for gateway to detect failure and failover (~10 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "  Gateway Status after failover:" -ForegroundColor Cyan
try {
    $status = (Invoke-WebRequest -Uri "http://localhost:8080/gateway-status" -TimeoutSec 5).Content
    Write-Host $status
} catch {
    Write-Host "  (Could not reach gateway status endpoint)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  STEP 3: Verify traffic is now served by SECONDARY." -ForegroundColor Gray
Write-Host "  Visit http://localhost:8080 — counter will differ (independent Redis)." -ForegroundColor Yellow
Write-Host "  Press Enter when ready to restore primary..." -ForegroundColor Yellow
Read-Host

Write-Host ""
Write-Host "  STEP 4: Restoring primary cluster..." -ForegroundColor Green
kubectl scale deployment flask-app --replicas=2 -n visitor-counter --context minikube-private-cluster
kubectl rollout status deployment/flask-app -n visitor-counter --context minikube-private-cluster --timeout=120s

Write-Host "  Waiting for gateway to detect recovery (~15 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host ""
Write-Host "  Gateway Status after recovery:" -ForegroundColor Cyan
try {
    $status = (Invoke-WebRequest -Uri "http://localhost:8080/gateway-status" -TimeoutSec 5).Content
    Write-Host $status
} catch {
    Write-Host "  (Could not reach gateway status endpoint)" -ForegroundColor Gray
}

Write-Banner "Failover Demo Complete" "Green"
Write-Host "  Cleanup: .\failover\dual_cluster_demo.ps1 -Cleanup" -ForegroundColor Gray
Stop-Job $gatewayJob -PassThru | Remove-Job
