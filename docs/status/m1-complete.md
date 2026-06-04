# M1 Completion Log — Backend Setup & Database Layer

**Status:** ✅ Complete  
**Completed At:** 2026-06-04  
**Agent:** Antigravity (Folio coding agent)

---

## Tasks Completed

### 1.1 — Project Scaffolding
- Created `backend/requirements.txt` with all required dependencies.
- Initialized Python virtual environment at `backend/.venv`.
- Installed all dependencies (fastapi, uvicorn, sqlmodel, yfinance, pandas, httpx, pytest).

### 1.2 — Configuration & Database Bootstrap
- Created `backend/app/config.py` with `Settings` class (`DATABASE_URL`, `API_V1_PREFIX`).
- Created `backend/app/database.py` with SQLAlchemy engine, `get_session()` dependency, and `create_db_and_tables()`.
- Created `backend/app/models.py` with all SQLModel table definitions:
  - `Account`, `Asset`, `Transaction`, `FIFOLot`, `LotClosure`, `PriceCache`
  - Used `datetime.now(timezone.utc)` throughout (no deprecated `datetime.utcnow()`)
  - `PriceCache` has `UniqueConstraint("asset_id", "price_date", name="uq_asset_price_date")`

### 1.3 — FastAPI App Factory
- Created `backend/app/main.py`:
  - FastAPI app named "Folio API"
  - CORS middleware allowing `http://localhost:5173`
  - `lifespan` handler calling `create_db_and_tables()` on startup
  - Routers mounted at `/api/v1`
  - Root `GET /` healthcheck returning `{"status": "ok"}`

### 1.4 — Account CRUD Router
- Created `backend/app/schemas.py` with `AccountCreate`, `AccountUpdate`, `AssetCreate`, `AssetUpdate`, `ErrorResponse`.
- Created `backend/app/routers/accounts.py`:
  - `GET /accounts` — list all
  - `POST /accounts` — create with 409 on duplicate name, 201 on success
  - `GET /accounts/{id}` — get or 404
  - `PUT /accounts/{id}` — update name, 409 on duplicate, 404 if not found
  - `DELETE /accounts/{id}` — 204 on success, 409 if transactions exist, 404 if not found

### 1.5 — Asset CRUD Router
- Created `backend/app/routers/assets.py`:
  - `GET /assets` — list all
  - `POST /assets` — create with auto-uppercase ticker, 409 on duplicate, 201 on success
  - `GET /assets/{id}` — get or 404
  - `DELETE /assets/{id}` — 204 on success, 409 if transactions exist, 404 if not found

---

## Test Results

```
17 passed, 1 warning in 1.05s
```

All 17 pytest tests passed on first run. Tests cover:
- Healthcheck endpoint
- Account CRUD: create, duplicate rejection, list, get, update, update-duplicate, delete, delete-not-found
- Asset CRUD: create with uppercase, duplicate rejection, list, get, delete, delete-not-found

---

## Validation Checkpoint Results

All 6 API validation calls passed:

1. `GET /` → `{"status": "ok"}` ✅
2. `POST /api/v1/accounts` with `{"name":"Zerodha"}` → `201 Created` ✅
3. `GET /api/v1/accounts` → JSON array with created account ✅
4. `POST /api/v1/accounts` duplicate name → `409 Conflict` ✅
5. `POST /api/v1/assets` with `{"ticker":"aapl"}` → `201 Created`, ticker saved as `"AAPL"` ✅
6. `folio.db` exists with tables: `account`, `asset`, `fifolot`, `lotclosure`, `pricecache`, `transaction` ✅

---

## Files Created

- `backend/requirements.txt`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/main.py`
- `backend/app/routers/__init__.py`
- `backend/app/routers/accounts.py`
- `backend/app/routers/assets.py`
- `backend/tests/__init__.py`
- `backend/tests/test_m1.py`
