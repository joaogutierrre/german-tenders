#!/bin/bash
set -e

echo "=== German Tenders Platform Setup ==="
echo ""

# 1. Start Docker services
echo "[1/5] Starting Docker services..."
docker compose up -d

# 2. Wait for PostgreSQL
echo "[2/5] Waiting for PostgreSQL..."
until docker compose exec -T db pg_isready -U app -d german_tenders > /dev/null 2>&1; do
    sleep 1
done
echo "  PostgreSQL is ready."

# 3. Wait for MinIO
echo "[3/5] Waiting for MinIO..."
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    sleep 1
done
echo "  MinIO is ready."

# Create MinIO bucket
python -c "
from minio import Minio
client = Minio('localhost:9000', access_key='minioadmin', secret_key='changeme', secure=False)
if not client.bucket_exists('tender-documents'):
    client.make_bucket('tender-documents')
    print('  Bucket tender-documents created.')
else:
    print('  Bucket tender-documents already exists.')
" 2>/dev/null || echo "  (MinIO bucket creation will be handled at runtime)"

# 4. Pull Ollama model
echo "[4/5] Setting up Ollama model..."
bash scripts/setup_ollama.sh

# 5. Run database migrations
echo "[5/5] Running database migrations..."
alembic upgrade head

echo ""
echo "=== Setup complete! ==="
echo "Run 'tender-cli --help' to get started."
