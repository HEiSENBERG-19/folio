# Milestone 1: Minimal Backend Setup & Database Layer

## Goal
A running FastAPI server with SQLite database, SQLModel tables created, and basic CRUD API endpoints for Accounts and Assets.

## Scope Constraints
- **DO**: Set up Python virtual environment, dependencies (`requirements.txt`), config, database engine/session, and the FastAPI application shell.
- **DO**: Implement tables for all models with correct relationships, indices, and constraints.
- **DO**: Enforce unique constraints on Account names, Asset tickers (auto-uppercased), and PriceCache (composite asset+date).
- **DO NOT**: Implement any transaction logging, FIFO engine math, yfinance price fetching, portfolio math, or frontend UI. Keep all of these out of scope for now.

## Prerequisites
- None (Initial step of the repository build).

## Tasks

### 1.1 — Project Scaffolding
Set up the backend structure in the `backend/` directory:
- Create `backend/requirements.txt` with:
  ```text
  fastapi>=0.110.0
  uvicorn[standard]>=0.29.0
  sqlmodel>=0.0.16
  yfinance>=0.2.37
  pandas>=2.2.0
  httpx>=0.27.0
  pytest>=8.1.0
  ```
- Initialize a Python virtual environment: `python -m venv .venv` and install the requirements: `pip install -r requirements.txt`.

### 1.2 — Configuration & Database Bootstrap
- **`backend/app/config.py`**: Define a `Settings` class using Pydantic Settings (or basic class):
  - `DATABASE_URL: str = "sqlite:///./folio.db"`
  - `API_V1_PREFIX: str = "/api/v1"`
- **`backend/app/database.py`**:
  - Set up SQLAlchemy engine: `engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})`.
  - Define `get_session()` dependency yielding a `sqlmodel.Session`.
  - Define `create_db_and_tables()` calling `SQLModel.metadata.create_all(engine)`.
- **`backend/app/models.py`**: Implement the SQLModel classes.
  - **CRITICAL CONVENTION**: Use `datetime.now(timezone.utc)` (from standard `datetime` module) instead of the deprecated `datetime.utcnow()`.
  - Enforce `UniqueConstraint("asset_id", "price_date")` on `PriceCache` inside `__table_args__`.
  - Define the following schema fields exactly:

```python
from datetime import datetime, date, timezone
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field, UniqueConstraint

class TxType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FEE = "FEE"

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    cash_balance: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True, unique=True)
    name: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id")
    asset_id: Optional[int] = Field(default=None, foreign_key="asset.id")
    tx_type: TxType
    quantity: float = Field(default=0.0)
    price_per_unit: float = Field(default=0.0)
    total_amount: float = Field(default=0.0)
    notes: str = Field(default="")
    executed_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FIFOLot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id")
    asset_id: int = Field(foreign_key="asset.id")
    open_transaction_id: int = Field(foreign_key="transaction.id")
    quantity_purchased: float
    quantity_remaining: float
    cost_per_unit: float
    opened_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LotClosure(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fifo_lot_id: int = Field(foreign_key="fifolot.id")
    sell_transaction_id: int = Field(foreign_key="transaction.id")
    quantity_closed: float
    cost_per_unit: float
    sell_price_per_unit: float
    realized_pnl: float
    closed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PriceCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    price_date: date = Field(index=True)
    close_price: float
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("asset_id", "price_date", name="uq_asset_price_date"),
    )
```

### 1.3 — FastAPI App Factory
- **`backend/app/main.py`**:
  - Initialize the FastAPI app named "Folio API".
  - Configure CORS middleware to permit origin `http://localhost:5174` (Vite frontend dev server).
  - Use `lifespan` handler to trigger `create_db_and_tables()` on startup.
  - Mount routing handlers for accounts and assets under `/api/v1`.
  - Add simple root GET `/` healthcheck endpoint returning `{"status": "ok"}`.

### 1.4 — Account CRUD Router
- **`backend/app/schemas.py`**: Create standard payload schemas:
  ```python
  from pydantic import BaseModel

  class AccountCreate(BaseModel):
      name: str

  class AccountUpdate(BaseModel):
      name: str

  class ErrorResponse(BaseModel):
      detail: str
  ```
- **`backend/app/routers/accounts.py`**: Implement CRUD routes:
  - `GET /accounts`: List all accounts.
  - `POST /accounts`: Create new account. Reject duplicate names with HTTP `409 Conflict`.
  - `GET /accounts/{id}`: Return account or raise HTTP `404 Not Found`.
  - `PUT /accounts/{id}`: Update account name. Reject duplicate names with HTTP `409 Conflict`.
  - `DELETE /accounts/{id}`: Delete account. If transactions refer to this account, reject with HTTP `409 Conflict`. Otherwise delete and return `204 No Content`.

### 1.5 — Asset CRUD Router
- **`backend/app/routers/assets.py`**: Implement CRUD routes:
  - `GET /assets`: List all tracked assets.
  - `POST /assets`: Create new asset. Automatically uppercase the ticker (e.g. `aapl` -> `AAPL`). Reject duplicate tickers with HTTP `409 Conflict`.
  - `GET /assets/{id}`: Return asset details or raise HTTP `404 Not Found`.
  - `DELETE /assets/{id}`: Delete asset. If transactions exist referencing this asset, reject with HTTP `409 Conflict`. Otherwise delete and return `204 No Content`.

## Validation Checkpoint
Verify functionality by running the backend:
```bash
cd backend && uvicorn app.main:app --reload
```
Perform the following validation calls:
1. `curl http://localhost:8000/` -> Expected: `{"status":"ok"}`
2. Create Account:
   ```bash
   curl -i -X POST http://localhost:8000/api/v1/accounts -H "Content-Type: application/json" -d '{"name":"Zerodha"}'
   ```
   -> Expected: `201 Created` with created Account JSON.
3. List Accounts:
   ```bash
   curl http://localhost:8000/api/v1/accounts
   ```
   -> Expected: JSON array containing the created account.
4. Try duplicate account name:
   -> Expected: `409 Conflict`.
5. Create Asset:
   ```bash
   curl -i -X POST http://localhost:8000/api/v1/assets -H "Content-Type: application/json" -d '{"ticker":"aapl","name":"Apple Inc."}'
   ```
   -> Expected: `201 Created` with ticker saved as `"AAPL"`.
6. Database verification:
   Verify `folio.db` exists in `backend/` and verify table schemas:
   ```bash
   sqlite3 folio.db ".tables"
   ```
   -> Expected: `account`, `asset`, `transaction`, `fifolot`, `lotclosure`, `pricecache`.

## Completion Protocol
Once all items pass verification:
1. Write completion log to `docs/status/m1-complete.md` following the standard template.
2. Add an entry under `## [v0.1.0]` in `CHANGELOG.md`.
3. Update `AGENTS.md` roadmap status to mark M1 as `[x]`.
4. Report completion to the user and request manual QA.
