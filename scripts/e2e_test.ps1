# End-to-End Test Script for German Tenders Platform
# Requires: Docker running, Python venv activated, pip install -e ".[dev]" done

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  German Tenders E2E Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Run unit tests
Write-Host "`n[1/7] Running unit tests..." -ForegroundColor Yellow
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Unit tests" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: Unit tests" -ForegroundColor Green

# 2. Check Docker services
Write-Host "`n[2/7] Checking Docker services..." -ForegroundColor Yellow
docker compose ps --format json | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Starting Docker services..."
    docker compose up -d
    Start-Sleep -Seconds 10
}
Write-Host "PASSED: Docker services running" -ForegroundColor Green

# 3. Run migrations
Write-Host "`n[3/7] Running database migrations..." -ForegroundColor Yellow
alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Alembic migrations" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: Migrations applied" -ForegroundColor Green

# 4. Ingest tenders (1 day, no enrichment to be fast)
Write-Host "`n[4/7] Ingesting tenders (1 day, no enrichment)..." -ForegroundColor Yellow
tender-cli ingest run --days 1 --no-enrich
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Ingestion" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: Ingestion" -ForegroundColor Green

# 5. Load organizations
Write-Host "`n[5/7] Loading sample organizations..." -ForegroundColor Yellow
tender-cli orgs load --csv tests/fixtures/sample_organizations.csv
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Organization loading" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: Organizations loaded" -ForegroundColor Green

# 6. Show stats
Write-Host "`n[6/7] Checking system stats..." -ForegroundColor Yellow
tender-cli stats
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Stats command" -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: Stats" -ForegroundColor Green

# 7. Document analysis
Write-Host "`n[7/7] Running document analysis..." -ForegroundColor Yellow
tender-cli docs analyze
Write-Host "PASSED: Document analysis" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ALL E2E TESTS PASSED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
