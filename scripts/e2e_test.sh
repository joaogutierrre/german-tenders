#!/bin/bash
# End-to-End Test Script for German Tenders Platform
# Requires: Docker running, Python venv activated, pip install -e ".[dev]" done

set -e

echo "========================================"
echo "  German Tenders E2E Test"
echo "========================================"

# 1. Run unit tests
echo -e "\n[1/7] Running unit tests..."
python -m pytest tests/ -v --tb=short
echo "PASSED: Unit tests"

# 2. Check Docker services
echo -e "\n[2/7] Checking Docker services..."
docker compose ps > /dev/null 2>&1 || {
    echo "Starting Docker services..."
    docker compose up -d
    sleep 10
}
echo "PASSED: Docker services running"

# 3. Run migrations
echo -e "\n[3/7] Running database migrations..."
alembic upgrade head
echo "PASSED: Migrations applied"

# 4. Ingest tenders (1 day, no enrichment to be fast)
echo -e "\n[4/7] Ingesting tenders (1 day, no enrichment)..."
tender-cli ingest run --days 1 --no-enrich
echo "PASSED: Ingestion"

# 5. Load organizations
echo -e "\n[5/7] Loading sample organizations..."
tender-cli orgs load --csv tests/fixtures/sample_organizations.csv
echo "PASSED: Organizations loaded"

# 6. Show stats
echo -e "\n[6/7] Checking system stats..."
tender-cli stats
echo "PASSED: Stats"

# 7. Document analysis
echo -e "\n[7/7] Running document analysis..."
tender-cli docs analyze
echo "PASSED: Document analysis"

echo -e "\n========================================"
echo "  ALL E2E TESTS PASSED"
echo "========================================"
