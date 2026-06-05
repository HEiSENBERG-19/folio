# backend/ — Agent Context

> FastAPI backend with SQLModel ORM, SQLite database, and yfinance integration.

## Module Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, router registration
│   ├── config.py            # Settings (API_V1_PREFIX)
│   ├── database.py          # SQLite engine, get_session dependency
│   ├── models.py            # SQLModel tables: Account, Asset, Transaction, FIFOLot, LotClosure, PriceCache
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── accounts.py      # CRUD for brokerage accounts
│   │   ├── assets.py        # CRUD for tracked assets (stocks)
│   │   ├── transactions.py  # BUY/SELL/DEPOSIT/WITHDRAWAL/FEE transactions
│   │   └── portfolio.py     # Summary, history, allocation endpoints
│   └── services/
│       ├── fifo_engine.py   # FIFO lot matching for sell orders
│       ├── portfolio.py     # Portfolio aggregation and history calculations
│       └── price_service.py # yfinance price fetching with PriceCache
├── tests/
│   ├── conftest.py          # Fixtures: in-memory SQLite session, TestClient
│   ├── test_api.py          # Integration tests for all API endpoints
│   ├── test_fifo_engine.py  # Unit tests for FIFO matching logic
│   ├── test_m1.py           # Milestone 1 validation tests
│   └── test_portfolio.py    # Portfolio calculation tests
├── requirements.txt         # Python dependencies
└── .venv/                   # Virtual environment (not committed)
```

## Key Patterns

- **Dependency injection**: `get_session` provides SQLModel `Session` to route handlers
- **Lifespan handler**: `create_db_and_tables()` runs on app startup
- **CORS**: Allows `http://localhost:5174` for Vite dev server
- **Auto-uppercase**: Asset tickers are normalized to uppercase on creation
- **FIFO engine**: Sell transactions match against oldest open lots first
- **Price caching**: yfinance data cached in `PriceCache` table with `(asset_id, price_date)` unique constraint

## Testing

```bash
# Activate venv and run tests
cd backend && source .venv/bin/activate
python -m pytest -v --tb=short

# Run specific test file
python -m pytest tests/test_fifo_engine.py -v
```

- Tests use in-memory SQLite via `StaticPool` — no file DB needed
- `TestClient` wraps the FastAPI app with session override
- ~50 tests covering API endpoints, FIFO logic, and portfolio calculations

## Adding a New Feature

1. Add models to `models.py` (if new tables needed)
2. Add schemas to `schemas.py` (request/response)
3. Add business logic to `services/` (if complex)
4. Add routes to `routers/` and register in `main.py`
5. Add tests to `tests/`
6. Run `python -m pytest -v` to verify
