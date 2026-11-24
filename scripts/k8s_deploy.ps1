<#
.SYNOPSIS
    k8s_deploy.ps1 — Deploy the Visitor Counter app to Minikube.

.DESCRIPTION
    1. Checks minikube/kubectl are installed
    2. Starts (or reuses) the Minikube cluster
    3. Enables the metrics-server addon (required for HPA)
    4. Builds the Docker image inside Minikube's Docker daemon
    5. Applies k8s.yaml and hpa.yaml manifests
    6. Waits for rollout to complete
    7. Port-forwards the flask-service or shows NodePort URL
    8. Demonstrates self-healing by deleting a Flask pod

.USAGE
    .\scripts\k8s_deploy.ps1
    .\scripts\k8s_deploy.ps1 -SkipBuild     # Skip docker build
    .\scripts\k8s_deploy.ps1 -Teardown      # Delete all resources
    .\scripts\k8s_deploy.ps1 -DemoHealing   # Only run self-healing demo
#>

param(
    [switch]$SkipBuild,
    [switch]$Teardown,
    [switch]$DemoHealing
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$NS = "visitor-counter"

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Visitor Counter — Kubernetes (Minikube) Deployer" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Check prerequisites ───────────────────────────────────────────────────────
foreach ($cmd in @("minikube", "kubectl")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "❌ '$cmd' not found. Install from:" -ForegroundColor Red
        if ($cmd -eq "minikube") {
            Write-Host "   https://minikube.sigs.k8s.io/docs/start/" -ForegroundColor Yellow
        } else {
            Write-Host "   https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/" -ForegroundColor Yellow
        }
        exit 1
    }
}

# ── Teardown ──────────────────────────────────────────────────────────────────
if ($Teardown) {
    Write-Host "⚠️  Deleting namespace $NS and all resources..." -ForegroundColor Yellow
    kubectl delete namespace $NS --ignore-not-found
    Write-Host "✅ Teardown complete." -ForegroundColor Green
    exit 0
}

# ── Start Minikube ────────────────────────────────────────────────────────────
Write-Host "🚀 Starting Minikube (default profile)..." -ForegroundColor Cyan
minikube start --driver=docker --memory=2048 --cpus=2 2>&1 | Write-Host

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Minikube failed to start. Check Docker Desktop is running." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Minikube is running." -ForegroundColor Green

# ── Enable Metrics Server ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "📊 Enabling metrics-server addon (required for HPA)..." -ForegroundColor Cyan
minikube addons enable metrics-server
Write-Host "   Note: metrics-server may take 60-90 seconds to become ready." -ForegroundColor Gray

# ── Build image inside Minikube's Docker ─────────────────────────────────────
if (-not $SkipBuild) {
    Write-Host ""
    Write-Host "🔨 Building image inside Minikube's Docker daemon..." -ForegroundColor Cyan
    Write-Host "   (This avoids the need to push to a registry)" -ForegroundColor Gray

    # Point the shell's Docker client to Minikube's Docker daemon
    $env:DOCKER_TLS_VERIFY = "1"
    & minikube docker-env --shell=powershell | Invoke-Expression

    docker build -t visitor-counter:latest .

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker build failed inside Minikube." -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Image 'visitor-counter:latest' built in Minikube." -ForegroundColor Green
}

# ── Apply manifests ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "📦 Applying Kubernetes manifests..." -ForegroundColor Cyan
kubectl apply -f k8s.yaml
kubectl apply -f hpa.yaml

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ kubectl apply failed." -ForegroundColor Red
    exit 1
}

# ── Wait for rollout ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "⏳ Waiting for Redis rollout..." -ForegroundColor Yellow
kubectl rollout status deployment/redis -n $NS --timeout=120s

Write-Host ""
Write-Host "⏳ Waiting for Flask rollout..." -ForegroundColor Yellow
kubectl rollout status deployment/flask-app -n $NS --timeout=120s

# ── Show pod status ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "════ Pod Status ═════════════════════════════════════════" -ForegroundColor Cyan
kubectl get pods -n $NS -o wide
Write-Host ""
Write-Host "════ Services ═══════════════════════════════════════════" -ForegroundColor Cyan
kubectl get services -n $NS
Write-Host ""
Write-Host "════ HPA Status ═════════════════════════════════════════" -ForegroundColor Cyan
kubectl get hpa -n $NS

# ── Self-healing demo ─────────────────────────────────────────────────────────
if ($DemoHealing -or (-not $SkipBuild)) {
    Write-Host ""
    Write-Host "════ Self-Healing Demonstration ═════════════════════════" -ForegroundColor Magenta
    Write-Host "Deleting one Flask pod to demonstrate Kubernetes self-healing..." -ForegroundColor Yellow

    $flaskPod = kubectl get pods -n $NS -l app=flask-app -o jsonpath='{.items[0].metadata.name}' 2>&1
    if ($flaskPod -and $flaskPod -notmatch "Error") {
        Write-Host "  Deleting pod: $flaskPod" -ForegroundColor Yellow
        kubectl delete pod $flaskPod -n $NS

        Write-Host "  Watching Kubernetes replace the pod (Ctrl+C to stop)..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
        kubectl get pods -n $NS -l app=flask-app --watch &
        Start-Sleep -Seconds 15
        Write-Host ""
        Write-Host "  Current pod status after self-healing:" -ForegroundColor Cyan
        kubectl get pods -n $NS -l app=flask-app
    } else {
        Write-Host "  No Flask pods found to delete." -ForegroundColor Yellow
    }
}

# ── Access URL ────────────────────────────────────────────────────────────────
Write-Host ""
$minikubeIP = minikube ip 2>&1
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Application is available at:" -ForegroundColor Green
Write-Host "  🌐  http://${minikubeIP}:30080" -ForegroundColor Green
Write-Host ""
Write-Host "  Or use port-forward:" -ForegroundColor Gray
Write-Host "  kubectl port-forward svc/flask-service 5000:80 -n $NS" -ForegroundColor Gray
Write-Host "  Then visit: http://localhost:5000" -ForegroundColor Gray
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
