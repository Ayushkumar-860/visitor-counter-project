# Deploy a Visitor Counter Web App (Flask + Redis) on Docker and Kubernetes

> **Cloud Computing Academic Project** — Complete implementation with Docker, Kubernetes, HPA, Failover Simulation, and Cost Analysis

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Quick Start — Docker Compose](#quick-start--docker-compose)
4. [Running Tests](#running-tests)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [HPA Autoscaling Demo](#hpa-autoscaling-demo)
7. [Hybrid-Cloud Failover Simulation](#hybrid-cloud-failover-simulation)
8. [Cost Optimization](#cost-optimization)
9. [Architecture](#architecture)
10. [Assignment Requirements Checklist](#assignment-requirements-checklist)
11. [Screenshots Guide](#screenshots-guide)
12. [Troubleshooting](#troubleshooting)
13. [GitHub Setup](#github-setup)
14. [Cleanup](#cleanup)

---

## Prerequisites

### Required Tools

| Tool | Purpose | Install |
|---|---|---|
| Docker Desktop | Container runtime + Compose | https://www.docker.com/products/docker-desktop/ |
| Minikube | Local Kubernetes | https://minikube.sigs.k8s.io/docs/start/ |
| kubectl | Kubernetes CLI | https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/ |
| Python 3.10+ | Tests + scripts | https://www.python.org/downloads/ ✅ Already installed |
| Git | Version control | https://git-scm.com/download/win |

### Installation — Windows PowerShell (winget)

```powershell
# Docker Desktop
winget install Docker.DockerDesktop

# Git
winget install Git.Git

# Minikube
winget install Kubernetes.minikube

# kubectl
winget install Kubernetes.kubectl
```

After installing Docker Desktop, **restart your machine** and ensure it is running (tray icon shows green).

### Verify Installation

```powershell
docker --version          # Docker version 24.x or higher
docker compose version    # Docker Compose version v2.x
minikube version          # minikube version: v1.32.x
kubectl version --client  # Client Version: v1.29.x
python --version          # Python 3.10.x  (already installed)
git --version             # git version 2.x
```

### Minimum System Requirements (Two-Cluster Mode)

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk | 20 GB free | 40 GB free |

---

## Project Structure

```
visitor-counter-project/
├── app.py                      # Flask application (Redis counter, health/ready endpoints)
├── requirements.txt            # Pinned Python dependencies
├── Dockerfile                  # Multi-stage build (python:3.10-slim + non-root)
├── docker-compose.yml          # Local dev: flask-app + redis with health checks
├── .dockerignore               # Excludes caches from Docker build context
├── .gitignore                  # Excludes secrets/venvs from Git
├── k8s.yaml                    # K8s: Namespace, ConfigMap, Redis PVC+Deploy+Svc, Flask Deploy+Svc
├── hpa.yaml                    # HorizontalPodAutoscaler (autoscaling/v2, CPU 50%)
├── pytest.ini                  # pytest configuration
├── templates/index.html        # Jinja2 HTML template (responsive dashboard)
├── static/style.css            # Dark-themed CSS
├── tests/test_app.py           # 16 pytest tests (fakeredis, no live Redis needed)
├── scripts/
│   ├── docker_run.ps1          # Build + run Docker Compose, wait for health
│   ├── k8s_deploy.ps1          # Minikube start, image build, apply, rollout, self-healing demo
│   ├── hpa_demo.ps1            # HPA autoscaling demonstration
│   └── cost_benchmark.py       # Measure image sizes, memory, response time
├── load-test/
│   └── load_test.py            # Pure-Python HTTP load generator (triggers HPA)
├── failover/
│   ├── gateway.py              # Python reverse-proxy with health-check-driven failover
│   └── dual_cluster_demo.ps1   # Two-cluster simulation + controlled failover
├── screenshots/README.md       # Screenshot checklist (31 required screenshots)
├── architecture.mmd            # Mermaid architecture diagram source
├── cost_analysis.csv           # Auto-generated cost/resource table
├── cost_analysis.md            # Cost optimization analysis and cloud estimates
├── report.md                   # Academic report (PDF-ready)
├── github_link.txt             # GitHub URL placeholder
└── README.md                   # This file
```

---

## Quick Start — Docker Compose

### Option A: Using the PowerShell Script (Recommended)

```powershell
# From the project root in PowerShell:
.\scripts\docker_run.ps1

# Stop everything:
.\scripts\docker_run.ps1 -Down

# Force rebuild (after changing app.py):
.\scripts\docker_run.ps1 -Rebuild
```

### Option B: Manual Commands

```powershell
# 1. Build the image
docker compose build

# 2. Start services
docker compose up -d

# 3. Check status (wait for both to show "healthy")
docker compose ps

# 4. View logs
docker compose logs -f flask-app
```

### Expected Output

```
NAME                     STATUS          PORTS
visitor-counter-redis    Up (healthy)    0.0.0.0:6379->6379/tcp
visitor-counter-app      Up (healthy)    0.0.0.0:5000->5000/tcp
```

### Access the Application

| URL | Description |
|---|---|
| http://localhost:5000 | Main visitor counter dashboard |
| http://localhost:5000/health | Liveness probe (always 200) |
| http://localhost:5000/ready | Readiness probe (200 when Redis OK) |
| http://localhost:5000/stats | JSON visitor count |

---

## Running Tests

> Tests use **fakeredis** — no real Redis server required.

```powershell
# Install test dependencies (already done if you followed setup)
pip install -r requirements.txt

# Run all 16 tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test class
python -m pytest tests/ -v -k "TestHealthEndpoints"
```

### Test Results (Verified — Python 3.10.10)

```
tests/test_app.py::TestHomepage::test_homepage_returns_200           PASSED
tests/test_app.py::TestHomepage::test_homepage_contains_title        PASSED
tests/test_app.py::TestHomepage::test_homepage_contains_counter      PASSED
tests/test_app.py::TestHomepage::test_visitor_count_increments       PASSED
tests/test_app.py::TestHomepage::test_homepage_shows_redis_status    PASSED
tests/test_app.py::TestHealthEndpoints::test_health_returns_200      PASSED
tests/test_app.py::TestHealthEndpoints::test_health_returns_json     PASSED
tests/test_app.py::TestHealthEndpoints::test_ready_returns_200_...   PASSED
tests/test_app.py::TestHealthEndpoints::test_ready_returns_json_...  PASSED
tests/test_app.py::TestStatsEndpoint::test_stats_returns_200         PASSED
tests/test_app.py::TestStatsEndpoint::test_stats_returns_visitor_... PASSED
tests/test_app.py::TestStatsEndpoint::test_stats_count_matches_...   PASSED
tests/test_app.py::TestResetEndpoint::test_reset_allowed_in_testing  PASSED
tests/test_app.py::TestResetEndpoint::test_reset_then_count_...      PASSED
tests/test_app.py::TestRedisUnavailable::test_homepage_handles_...   PASSED
tests/test_app.py::TestRedisUnavailable::test_ready_returns_503_...  PASSED

16 passed in 1.49s
```

---

## Kubernetes Deployment

### Step 1 — Start Minikube with Metrics Server

```powershell
# Start Minikube (uses Docker Desktop as driver)
minikube start --driver=docker --memory=2048 --cpus=2

# Enable Metrics Server (required for HPA)
minikube addons enable metrics-server

# Verify metrics-server is running (wait ~90 seconds after enabling)
kubectl get deployment metrics-server -n kube-system
```

### Step 2 — Build Image Inside Minikube

```powershell
# Point Docker CLI to Minikube's internal Docker daemon
# (This avoids needing a Docker registry)
& minikube docker-env --shell=powershell | Invoke-Expression

# Build the image (now it's inside Minikube)
docker build -t visitor-counter:latest .

# Verify image is available
docker images visitor-counter
```

### Step 3 — Deploy

```powershell
# Apply all manifests
kubectl apply -f k8s.yaml
kubectl apply -f hpa.yaml

# Wait for Redis to be ready
kubectl rollout status deployment/redis -n visitor-counter --timeout=120s

# Wait for Flask to be ready
kubectl rollout status deployment/flask-app -n visitor-counter --timeout=120s
```

### Step 4 — Verify Deployment

```powershell
# Check pods
kubectl get pods -n visitor-counter -o wide

# Check services
kubectl get services -n visitor-counter

# Check HPA
kubectl get hpa -n visitor-counter

# Check ConfigMap
kubectl get configmap -n visitor-counter

# Check PVC
kubectl get pvc -n visitor-counter
```

### Step 5 — Access the Application

```powershell
# Method A: NodePort (direct Minikube IP)
minikube ip
# Access: http://<minikube-ip>:30080

# Method B: Port-forward (more reliable)
kubectl port-forward svc/flask-service 5000:80 -n visitor-counter
# Access: http://localhost:5000

# Method C: Minikube service shortcut
minikube service flask-service -n visitor-counter --url
```

### Step 6 — Self-Healing Demo

```powershell
# See current pods
kubectl get pods -n visitor-counter -l app=flask-app

# Delete one Flask pod (copy a pod name from above)
kubectl delete pod flask-app-<random-suffix> -n visitor-counter

# Watch Kubernetes immediately create a replacement
kubectl get pods -n visitor-counter -l app=flask-app -w
```

**Expected behavior:** Within 5–10 seconds, Kubernetes detects the pod is gone and creates a new one. The service continues serving traffic through the remaining pod.

### Or Use the Script (Automates All Steps)

```powershell
.\scripts\k8s_deploy.ps1              # Full deploy + self-healing demo
.\scripts\k8s_deploy.ps1 -SkipBuild  # Skip image build
.\scripts\k8s_deploy.ps1 -Teardown   # Clean up all resources
```

---

## HPA Autoscaling Demo

### Prerequisites

```powershell
# Ensure metrics-server addon is enabled
minikube addons list | Select-String metrics-server

# Verify metrics are flowing (may take 60-90s after enabling)
kubectl top pods -n visitor-counter
```

### Run the Demo

```powershell
# Method A: Automated script
.\scripts\hpa_demo.ps1

# Method B: Manual — watch HPA in one terminal
kubectl get hpa flask-hpa -n visitor-counter -w

# Method B: Run load test in another terminal
python load-test/load_test.py --url http://<minikube-ip>:30080 --duration 60 --workers 10

# Method B: Watch pods scale in a third terminal
kubectl get pods -n visitor-counter -l app=flask-app -w
```

### What to Observe

1. **Before load:** `TARGETS: 0%/50%`, `REPLICAS: 2`
2. **During load:** CPU climbs above 50%, replicas increase to 3, 4, or 5
3. **After load stops:** CPU drops, replicas return to 2 (after ~5 minute scale-down delay)

### Important Notes

- Metrics Server must be running and collecting data before HPA can act
- CPU must exceed 50% of the **requested** value (100m), not the limit
- Scale-down has a 5-minute stabilization window (prevents flapping)
- If CPU does not rise, increase `--workers` in the load test

---

## Hybrid-Cloud Failover Simulation

> **IMPORTANT:** This is a **local simulation on one laptop**. It is NOT real hybrid cloud.
> Both "clusters" run as separate Minikube profiles. Redis counters are independent.

### RAM Check

```powershell
# Check free RAM (need ~6 GB free for two clusters)
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
```

### Two-Cluster Demo (Full)

```powershell
.\failover\dual_cluster_demo.ps1

# Check cluster status:
.\failover\dual_cluster_demo.ps1 -Status

# Cleanup (DESTRUCTIVE — deletes both Minikube profiles):
.\failover\dual_cluster_demo.ps1 -Cleanup
```

### Single-Cluster Fallback (Low RAM)

```powershell
.\failover\dual_cluster_demo.ps1 -SingleCluster
# Prints step-by-step instructions for simulating failover
# using two Docker containers on ports 5000 and 5001
```

### Manual Failover Steps

```powershell
# 1. Set cluster URLs (replace IPs from `minikube ip -p <profile>`)
$env:PRIMARY_URL   = "http://192.168.49.2:30080"   # private-cluster
$env:SECONDARY_URL = "http://192.168.58.2:30080"   # public-cluster

# 2. Start the failover gateway (runs on port 8080)
python failover/gateway.py

# 3. Browse to http://localhost:8080 — served by PRIMARY

# 4. Simulate primary outage (scale Flask to 0 replicas)
kubectl scale deployment flask-app --replicas=0 -n visitor-counter --context minikube-private-cluster

# 5. Watch gateway log — after ~10s it shows:
#    "[HH:MM:SS] WARNING PRIMARY UNHEALTHY -- Switched to SECONDARY (failover #1)"

# 6. Browse to http://localhost:8080 — now served by SECONDARY
#    Note: counter value is different (independent Redis in each cluster)

# 7. Restore primary
kubectl scale deployment flask-app --replicas=2 -n visitor-counter --context minikube-private-cluster

# 8. After ~15s gateway log shows:
#    "[HH:MM:SS] PRIMARY RECOVERED -- Switched back to PRIMARY"

# 9. Check gateway status at any time:
Invoke-RestMethod http://localhost:8080/gateway-status
```

### Failover Limitations (Important)

- Two Minikube clusters share the same laptop CPU/RAM — not true isolation
- Redis state is **NOT shared** between clusters — counters differ after failover
- Shared Redis would require distributed storage (e.g., Redis Cluster with replicas, Redis Sentinel) — out of scope for this project
- Recovery to primary is automatic after health checks pass
- For real HA, production systems use DNS failover (Route53, Cloudflare) or Anycast

---

## Cost Optimization

### Generate Measurements

```powershell
# After docker compose up, run the benchmark:
python scripts/cost_benchmark.py

# Results saved to cost_analysis.csv
# Markdown analysis in cost_analysis.md
```

### Image Size Comparison

```powershell
# Compare full Python image vs our optimized image
docker images python:3.10          # ~950 MB (illustrative — full image)
docker images visitor-counter:latest  # ~180-250 MB (slim + multi-stage)
```

### Key Techniques Applied

| # | Technique | Expected Saving |
|---|---|---|
| 1 | `python:3.10-slim` + multi-stage build | ~70% image size reduction |
| 2 | HPA min=2 replicas (vs always-on 5) | ~60% idle compute cost |
| 3 | Right-sized CPU request (100m) | Accurate HPA + better bin-packing |
| 4 | `.dockerignore` excludes caches | Smaller build context, faster builds |
| 5 | Non-root container user (UID 1001) | Security posture, audit compliance |

---

## Architecture

```
Browser → [Failover Gateway :8080] ─────────────────────────────────┐
                                                                      │
                    ┌── PRIMARY ─────────────────────────────────────┤
                    │   Minikube: private-cluster                     │
                    │   ┌─────────────────────────────────────────┐   │
                    │   │ Namespace: visitor-counter               │   │
                    │   │  ┌──────────┐    ┌──────────────────┐   │   │
                    │   │  │  Flask   │    │   HPA (2–5 pods) │   │   │
                    │   │  │  Pod ×2  │◄───│   Metrics Server │   │   │
                    │   │  └────┬─────┘    └──────────────────┘   │   │
                    │   │       │  redis-service (ClusterIP)       │   │
                    │   │  ┌────▼─────┐    ┌──────────────────┐   │   │
                    │   │  │  Redis   │◄───│    PVC (100Mi)   │   │   │
                    │   │  │   Pod    │    │  Persistent Vol  │   │   │
                    │   │  └──────────┘    └──────────────────┘   │   │
                    │   └─────────────────────────────────────────┘   │
                    │                                                  │
                    └── SECONDARY (failover) ────────────────────────┘
                        Minikube: public-cluster
                        (independent Redis — separate counter)
```

The architecture diagram source is in [architecture.mmd](./architecture.mmd).
Render it at https://mermaid.live or with VS Code's Mermaid extension.

---

## Assignment Requirements Checklist

| Requirement | File(s) | Status |
|---|---|---|
| Flask + Redis app | `app.py` | ✅ Implemented |
| Responsive HTML dashboard | `templates/index.html`, `static/style.css` | ✅ Implemented |
| /health liveness endpoint | `app.py` → `/health` | ✅ Implemented |
| /ready readiness endpoint | `app.py` → `/ready` | ✅ Implemented |
| Redis atomic counter | `app.py` → `client.incr()` | ✅ Implemented |
| Environment variable config | `app.py`, `docker-compose.yml`, `k8s.yaml` | ✅ Implemented |
| Dockerfile (non-root, slim) | `Dockerfile` | ✅ Implemented |
| .dockerignore | `.dockerignore` | ✅ Implemented |
| Docker Compose + Redis volume | `docker-compose.yml` | ✅ Implemented |
| Kubernetes manifests | `k8s.yaml` | ✅ Implemented |
| Redis ClusterIP (not public) | `k8s.yaml` → redis-service | ✅ Implemented |
| Redis PVC | `k8s.yaml` → redis-pvc | ✅ Implemented |
| ConfigMap | `k8s.yaml` → visitor-counter-config | ✅ Implemented |
| Resource requests/limits | `k8s.yaml` | ✅ Implemented |
| Liveness/Readiness probes | `k8s.yaml` | ✅ Implemented |
| HPA (autoscaling/v2) | `hpa.yaml` | ✅ Implemented |
| Minikube deploy script | `scripts/k8s_deploy.ps1` | ✅ Implemented |
| Self-healing demo | `scripts/k8s_deploy.ps1 -DemoHealing` | ✅ Script ready |
| Load test | `load-test/load_test.py` | ✅ Implemented |
| HPA demo script | `scripts/hpa_demo.ps1` | ✅ Implemented |
| Failover gateway | `failover/gateway.py` | ✅ Implemented |
| Dual-cluster demo | `failover/dual_cluster_demo.ps1` | ✅ Implemented |
| Single-cluster fallback | `failover/dual_cluster_demo.ps1 -SingleCluster` | ✅ Implemented |
| Cost analysis CSV | `cost_analysis.csv` | ✅ Generated |
| Cost analysis markdown | `cost_analysis.md` | ✅ Implemented |
| Cost benchmark script | `scripts/cost_benchmark.py` | ✅ Implemented |
| Architecture diagram | `architecture.mmd` | ✅ Implemented |
| Unit/integration tests | `tests/test_app.py` (16 tests) | ✅ **ALL PASSED** |
| Redis-unavailable test | `tests/test_app.py::TestRedisUnavailable` | ✅ **PASSED** |
| README | `README.md` | ✅ This file |
| Academic report | `report.md` | ✅ Implemented |
| Screenshot checklist | `screenshots/README.md` | ✅ Implemented |
| .gitignore | `.gitignore` | ✅ Implemented |
| GitHub preparation | `github_link.txt`, `.gitignore` | ✅ Implemented |

---

## Screenshots Guide

See [screenshots/README.md](./screenshots/README.md) for the complete list of 31 required screenshots with filenames and instructions.

**Key screenshots to capture:**
1. `docker compose ps` showing both services healthy
2. Browser at http://localhost:5000 showing the counter
3. `kubectl get pods` showing Flask + Redis running
4. Self-healing: pod list before → delete → pod list after (new pod created)
5. `kubectl get hpa` before and after load test
6. Gateway terminal showing "Switched to SECONDARY"
7. `pytest` output showing 16 passed

---

## Troubleshooting

### Docker Issues

```powershell
# Docker daemon not running
# → Start Docker Desktop from the Start menu, wait for the whale icon to turn green

# Port 5000 already in use
netstat -ano | Select-String ":5000"
Stop-Process -Id <PID>

# Redis container unhealthy
docker compose logs redis
docker exec visitor-counter-redis redis-cli ping   # Should return PONG

# Flask cannot connect to Redis
# Check REDIS_HOST is "redis" (the service name), not "localhost"
docker compose logs flask-app | Select-String "Redis"
```

### Kubernetes Issues

```powershell
# Pod stuck in Pending
kubectl describe pod <pod-name> -n visitor-counter
# Common cause: imagePullPolicy: Never but image not built in Minikube

# "ErrImageNeverPull" error
# Solution: Build image inside Minikube's Docker daemon
& minikube docker-env --shell=powershell | Invoke-Expression
docker build -t visitor-counter:latest .

# HPA shows <unknown> for CPU
# Metrics Server not ready yet — wait 60-90 seconds then:
kubectl top pods -n visitor-counter

# Pod CrashLoopBackOff
kubectl logs <pod-name> -n visitor-counter --previous
kubectl describe pod <pod-name> -n visitor-counter
```

### Minikube Issues

```powershell
# Minikube fails to start
minikube delete
minikube start --driver=docker --memory=2048 --cpus=2

# Cannot reach NodePort from browser
minikube tunnel   # Run in a separate PowerShell window (needs admin)
# Or use port-forward instead:
kubectl port-forward svc/flask-service 5000:80 -n visitor-counter

# Two-cluster low RAM
# Use -SingleCluster mode
.\failover\dual_cluster_demo.ps1 -SingleCluster
```

---

## GitHub Setup

```powershell
# 1. Initialize Git repository
git init
git add .
git commit -m "Initial commit: Visitor Counter Flask+Redis+Docker+Kubernetes project"

# 2. Create a repository at https://github.com/new
#    Name: visitor-counter-project
#    Visibility: Public
#    Do NOT initialize with README

# 3. Connect and push
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/visitor-counter-project.git
git push -u origin main

# 4. Update github_link.txt with the actual URL
```

**What NOT to commit:**
- `.env` files (secrets)
- `venv/` or `.venv/` folders
- `__pycache__/` directories
- Screenshots (optional — can be excluded)

These are all covered by `.gitignore`.

---

## Cleanup

```powershell
# Stop Docker Compose
docker compose down

# Remove Docker volumes (WARNING: deletes persisted Redis data)
docker compose down -v

# Remove Docker images
docker rmi visitor-counter:latest

# Delete Kubernetes resources
kubectl delete namespace visitor-counter

# Stop Minikube
minikube stop

# Delete Minikube cluster (WARNING: deletes cluster)
minikube delete

# Delete dual-cluster profiles (WARNING: destructive)
.\failover\dual_cluster_demo.ps1 -Cleanup
```

---

## Submitting the Assignment

1. **Screenshots** — Capture all 31 screenshots per `screenshots/README.md`
2. **GitHub** — Push to public repository, update `github_link.txt`
3. **Report** — Fill in `report.md` with your name, roll number, institution, and actual screenshots
4. **ZIP** — Zip the entire project folder
5. **Google Drive** — Upload ZIP, `report.md` (converted to PDF), and screenshots folder
6. **Submit** — Share Google Drive link per your instructor's submission instructions
