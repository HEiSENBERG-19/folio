# Milestone 2: FIFO Core Logic & Python Service Engine

## Goal
Implement the business logic service (`fifo_engine.py`) to process BUY, SELL, DEPOSIT, WITHDRAWAL, and FEE transactions, manage FIFO lots, recalculate ledger history on deletion via replay, and create transaction CRUD endpoints.

## Scope Constraints
- **DO**: Implement all transaction validation logic, FIFO lot tracking, cash balance updates, and transaction CRUD routes.
- **DO**: Create a comprehensive unit test suite in `tests/` using pytest, with a `conftest.py` providing standard db fixtures.
- **DO NOT**: Implement price fetching, yfinance caching, portfolio summary/history logic, or frontend UI. Keep these out of scope.

## Prerequisites
- Milestone 1 completed, verified, and database schema active.

## Tasks

### 2.1 — Setup Testing Infrastructure
- Create `backend/tests/conftest.py` containing:
  - An in-memory SQLite engine fixture for test runs.
  - A clean database session fixture that sets up and tears down tables for each test.
  - Standard test client fixture using FastAPI's `TestClient`.

### 2.2 — Transaction Validation Schemas
- **`backend/app/schemas.py`**: Add transaction schemas:
  ```python
  from datetime import datetime
  from typing import Optional
  from pydantic import BaseModel, field_validator
  from app.models import TxType

  class TransactionCreate(BaseModel):
      account_id: int
      asset_id: Optional[int] = None
      tx_type: TxType
      quantity: float = 0.0
      price_per_unit: float = 0.0
      total_amount: float = 0.0
      notes: str = ""
      executed_at: datetime

      @field_validator("tx_type")
      @classmethod
      def validate_tx_rules(cls, v, info):
          # Access other fields from info.data (Pydantic v2)
          # Make sure appropriate fields are present depending on TxType
          return v
  ```
  *Validation Rules*:
  - If `tx_type` is `BUY` or `SELL`: `asset_id` must be provided, `quantity` must be > 0, and `price_per_unit` must be > 0. `total_amount` should be automatically set to `quantity * price_per_unit` if not provided or to ensure consistency.
  - If `tx_type` is `DEPOSIT`, `WITHDRAWAL`, or `FEE`: `total_amount` must be > 0. `quantity` and `price_per_unit` must be 0. `asset_id` should be `None`.

### 2.3 — FIFO Engine Service
- **`backend/app/services/fifo_engine.py`**: Implement three core functions:

#### 1. `process_sell(session, tx) -> list[LotClosure]`
Find open lots for the given account and asset, ordered by `opened_at` (ascending) and `id` (ascending). Consume shares sequentially. Create a `LotClosure` for each consumed lot. Update `quantity_remaining` on the lot. If there are insufficient shares remaining across all lots, raise a `ValueError("Insufficient shares to sell.")`.
```python
from sqlmodel import Session, select
from app.models import FIFOLot, LotClosure, Transaction

def process_sell(session: Session, tx: Transaction) -> list[LotClosure]:
    remaining_to_sell = tx.quantity
    closures: list[LotClosure] = []

    open_lots = session.exec(
        select(FIFOLot)
        .where(FIFOLot.account_id == tx.account_id)
        .where(FIFOLot.asset_id == tx.asset_id)
        .where(FIFOLot.quantity_remaining > 0)
        .order_by(FIFOLot.opened_at.asc(), FIFOLot.id.asc())
    ).all()

    for lot in open_lots:
        if remaining_to_sell <= 0:
            break

        qty_from_this_lot = min(lot.quantity_remaining, remaining_to_sell)
        realized = (tx.price_per_unit - lot.cost_per_unit) * qty_from_this_lot

        closure = LotClosure(
            fifo_lot_id=lot.id,
            sell_transaction_id=tx.id,
            quantity_closed=qty_from_this_lot,
            cost_per_unit=lot.cost_per_unit,
            sell_price_per_unit=tx.price_per_unit,
            realized_pnl=realized,
            closed_at=tx.executed_at  # Align closure timestamp with trade execution
        )
        closures.append(closure)
        session.add(closure)

        lot.quantity_remaining -= qty_from_this_lot
        session.add(lot)

        remaining_to_sell -= qty_from_this_lot

    if remaining_to_sell > 0:
        raise ValueError(
            f"Insufficient shares to sell. Tried to sell {tx.quantity} shares of asset_id={tx.asset_id}, "
            f"but only {tx.quantity - remaining_to_sell} available."
        )

    return closures
```

