# Skill: Python Backend

## When to Use
When working on the FastAPI backend in `backend/app/`.

## Tech Stack
- **Framework**: FastAPI 0.110+
- **ORM**: SQLModel 0.0.16+ (SQLAlchemy + Pydantic)
- **Database**: SQLite (file: `backend/folio.db`)
- **Market Data**: yfinance 0.2.37+
- **HTTP Client**: httpx 0.27+ (for async requests and test client)
- **Testing**: pytest 8.1+

## Commands

```bash
# Activate virtual environment
cd backend && source .venv/bin/activate

# Run all tests
python -m pytest -v

# Run tests with short tracebacks
python -m pytest -v --tb=short

# Run a specific test file
python -m pytest tests/test_api.py -v

# Run with coverage (if pytest-cov installed)
python -m pytest --cov=app --cov-report=html

# Start dev server
uvicorn app.main:app --reload --port 8000

# Lint (if ruff installed)
ruff check app/ tests/
ruff format --check app/ tests/
```

## Project Patterns

### Models (`app/models.py`)
- Use `SQLModel` with `table=True` for database tables
- Use `float` for monetary values (single-user scope)
- Use `datetime.now(timezone.utc)` for timestamps

### Schemas (`app/schemas.py`)
- Pydantic models for request/response validation
- Separate `Create`, `Read`, `Update` schemas per entity

### Routers (`app/routers/`)
- One file per resource: `accounts.py`, `assets.py`, `transactions.py`, `portfolio.py`
- All routes prefixed with `/api/v1` (via `settings.API_V1_PREFIX`)
- Errors return `{"detail": "message"}` with appropriate HTTP status
- Use `Depends(get_session)` for database sessions

### Services (`app/services/`)
- Business logic separated from route handlers
- `holdings_service.py` — Weighted average cost calculations for holdings
- `transaction_service.py` — Transaction processing and validation
- `portfolio.py` — Portfolio summary, history, allocation calculations
- `price_service.py` — yfinance price fetching with SQLite cache
- `csv_import.py` — CSV trade file import and parsing

### Tests (`tests/`)
- `conftest.py` provides `session` (in-memory SQLite) and `client` (TestClient) fixtures
- Tests use `TestClient` from FastAPI, not httpx directly
- Each test file focuses on one area: `test_api.py`, `test_holdings_service.py`, `test_portfolio.py`
- Run `python -m pytest -v` to see current test count

## Conventions
- **No `datetime.utcnow()`** — always `datetime.now(timezone.utc)`
- **Auto-uppercase tickers** on asset creation
- **409 Conflict** for duplicate names/tickers
- **FK-protected deletes** return 409 when referenced entities exist
- **CORS** allows `http://localhost:5174` (Vite dev server)
