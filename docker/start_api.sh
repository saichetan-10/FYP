#!/bin/bash
set -e

echo "=== Waiting for PostgreSQL ==="
until pg_isready -h "${DB_HOST:-postgres}" -U "${DB_USER:-nluser}"; do
  echo "  postgres not ready yet, retrying in 2s..."
  sleep 2
done
echo "  PostgreSQL is ready."

echo "=== Checking if databases need seeding ==="
NEEDS_INIT=$(python3 -c "
import os, sys
os.chdir('/app')
try:
    from src.db.manager import DatabaseManager, DatabaseConfig
    db = DatabaseManager(DatabaseConfig(
        engine_type='postgresql',
        host=os.getenv('DB_HOST','postgres'),
        user=os.getenv('DB_USER','nluser'),
        password=os.getenv('DB_PASSWORD','nlpassword'),
        database='nlretrieval_sales',
    ))
    rows = db.query('SELECT COUNT(*) AS c FROM customers')
    count = rows[0]['c'] if rows else 0
    print('0' if count > 0 else '1')
except Exception as e:
    print('1')
" 2>/dev/null)

if [ "$NEEDS_INIT" = "1" ]; then
  echo "=== Seeding databases with ~2M records (first run — takes ~5 min) ==="
  DB_DIALECT=postgresql \
  DB_HOST="${DB_HOST:-postgres}" \
  DB_USER="${DB_USER:-nluser}" \
  DB_PASSWORD="${DB_PASSWORD:-nlpassword}" \
  python3 main.py init
  echo "=== Seeding complete ==="
else
  echo "=== Databases already seeded, skipping init ==="
fi

echo "=== Starting API server ==="
exec uvicorn src.api.backend:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --log-level info
