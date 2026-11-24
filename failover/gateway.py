"""
gateway.py — Local Failover Gateway for Hybrid-Cloud Simulation
Simulates primary (private-cluster) and secondary (public-cluster) traffic routing.

WHAT THIS IS:
  A lightweight reverse-proxy that runs on localhost:8080.
  It health-checks the primary endpoint every few seconds.
  If the primary is unhealthy, it automatically switches to the secondary.

ARCHITECTURE:
  Browser → Gateway (:8080) → Primary (private-cluster NodePort)
                             → Secondary (public-cluster NodePort) [on failover]

USAGE:
  # Set environment variables for your cluster endpoints
  $env:PRIMARY_URL   = "http://192.168.49.2:30080"    # private-cluster IP
  $env:SECONDARY_URL = "http://192.168.58.2:30080"    # public-cluster IP
  python failover/gateway.py

  # Or test with a single cluster (port-forwarded to different ports):
  $env:PRIMARY_URL   = "http://localhost:5000"
  $env:SECONDARY_URL = "http://localhost:5001"
  python failover/gateway.py

LIMITATIONS:
  - This is a simulation on a single laptop; both "clusters" are local.
  - Redis counters are INDEPENDENT in each cluster (no shared state).
  - This is NOT production-grade HA. It demonstrates the concept only.
"""

import os
import sys
import time
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Configuration ──────────────────────────────────────────────────────────────
PRIMARY_URL       = os.environ.get("PRIMARY_URL",   "http://localhost:5000")
SECONDARY_URL     = os.environ.get("SECONDARY_URL", "http://localhost:5001")
GATEWAY_PORT      = int(os.environ.get("GATEWAY_PORT", 8080))
HEALTH_CHECK_PATH = os.environ.get("HEALTH_CHECK_PATH", "/health")
CHECK_INTERVAL    = int(os.environ.get("CHECK_INTERVAL_SECS", 5))
FAILURE_THRESHOLD = int(os.environ.get("FAILURE_THRESHOLD", 2))
RECOVERY_THRESHOLD = int(os.environ.get("RECOVERY_THRESHOLD", 3))
TIMEOUT           = float(os.environ.get("HEALTH_TIMEOUT", 3.0))

# ── State ──────────────────────────────────────────────────────────────────────
state = {
    "active":           "primary",
    "primary_ok":       True,
    "secondary_ok":     True,
    "primary_fails":    0,
    "primary_recovers": 0,
    "failover_count":   0,
    "lock":             threading.Lock(),
}


def check_endpoint(url: str) -> bool:
    """Return True if the health endpoint returns HTTP 200."""
    try:
        full_url = url.rstrip("/") + HEALTH_CHECK_PATH
        with urllib.request.urlopen(full_url, timeout=TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False


def health_monitor():
    """Background thread: continuously checks primary health and triggers failover."""
    while True:
        time.sleep(CHECK_INTERVAL)
        primary_ok = check_endpoint(PRIMARY_URL)

        with state["lock"]:
            state["primary_ok"] = primary_ok

            if state["active"] == "primary":
                if not primary_ok:
                    state["primary_fails"] += 1
                    if state["primary_fails"] >= FAILURE_THRESHOLD:
                        state["active"] = "secondary"
                        state["failover_count"] += 1
                        state["primary_fails"] = 0
                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️  PRIMARY UNHEALTHY — Switched to SECONDARY "
                              f"(failover #{state['failover_count']})", flush=True)
                else:
                    state["primary_fails"] = 0
            else:  # active == secondary
                if primary_ok:
                    state["primary_recovers"] += 1
                    if state["primary_recovers"] >= RECOVERY_THRESHOLD:
                        state["active"] = "primary"
                        state["primary_recovers"] = 0
                        print(f"[{time.strftime('%H:%M:%S')}] ✅  PRIMARY RECOVERED — Switched back to PRIMARY",
                              flush=True)
                else:
                    state["primary_recovers"] = 0


class GatewayHandler(BaseHTTPRequestHandler):
    """Reverse-proxy handler: forwards requests to active backend."""

    def log_message(self, fmt, *args):
        """Override default logger to add backend info."""
        with state["lock"]:
            backend = state["active"].upper()
        print(f"[{time.strftime('%H:%M:%S')}] [{backend}] {self.requestline} → {args[1]}", flush=True)

    def _get_target_url(self):
        with state["lock"]:
            if state["active"] == "primary":
                return PRIMARY_URL
            return SECONDARY_URL

    def do_GET(self):
        self._proxy_request("GET")

    def do_POST(self):
        self._proxy_request("POST")

    def do_HEAD(self):
        self._proxy_request("HEAD")

    def _proxy_request(self, method: str):
        target_url = self._get_target_url()
        full_url = target_url.rstrip("/") + self.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            req = urllib.request.Request(full_url, data=body, method=method)
            # Forward select headers
            for h in ("Content-Type", "Accept", "User-Agent"):
                v = self.headers.get(h)
                if v:
                    req.add_header(h, v)

            with urllib.request.urlopen(req, timeout=10) as resp:
                self.send_response(resp.status)
                for key, val in resp.headers.items():
                    if key.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(key, val)
                # Inject active backend info
                with state["lock"]:
                    self.send_header("X-Gateway-Backend", state["active"])
                    self.send_header("X-Failover-Count", str(state["failover_count"]))
                self.end_headers()
                self.wfile.write(resp.read())

        except Exception as exc:
            # Serve a simple error page
            msg = (
                f"<h2>Gateway Error</h2>"
                f"<p>Could not reach <code>{full_url}</code>: {exc}</p>"
                f"<p>Active backend: <code>{self._get_target_url()}</code></p>"
            ).encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET_status(self):
        """Special /gateway-status endpoint to show current state."""
        import json
        with state["lock"]:
            info = {k: v for k, v in state.items() if k != "lock"}
        info["primary_url"] = PRIMARY_URL
        info["secondary_url"] = SECONDARY_URL
        body = json.dumps(info, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/gateway-status":
            self.do_GET_status()
        else:
            self._proxy_request("GET")


if __name__ == "__main__":
    print(f"""
{'═'*55}
  Visitor Counter — Failover Gateway
{'═'*55}
  Gateway:    http://localhost:{GATEWAY_PORT}
  Primary:    {PRIMARY_URL}  (private-cluster)
  Secondary:  {SECONDARY_URL}  (public-cluster)
  Health:     {HEALTH_CHECK_PATH}  every {CHECK_INTERVAL}s
  Failover threshold:  {FAILURE_THRESHOLD} failures
  Recovery threshold:  {RECOVERY_THRESHOLD} successes
{'═'*55}

  ⚠️  SIMULATION NOTE:
  Both clusters run on this laptop. This is NOT real hybrid cloud.
  Redis counters in each cluster are independent (no shared state).
  This demonstrates the traffic-routing concept only.
{'═'*55}
  Status: http://localhost:{GATEWAY_PORT}/gateway-status
{'═'*55}
""", flush=True)

    # Start background health monitor
    monitor = threading.Thread(target=health_monitor, daemon=True)
    monitor.start()

    server = HTTPServer(("0.0.0.0", GATEWAY_PORT), GatewayHandler)
    print(f"[{time.strftime('%H:%M:%S')}] Gateway listening on port {GATEWAY_PORT} ...", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGateway stopped.")
