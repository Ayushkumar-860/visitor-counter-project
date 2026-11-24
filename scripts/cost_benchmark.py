"""
cost_benchmark.py -- Resource and Cost Analysis Benchmark Script
Measures image sizes, memory usage, and response time for the cost analysis.

Run this script after Docker is installed and images are built.
If Docker is not available, it marks measurements as PENDING.

Usage:
    python scripts/cost_benchmark.py
    python scripts/cost_benchmark.py --output cost_analysis.csv
"""

import csv
import os
import sys
import time
import subprocess
import json
import urllib.request
import urllib.error
from datetime import datetime

OUTPUT_CSV = os.environ.get("OUTPUT_CSV", "cost_analysis.csv")
APP_URL    = os.environ.get("APP_URL", "http://localhost:5000")
PENDING    = "PENDING - run after Docker build"


def run_cmd(cmd: list):
    """Run a shell command, return (returncode, output)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return 1, "Command not found: " + cmd[0]
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"


def measure_image_size(tag: str) -> str:
    """Return Docker image size for a given tag, or PENDING."""
    rc, out = run_cmd(["docker", "inspect", tag, "--format={{.Size}}"])
    if rc == 0 and out.isdigit():
        mb = round(int(out) / (1024 * 1024), 1)
        return str(mb) + " MB"
    return PENDING


def measure_response_time(url: str, n: int = 20) -> str:
    """Measure average response time over n requests."""
    latencies = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                _ = r.read()
                latencies.append((time.perf_counter() - t0) * 1000)
        except Exception:
            pass
    if latencies:
        return str(round(sum(latencies) / len(latencies), 1)) + " ms"
    return PENDING


def measure_container_memory(container_name: str) -> str:
    """Return container memory usage from docker stats."""
    rc, out = run_cmd(["docker", "stats", container_name, "--no-stream",
                       "--format={{.MemUsage}}"])
    if rc == 0 and out:
        return out.split("/")[0].strip()
    return PENDING


def docker_available() -> bool:
    rc, _ = run_cmd(["docker", "info"])
    return rc == 0


def build_rows() -> list:
    docker_ok = docker_available()

    rows = []

    # Technique 1: Image Size
    baseline_img  = measure_image_size("python:3.10") if docker_ok else PENDING
    optimized_img = measure_image_size("visitor-counter:latest") if docker_ok else PENDING

    rows.append({
        "Technique": "Container image size (multi-stage + slim base)",
        "Baseline": baseline_img,
        "Baseline_Unit": "MB",
        "Optimized": optimized_img,
        "Optimized_Unit": "MB",
        "Measurement_Command": "docker inspect <tag> --format={{.Size}}",
        "Workload_Conditions": "After docker build, idle",
        "Pct_Change": "PENDING - populate after build",
        "Notes": "python:3.10 full -> python:3.10-slim multi-stage",
    })

    # Technique 2: HPA Replica Count
    rows.append({
        "Technique": "HPA replica count - idle vs loaded",
        "Baseline": "5 replicas (manual max)",
        "Baseline_Unit": "replicas",
        "Optimized": "2 replicas (HPA min, idle)",
        "Optimized_Unit": "replicas",
        "Measurement_Command": "kubectl get hpa flask-hpa -n visitor-counter",
        "Workload_Conditions": "Idle - no incoming traffic",
        "Pct_Change": "-60% (5->2 replicas)",
        "Notes": "HPA scales down to minReplicas=2 when CPU < 50%",
    })

    # Technique 3: Right-sized CPU request
    rows.append({
        "Technique": "Right-sized CPU request (100m) vs over-provisioned (500m limit)",
        "Baseline": "500m CPU limit only",
        "Baseline_Unit": "millicores",
        "Optimized": "100m CPU request + 500m limit",
        "Optimized_Unit": "millicores",
        "Measurement_Command": "kubectl top pods -n visitor-counter",
        "Workload_Conditions": "Idle, 1 request/s",
        "Pct_Change": "PENDING - measure kubectl top after deploy",
        "Notes": "Requests right-sized to observed usage; limits kept high for burst",
    })

    # Technique 4: Response time benchmark
    resp_time = measure_response_time(APP_URL) if docker_ok else PENDING
    rows.append({
        "Technique": "Average HTTP response time (20 sequential requests)",
        "Baseline": PENDING,
        "Baseline_Unit": "ms",
        "Optimized": resp_time,
        "Optimized_Unit": "ms",
        "Measurement_Command": "python scripts/cost_benchmark.py",
        "Workload_Conditions": "20 sequential GET / to " + APP_URL,
        "Pct_Change": "PENDING - capture baseline before optimizations",
        "Notes": "Run before and after Gunicorn --workers tuning",
    })

    # Technique 5: Memory usage
    mem = measure_container_memory("visitor-counter-app") if docker_ok else PENDING
    rows.append({
        "Technique": "Container memory usage (non-root, .dockerignore, slim image)",
        "Baseline": PENDING,
        "Baseline_Unit": "MiB",
        "Optimized": mem,
        "Optimized_Unit": "MiB",
        "Measurement_Command": "docker stats visitor-counter-app --no-stream",
        "Workload_Conditions": "Idle, after docker compose up",
        "Pct_Change": "PENDING - capture baseline before optimizations",
        "Notes": "python:3.10 full base expected ~200+ MiB; slim ~40-80 MiB",
    })

    return rows


def write_csv(rows: list, path: str):
    fieldnames = [
        "Technique", "Baseline", "Baseline_Unit", "Optimized", "Optimized_Unit",
        "Measurement_Command", "Workload_Conditions", "Pct_Change", "Notes"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("CSV written to: " + path)


def print_summary(rows: list):
    sep = "-" * 65
    print("\n" + sep)
    print("  Cost & Resource Optimization Analysis  (" + datetime.now().strftime("%Y-%m-%d %H:%M") + ")")
    print(sep)
    for i, r in enumerate(rows, 1):
        print("\n  [" + str(i) + "] " + r["Technique"])
        print("      Baseline:  " + str(r["Baseline"]) + " " + r["Baseline_Unit"])
        print("      Optimized: " + str(r["Optimized"]) + " " + r["Optimized_Unit"])
        print("      Change:    " + str(r["Pct_Change"]))
        if "PENDING" in str(r["Baseline"]) or "PENDING" in str(r["Optimized"]):
            print("      NOTE: Some values are PENDING -- requires Docker/Kubernetes")
    print("\n" + sep + "\n")


if __name__ == "__main__":
    rows = build_rows()
    print_summary(rows)
    write_csv(rows, OUTPUT_CSV)
