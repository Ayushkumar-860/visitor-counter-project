<#
.SYNOPSIS
    hpa_demo.ps1 — Demonstrate HPA autoscaling with a load test.

.DESCRIPTION
    1. Verifies metrics-server is running
    2. Shows current HPA status
    3. Runs the load test (load-test/load_test.py) to generate CPU load
    4. Watches HPA scale Flask pods up
    5. Shows pod count over time
    6. Waits for load to stop, watches scale-down

.USAGE
    .\scripts\hpa_demo.ps1
#>

$NS = "visitor-counter"

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  HPA Autoscaling Demonstration" -ForegroundColor Magenta
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

# ── Check metrics server ──────────────────────────────────────────────────────
Write-Host "📊 Checking Metrics Server..." -ForegroundColor Cyan
$msReady = kubectl get deployment metrics-server -n kube-system -o jsonpath='{.status.readyReplicas}' 2>$null
if (-not $msReady -or $msReady -eq "0") {
    Write-Host "⚠️  Metrics Server may not be ready yet. Run:" -ForegroundColor Yellow
    Write-Host "   minikube addons enable metrics-server" -ForegroundColor Yellow
    Write-Host "   Then wait 60-90 seconds and retry." -ForegroundColor Yellow
} else {
    Write-Host "✅ Metrics Server is ready." -ForegroundColor Green
}

# ── Baseline HPA status ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "════ Baseline HPA Status ════════════════════════════════" -ForegroundColor Cyan
kubectl get hpa -n $NS
Write-Host ""
Write-Host "════ Current Pod Count (baseline) ══════════════════════" -ForegroundColor Cyan
kubectl get pods -n $NS -l app=flask-app

# ── Get the flask service URL ─────────────────────────────────────────────────
$minikubeIP = minikube ip 2>$null
$TARGET_URL = "http://${minikubeIP}:30080"
Write-Host ""
Write-Host "🎯 Load test target: $TARGET_URL" -ForegroundColor Yellow
Write-Host "   (Adjust if using port-forward on localhost:5000)" -ForegroundColor Gray

# ── Start load test in background ────────────────────────────────────────────
Write-Host ""
Write-Host "🔥 Starting load test (60 seconds)..." -ForegroundColor Red
Write-Host "   This will generate sustained HTTP traffic to trigger HPA scale-out." -ForegroundColor Gray

$loadTestJob = Start-Job -ScriptBlock {
    param($url, $projectRoot)
    Set-Location $projectRoot
    python "load-test/load_test.py" --url $url --duration 60 --workers 10
} -ArgumentList $TARGET_URL, (Split-Path -Parent $PSScriptRoot)

# ── Watch HPA during load ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "════ Watching HPA during load (60 seconds) ══════════════" -ForegroundColor Cyan
Write-Host "   TARGETS column shows current/target CPU utilization." -ForegroundColor Gray
Write-Host "   REPLICAS will increase when CPU exceeds 50%." -ForegroundColor Gray
Write-Host ""

for ($i = 0; $i -lt 12; $i++) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "── [$timestamp] ─────────────────────────────────────────" -ForegroundColor DarkGray
    kubectl get hpa flask-hpa -n $NS
    kubectl get pods -n $NS -l app=flask-app --no-headers | Select-String "Running"
    Start-Sleep -Seconds 15
}

# ── Stop load test ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "⏹️  Load test complete. Waiting for scale-down (may take ~5 min)..." -ForegroundColor Yellow
Stop-Job $loadTestJob -PassThru | Remove-Job

Write-Host ""
Write-Host "════ Post-load HPA Status ═══════════════════════════════" -ForegroundColor Cyan
kubectl get hpa -n $NS
Write-Host ""
kubectl get pods -n $NS -l app=flask-app

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  HPA Demo Complete" -ForegroundColor Magenta
Write-Host "  To watch ongoing metrics:" -ForegroundColor Gray
Write-Host "    kubectl get hpa -n $NS -w" -ForegroundColor Gray
Write-Host "    kubectl top pods -n $NS" -ForegroundColor Gray
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Magenta
