"""
load_test.py — HTTP Load Testing Script for Visitor Counter HPA Demo
Generates sustained HTTP traffic to trigger CPU load on Flask pods.

Usage:
    python load-test/load_test.py                        # defaults
    python load-test/load_test.py --url http://localhost:5000
    python load-test/load_test.py --url http://192.168.49.2:30080 --duration 60 --workers 10

Requirements: Only Python standard library (no extra packages needed).
"""

import argparse
import sys
import time
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List


@dataclass
class Stats:
    """Thread-safe statistics collector."""
    lock: threading.Lock = field(default_factory=threading.Lock)
    success: int = 0
    errors: int = 0
    total_latency: float = 0.0

    def record(self, latency: float, ok: bool):
        with self.lock:
            if ok:
                self.success += 1
                self.total_latency += latency
            else:
                self.errors += 1

    def summary(self) -> dict:
        with self.lock:
            total = self.success + self.errors
            avg_lat = (self.total_latency / self.success * 1000) if self.success else 0
            return {
                "total_requests": total,
                "success": self.success,
                "errors": self.errors,
                "avg_latency_ms": round(avg_lat, 1),
                "requests_per_second": round(total / max(1, self._elapsed), 1),
            }

    _elapsed: float = 1.0


def worker(url: str, stats: Stats, stop_event: threading.Event):
    """Single worker thread: repeatedly GETs the URL until stop_event is set."""
    while not stop_event.is_set():
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                _ = resp.read()
                ok = resp.status == 200
        except (urllib.error.URLError, OSError, Exception):
            ok = False
        latency = time.perf_counter() - t0
        stats.record(latency, ok)


def run_load_test(url: str, duration: int, num_workers: int):
    """Launch workers, wait for duration seconds, then stop and report."""
    print(f"\n{'═'*55}")
    print(f"  🔥  Load Test Starting")
    print(f"{'═'*55}")
    print(f"  URL:      {url}")
    print(f"  Duration: {duration}s")
    print(f"  Workers:  {num_workers} concurrent threads")
    print(f"{'═'*55}\n")

    stats = Stats()
    stop_event = threading.Event()
    threads: List[threading.Thread] = []

    for _ in range(num_workers):
        t = threading.Thread(target=worker, args=(url, stats, stop_event), daemon=True)
        t.start()
        threads.append(t)

    start = time.time()
    interval = 10

    # Progress updates every 10 seconds
    next_report = start + interval
    while True:
        now = time.time()
        elapsed = now - start
        if elapsed >= duration:
            break
        if now >= next_report:
            s = stats.summary()
            s["_elapsed"] = elapsed
            remaining = int(duration - elapsed)
            print(f"  [{int(elapsed):3d}s elapsed | {remaining}s remaining] "
                  f"Requests: {s['total_requests']}  "
                  f"Errors: {s['errors']}  "
                  f"Avg latency: {s['avg_latency_ms']}ms")
            next_report += interval
        time.sleep(0.5)

    stop_event.set()
    for t in threads:
        t.join(timeout=5)

    stats._elapsed = time.time() - start
    s = stats.summary()

    print(f"\n{'═'*55}")
    print(f"  ✅  Load Test Complete")
    print(f"{'═'*55}")
    print(f"  Total requests:    {s['total_requests']}")
    print(f"  Successful:        {s['success']}")
    print(f"  Errors:            {s['errors']}")
    print(f"  Avg latency:       {s['avg_latency_ms']} ms")
    print(f"  Throughput:        {s['requests_per_second']} req/s")
    print(f"{'═'*55}\n")
    print("  After load stops, Kubernetes HPA will scale down after ~5 minutes.")
    print("  Watch with: kubectl get hpa -n visitor-counter -w")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visitor Counter Load Test")
    parser.add_argument("--url", default="http://localhost:5000",
                        help="Target URL (default: http://localhost:5000)")
    parser.add_argument("--duration", type=int, default=60,
                        help="Test duration in seconds (default: 60)")
    parser.add_argument("--workers", type=int, default=5,
                        help="Number of concurrent worker threads (default: 5)")
    args = parser.parse_args()

    try:
        run_load_test(args.url, args.duration, args.workers)
    except KeyboardInterrupt:
        print("\n  ⚠️  Load test interrupted by user.")
        sys.exit(0)
