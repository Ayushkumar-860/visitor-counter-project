# Cost Optimization Analysis
## Visitor Counter — Cloud Computing Project

> **Local measurements are resource-efficiency proxies, not real cloud bills.**
> PENDING fields must be populated by running the benchmark after Docker and Kubernetes are set up.
> See [instructions](#how-to-populate-pending-values) below.

---

## Optimization Techniques

### Technique 1 — Container Image Size (Multi-Stage + Slim Base)

| Field | Value |
|---|---|
| **Baseline** | `python:3.10` full image (~950 MB) |
| **Optimized** | `python:3.10-slim` multi-stage build |
| **Expected reduction** | ~70–80% (950 MB → ~180–250 MB) |
| **Measurement command** | `docker images visitor-counter:latest` |
| **Why it matters** | Smaller images pull faster, reduce attack surface, and lower container registry storage costs |

**Techniques applied:**
- Multi-stage Dockerfile (builder stage discarded after `pip install`)
- `python:3.10-slim` base instead of full Python image
- `.dockerignore` excludes `__pycache__/`, `venv/`, `.pytest_cache/`, `.idea/`, etc.
- Efficient layer ordering (copy `requirements.txt` first → cached pip install layer)
- Pinned dependency versions (no floating `latest` tags)

---

### Technique 2 — HPA Idle vs Peak Replica Count

| Field | Value |
|---|---|
| **Baseline** | 5 replicas (manual, always running) |
| **Optimized** | 2 replicas idle → up to 5 under load (HPA) |
| **Idle reduction** | −60% (5 → 2 replicas) |
| **Measurement command** | `kubectl get hpa flask-hpa -n visitor-counter` |
| **Workload** | No traffic (idle) |

**Configuration:**
```yaml
minReplicas: 2
maxReplicas: 5
averageUtilization: 50   # CPU target
```

**Cloud cost implication (illustrative only):**
Assuming 1 vCPU node at $0.05/vCPU-hour on a hypothetical cloud:
- Always-on 5 pods × $0.05 × 24h = $6.00/day
- Idle 2 pods × $0.05 × 24h = $2.40/day
- **Saving: $3.60/day ($108/month) at idle** *(source: illustrative, not tied to a real provider)*

---

### Technique 3 — Right-Sized CPU Requests vs Over-Provisioned

| Field | Value |
|---|---|
| **Baseline** | No CPU request set (Kubernetes cannot schedule efficiently) |
| **Optimized** | `requests.cpu: 100m`, `limits.cpu: 500m` |
| **Measurement command** | `kubectl top pods -n visitor-counter` |
| **Workload** | Idle — 1 req/s |

**Why right-sizing matters:**
- CPU **requests** determine how many pods fit on a node (bin packing)
- CPU **limits** prevent one pod from starving others
- Without requests, HPA cannot calculate utilization percentage
- Over-requesting wastes node capacity → needs more nodes → higher cost

**How to measure:**
```powershell
kubectl top pods -n visitor-counter   # Requires metrics-server
# Note actual CPU column for idle pods
# Compare to request value (100m)
```

---

### Technique 4 — HTTP Response Time (Gunicorn Tuning)

| Field | Value |
|---|---|
| **Baseline** | Flask dev server (single-threaded) |
| **Optimized** | Gunicorn `--workers=2 --threads=2` |
| **Measurement command** | `python scripts/cost_benchmark.py` |
| **Workload** | 20 sequential GET / requests |

**PENDING:** Run `python scripts/cost_benchmark.py` after `docker compose up` to capture actual ms values.

---

### Technique 5 — Container Memory Usage

| Field | Value |
|---|---|
| **Baseline** | `python:3.10` full image (~200+ MiB) |
| **Optimized** | `python:3.10-slim` + non-root user (~40–80 MiB) |
| **Measurement command** | `docker stats visitor-counter-app --no-stream` |
| **Workload** | Idle, after `docker compose up` |

**PENDING:** Run after `docker compose up` and populate with actual `docker stats` output.

---

## How to Populate PENDING Values

```powershell
# 1. Build and start Docker Compose
.\scripts\docker_run.ps1

# 2. Re-run the benchmark (now Docker is available)
python scripts/cost_benchmark.py

# 3. For Kubernetes metrics (after k8s_deploy.ps1):
kubectl top pods -n visitor-counter
kubectl get hpa flask-hpa -n visitor-counter

# 4. Record the output and update cost_analysis.csv manually
#    or re-run: python scripts/cost_benchmark.py
```

---

## Cloud Cost Estimation (Hypothetical)

> **Disclaimer:** These are illustrative estimates only, based on publicly listed pricing.
> Actual costs depend on your cloud provider, region, reserved vs on-demand, storage class, and traffic.
> Always consult the official pricing calculator of your chosen provider.

| Resource | Assumption | Cost (illustrative) |
|---|---|---|
| Compute (2 Flask pods) | 0.1 vCPU × 2 × $0.048/vCPU-hr (AWS t3.micro equiv) | ~$0.23/day |
| Redis pod | 0.05 vCPU × $0.048/vCPU-hr | ~$0.06/day |
| Storage (PVC 100Mi) | 100Mi × $0.10/GiB-month | ~$0.001/month |
| **Total (idle, 2 replicas)** | | **~$8.70/month** |
| **Total (5 replicas always-on)** | | **~$21.70/month** |
| **HPA savings at idle** | | **~$13/month (~60%)** |

*Pricing source: illustrative only. See [AWS Pricing](https://aws.amazon.com/pricing/), [GCP Calculator](https://cloud.google.com/products/calculator), or [Azure Calculator](https://azure.microsoft.com/en-us/pricing/calculator/) for real estimates.*
