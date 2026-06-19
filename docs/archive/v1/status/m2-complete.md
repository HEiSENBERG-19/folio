# M2 Completion Log — FIFO Core Logic & Python Service Engine

**Status:** ✅ Complete  
**Completed At:** 2026-06-04  
**Agent:** Antigravity (Folio coding agent)

---

## Tasks Completed

### 2.1 — Setup Testing Infrastructure
- Created [conftest.py](../../../../backend/tests/conftest.py) containing standard in-memory SQLite database session and FastAPI `TestClient` fixtures.
- Refactored [test_m1.py](../../../../backend/tests/test_m1.py) to leverage fixtures from `conftest.py` to keep tests DRY.

### 2.2 — Transaction Validation Schemas
- Updated [schemas.py](../../../../backend/app/schemas.py) with the `TransactionCreate` Pydantic model.
- Added model-level validation:
  - For `BUY` and `SELL`: Requires `asset_id`, ensures `quantity` > 0 and `price_per_unit` > 0. Sets `total_amount` to `quantity * price_per_unit` for consistency.
  - For `DEPOSIT`, `WITHDRAWAL`, and `FEE`: Ensures `total_amount` > 0, sets `quantity` and `price_per_unit` to 0.0, and sets `asset_id` to `None`.

### 2.3 — FIFO Engine Service
- Created [fifo_engine.py](../../../../backend/app/services/fifo_engine.py) implementing the core matching engine:
  - `process_sell(session, tx)`: Iterates through open lots ordered by `opened_at` (ascending) and `id` (ascending), consuming shares using FIFO rules and generating `LotClosure` entries with correct realized P&L. Raises `ValueError` if there are insufficient shares.
  - `process_transaction(session, tx)`: Dispatches transaction types (`DEPOSIT`, `WITHDRAWAL`, `FEE`, `BUY`, `SELL`), updating account cash balance and generating `FIFOLot` or triggering FIFO matching accordingly.
  - `replay_ledger(session, account_id)`: Rebuilds ledger state by deleting existing lots and closures, resetting cash balance to 0, and re-applying remaining transactions in execution order.

### 2.4 — Transaction CRUD API Router
- Created [transactions.py](../../../../backend/app/routers/transactions.py) with endpoints:
  - `GET /transactions`: Query/filter transactions by account, asset, or transaction type, with pagination support.
  - `POST /transactions`: Saves transaction, checks existence of account/asset, runs `process_transaction` under a transactional boundary, and returns `201 Created`. Returns `400 Bad Request` on engine `ValueError`.
  - `GET /transactions/{id}`: Retrieves single transaction or returns `404`.
  - `DELETE /transactions/{id}`: Deletes a transaction, triggers `replay_ledger` to rebuild the database state, and returns `204 No Content`.
- Registered the router on the FastAPI application in [main.py](../../../../backend/app/main.py).

### 2.5 — pytest Suite
- Created [test_fifo_engine.py](../../../../backend/tests/test_fifo_engine.py) with 15 test cases verifying:
  - Lot creation, FIFO consumption ordering, partial lot sales, spanning multiple lots, and exact lot closing.
  - Balance constraints, realized P&L calculation, same-date tie-breakers by DB id, and ledger replay execution.
  - REST endpoint operations (list, create errors, get, delete).

---

## Test Results

```
======================== 32 passed, 1 warning in 0.99s =========================
```
All 32 test cases (17 from M1, 15 from M2) are fully passing.

---

## Validation Checkpoint Results

All manual checks passed:
1. Running backend server with uvicorn.
2. Creating an account (`id: 1`) and adding a DEPOSIT of `10,000.0` → `201 Created`.
3. Creating a BUY of `10` AAPL shares at `150.0` (Day 2) → `201 Created`.
4. Creating a SELL of `4` AAPL shares at `170.0` (Day 3) → `201 Created`.
5. DB validation:
   - `quantity_remaining` in `fifolot` is `6.0` (Expected: `6.0`)
   - `realized_pnl` in `lotclosure` is `80.0` (Expected: `80.0`)

---

## Files Created/Modified

- **Modified:**
  - [AGENTS.md](../../../../AGENTS.md)
  - [CHANGELOG.md](../../../../CHANGELOG.md)
  - [backend/app/main.py](../../../../backend/app/main.py)
  - [backend/app/schemas.py](../../../../backend/app/schemas.py)
  - [backend/tests/test_m1.py](../../../../backend/tests/test_m1.py)
- **Created:**
  - [backend/app/services/fifo_engine.py](../../../../backend/app/services/fifo_engine.py)
  - [backend/app/routers/transactions.py](../../../../backend/app/routers/transactions.py)
  - [backend/tests/conftest.py](../../../../backend/tests/conftest.py)
  - [backend/tests/test_fifo_engine.py](../../../../backend/tests/test_fifo_engine.py)
