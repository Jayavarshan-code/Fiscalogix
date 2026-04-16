# ─────────────────────────────────────────────────────────────────────────────
# Fiscalogix Backend — Production Dockerfile
# Optimised for Railway (and any Docker-based cloud)
#
# Build order is tuned for layer caching:
#   1. System packages  (changes rarely)
#   2. Heavy Python deps: torch CPU, prophet  (changes rarely)
#   3. App Python deps   (changes on requirements.txt edit)
#   4. App source code   (changes on every push)
#
# IMPORTANT: Never add a COPY .env line here.
#   Secrets are injected as environment variables by Railway/Render/Fly.
#   The app reads them via os.environ — no file needed at runtime.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── Environment ───────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    # Prevents pip from creating unnecessary files
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Prophet / cmdstanpy: skip interactive Stan model compilation prompt
    CMDSTAN_AUTO_INSTALL=1

WORKDIR /code

# ── Layer 1: System packages ──────────────────────────────────────────────────
# build-essential  → compiles C extensions (psycopg2, prophet/pystan, shap)
# libpq-dev        → psycopg2 PostgreSQL adapter
# libgomp1         → OpenMP for ortools + scikit-learn parallel inference
# libffi-dev       → cryptography (JWT)
# libssl-dev       → cryptography (JWT)
# git              → some pip installs resolve git dependencies
# curl             → Railway health checks + WACC FRED feed
# gcc g++ make     → prophet compiles Stan models on first import
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    libpq-dev \
    libgomp1 \
    libffi-dev \
    libssl-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 2: App Python dependencies ─────────────────────────────────────────
# requirements.txt pins torch==2.2.2+cpu with --extra-index-url pointing to
# the PyTorch CPU wheel index. This prevents pip from pulling the 2 GB CUDA
# wheel when resolving sentence-transformers dependencies.
COPY backend/requirements.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt

# ── Layer 3: Application source ───────────────────────────────────────────────
COPY backend/app        /code/app
COPY backend/setup_db.py /code/setup_db.py
COPY backend/seed_db.py  /code/seed_db.py

# Pre-create model directory so first-boot auto-training has a target path
RUN mkdir -p /code/app/financial_system/ml_pipeline/models

# ── Layer 4: Startup entrypoint ───────────────────────────────────────────────
COPY entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

CMD ["/code/entrypoint.sh"]
