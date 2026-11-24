# Screenshots Required — Visitor Counter Project

This checklist maps each assignment requirement to a screenshot you must capture and save in this folder.

**Save screenshots as PNG with the exact filename shown.**
**Screenshots cannot be faked — they must show real running software.**

---

## Checklist

### Task 1 — Docker Containerization

- [ ] `01_docker_build.png` — Terminal showing `docker compose build` completing successfully
- [ ] `02_docker_ps.png` — `docker compose ps` showing flask-app and redis both "healthy"
- [ ] `03_app_browser.png` — Browser showing http://localhost:5000 with the visitor counter dashboard
- [ ] `04_app_health.png` — Browser or curl showing http://localhost:5000/health returning `{"status":"ok"}`
- [ ] `05_app_stats.png` — Browser showing http://localhost:5000/stats with current visitor count
- [ ] `06_docker_logs.png` — `docker compose logs flask-app` showing incoming request logs

### Task 2 — Kubernetes Deployment

- [ ] `07_minikube_start.png` — Terminal showing `minikube start` completing
- [ ] `08_kubectl_pods.png` — `kubectl get pods -n visitor-counter` showing Flask and Redis pods Running
- [ ] `09_kubectl_services.png` — `kubectl get services -n visitor-counter` showing flask-service and redis-service
- [ ] `10_k8s_app_browser.png` — Browser showing app accessed via Minikube NodePort or port-forward
- [ ] `11_self_healing_before.png` — Pod list before deleting a Flask pod (2 running)
- [ ] `12_self_healing_delete.png` — Terminal showing `kubectl delete pod <name>` command
- [ ] `13_self_healing_after.png` — Pod list a few seconds later showing Kubernetes created a new pod (back to 2)

### Task 3 — HPA Autoscaling

- [ ] `14_hpa_baseline.png` — `kubectl get hpa -n visitor-counter` showing 2 replicas, low CPU
- [ ] `15_load_test_running.png` — Terminal showing load_test.py running with request counts
- [ ] `16_hpa_scaling.png` — `kubectl get hpa -n visitor-counter` showing replicas increasing (3, 4, or 5)
- [ ] `17_hpa_pods_scaled.png` — `kubectl get pods -n visitor-counter` showing extra Flask pods
- [ ] `18_hpa_scaledown.png` — `kubectl get hpa -n visitor-counter` after load stops, replicas returning to 2

### Task 4 — Failover / Hybrid-Cloud Simulation

- [ ] `19_private_cluster_running.png` — `minikube status -p private-cluster` showing Running
- [ ] `20_public_cluster_running.png` — `minikube status -p public-cluster` showing Running
- [ ] `21_gateway_running.png` — Terminal showing `gateway.py` running with Primary/Secondary URLs
- [ ] `22_failover_before.png` — Browser showing app served by PRIMARY (check /gateway-status)
- [ ] `23_failover_triggered.png` — Terminal log showing "PRIMARY UNHEALTHY — Switched to SECONDARY"
- [ ] `24_failover_after.png` — Browser showing app served by SECONDARY (counter differs — independent Redis)
- [ ] `25_failover_recovered.png` — Terminal log showing "PRIMARY RECOVERED — Switched back to PRIMARY"

### Task 5 — Cost Optimization

- [ ] `26_image_size_before.png` — `docker images python:3.10` showing full image size
- [ ] `27_image_size_after.png` — `docker images visitor-counter:latest` showing slim image size
- [ ] `28_docker_stats.png` — `docker stats --no-stream` showing container memory usage
- [ ] `29_kubectl_top_pods.png` — `kubectl top pods -n visitor-counter` showing CPU/memory
- [ ] `30_cost_csv.png` — Screenshot of `cost_analysis.csv` opened in Excel or Notepad

### Tests

- [ ] `31_pytest_results.png` — Terminal showing `pytest tests/ -v` with all 16 tests PASSED

---

## How to Take Screenshots on Windows

```powershell
# Method 1: Snipping Tool (Win + Shift + S) — select area
# Method 2: Print Screen key, paste in Paint, save as PNG
# Method 3: PowerShell (full screen):
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::PrimaryScreen | Out-Null
$bmp = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,
                                         [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen(0, 0, 0, 0, $bmp.Size)
$bmp.Save("screenshots\screenshot.png")
```

---

> **Note:** Screenshots must show real, running software. Never submit screenshots of placeholder images, edited text, or stock photos. The grader may cross-reference timestamps, pod names, and counter values.
