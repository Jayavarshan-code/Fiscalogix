#!/bin/sh
set -e

echo "──────────────────────────────────────────"
echo " Fiscalogix Backend — Starting up"
echo "──────────────────────────────────────────"

# ── 1. Wait for Postgres to be ready ─────────────────────────────────────────
echo "[1/3] Waiting for database..."
MAX_TRIES=30
COUNT=0
until python -c "
import os, sys
from sqlalchemy import create_engine, text
url = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://', 1)
if not url:
    sys.exit(0)
try:
    engine = create_engine(url)
    with engine.connect() as c:
        c.execute(text('SELECT 1'))
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_TRIES ]; then
        echo "Database not reachable after ${MAX_TRIES} attempts. Starting anyway."
        break
    fi
    echo "  Waiting for database... attempt $COUNT/$MAX_TRIES"
    sleep 2
done
echo "  Database ready."

# ── 2. Run schema setup (idempotent — safe to run on every boot) ──────────────
echo "[2/3] Running database setup..."
python setup_db.py || echo "  setup_db.py failed or already up-to-date — continuing."

# ── 3. Start FastAPI server ───────────────────────────────────────────────────
echo "[3/3] Starting Fiscalogix API on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 2 \
    --log-level info \
    --timeout-keep-alive 75
