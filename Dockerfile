# ═══════════════════════════════════════════════════════════════════════════════
# Dockerfile — Visitor Counter Flask App
# Base: python:3.10-slim  (smaller footprint than python:3.10)
# Production server: Gunicorn
# Non-root execution for security
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage: builder (install deps in a clean layer) ────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /install

# Copy only the dependency file first (better layer cache)
COPY requirements.txt .

RUN pip install --upgrade pip --no-cache-dir \
 && pip install --prefix=/install/pkg --no-cache-dir -r requirements.txt


# ── Stage: runtime ────────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

# Metadata labels
LABEL maintainer="student@example.com" \
      version="1.0.0" \
      description="Visitor Counter — Cloud Computing Academic Project"

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup --no-create-home appuser

# Working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install/pkg /usr/local

# Copy application source code
COPY app.py          ./
COPY templates/      ./templates/
COPY static/         ./static/

# Set ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Environment defaults (can be overridden at runtime)
ENV FLASK_ENV=production \
    APP_ENV=production \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    PORT=5000

EXPOSE 5000

# Health check (Docker-native, used by docker-compose)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Launch Gunicorn: 2 workers per CPU core (adjust if needed)
CMD ["gunicorn", "--workers=2", "--threads=2", "--bind=0.0.0.0:5000", \
     "--access-logfile=-", "--error-logfile=-", "--log-level=info", \
     "app:app"]