#### 2. `process_transaction(session, tx) -> None`
Dispatch mutations to the account's cash balance and update/create lots:
- `DEPOSIT`: `account.cash_balance += tx.total_amount`
- `WITHDRAWAL`: check cash, then `account.cash_balance -= tx.total_amount`. Raise `ValueError("Insufficient cash for withdrawal.")` if cash < amount.
- `FEE`: `account.cash_balance -= tx.total_amount`
- `BUY`: check cash, then `account.cash_balance -= cost`. Create new `FIFOLot`. Raise `ValueError("Insufficient cash for purchase.")` if cash < cost.
- `SELL`: add proceeds to cash balance, run `process_sell(session, tx)`.

#### 3. `replay_ledger(session, account_id) -> None`
Rebuild the transaction ledger state from scratch when transaction deletions occur:
1. Delete all `LotClosure` rows associated with the account's lots.
2. Delete all `FIFOLot` rows associated with the account.
3. Reset `Account.cash_balance` to `0.0`.
4. Fetch all remaining transactions for the account, ordered by `executed_at` (ascending) and `id` (ascending).
5. Reprocess each transaction in order using `process_transaction`.

### 2.4 — Transaction CRUD API Router
- **`backend/app/routers/transactions.py`**: Implement the following routes:
  - `GET /transactions`: List transactions. Support query parameters to filter by `account_id`, `asset_id`, or `tx_type`. Support pagination via `skip` and `limit` query parameters.
  - `POST /transactions`: Validate request, check if account and asset (if provided) exist (return `404` if not). Save `Transaction` object. Dispatch to `process_transaction`. Commit and return the created transaction with status `201`. If a `ValueError` is raised, return `400 Bad Request` with `{"detail": "message"}`.
  - `GET /transactions/{id}`: Fetch single transaction or return `404`.
  - `DELETE /transactions/{id}`: Delete transaction from database, then run `replay_ledger` for the transaction's account, commit, and return `204 No Content`.

### 2.5 — pytest Suite
- Create **`backend/tests/test_fifo_engine.py`** with tests verifying:
  - `test_buy_creates_lot`: Check that a BUY creates a new `FIFOLot` and decreases account cash.
  - `test_sell_consumes_oldest_lot_first`: Check FIFO execution ordering.
  - `test_sell_partial_lot`: Check that partial sales decrease `quantity_remaining` correctly.
  - `test_sell_spans_multiple_lots`: Check sequential lot consumption across two BUYs.
  - `test_sell_exact_full_lot`: Check that exact sale quantity fully closes the lot.
  - `test_sell_insufficient_shares`: Check that selling too many shares raises a `ValueError`.
  - `test_realized_pnl_calculation`: Check correct P&L calculations in `LotClosure`.
  - `test_deposit_increases_cash`: Verify cash deposit additions.
  - `test_withdrawal_insufficient_cash`: Verify check on cash limit.
  - `test_fee_decreases_cash`: Verify fee updates cash balance.
  - `test_replay_ledger`: Add transactions, delete a transaction, check rebuilt states match expectations.
  - `test_fifo_order_with_same_date`: Ensure database `id` (insertion order) breaks date ties.

## Validation Checkpoint
Verify milestone execution:
1. Run pytest suite:
   ```bash
   cd backend && pytest tests/test_fifo_engine.py -v
   ```
   -> Expected: All tests pass.
2. Manual verification via API:
   - Deposit cash:
     ```bash
     curl -X POST http://localhost:8000/api/v1/transactions -H "Content-Type: application/json" -d '{"account_id":1,"tx_type":"DEPOSIT","total_amount":10000.0,"executed_at":"2026-06-01T00:00:00Z"}'
     ```
   - Buy shares:
     ```bash
     curl -X POST http://localhost:8000/api/v1/transactions -H "Content-Type: application/json" -d '{"account_id":1,"asset_id":1,"tx_type":"BUY","quantity":10.0,"price_per_unit":150.0,"executed_at":"2026-06-02T10:00:00Z"}'
     ```
   - Sell partial shares:
     ```bash
     curl -X POST http://localhost:8000/api/v1/transactions -H "Content-Type: application/json" -d '{"account_id":1,"asset_id":1,"tx_type":"SELL","quantity":4.0,"price_per_unit":170.0,"executed_at":"2026-06-03T11:00:00Z"}'
     ```
   - Query DB directly to check lot balances and closures:
     ```bash
     sqlite3 folio.db "SELECT quantity_remaining FROM fifolot WHERE id=1;" # Expected: 6.0
     sqlite3 folio.db "SELECT realized_pnl FROM lotclosure WHERE id=1;"    # Expected: 80.0
     ```

## Completion Protocol
Once all items pass verification:
1. Write completion log to `docs/status/m2-complete.md`.
2. Add an entry under `## [v0.2.0]` in `CHANGELOG.md`.
3. Update `AGENTS.md` roadmap status to mark M2 as `[x]`.
4. Report completion to the user and request manual QA.
