# Milestone 6: End-to-End Testing & Validation

## Goal
Perform comprehensive backend integration testing (specifically verifying FIFO math correctness, ledger replay, and caching mechanics) and validate the production-ready frontend build.

## Scope Constraints
- **DO**: Implement full API integration tests using FastAPI's `TestClient` in `tests/test_api.py`.
- **DO**: Program the exact deterministic scenario test for FIFO math correctness.
- **DO**: Run performance checks on caching speeds and build the production bundle for the frontend.
- **DO NOT**: Implement any E2E browser automation scripts (e.g. Playwright, Cypress). Manual validation checks are sufficient for the frontend smoke test.

## Prerequisites
- Milestones 1–5 are completed. Both backend and frontend servers run successfully.

## Tasks

### 6.1 — API Integration Tests
- **`backend/tests/test_api.py`**: Implement the following integration endpoints tests:
  - `test_full_trade_lifecycle`: Create account -> deposit -> buy -> buy -> sell (spanning 2 lots) -> verify summary stats.
  - `test_delete_transaction_replays`: Create 5 transactions, delete the middle transaction, verify cash/lots are correctly recalculated.
  - `test_portfolio_history_data_integrity`: Add transactions across multiple days and fetch history. Confirm correct calculations of value per day.
  - `test_sell_more_than_owned`: Assert that posting a SELL transaction for more shares than currently owned returns HTTP `400 Bad Request`.
  - `test_withdraw_more_than_cash`: Assert that posting a WITHDRAWAL transaction exceeding cash balance returns HTTP `400 Bad Request`.
  - `test_delete_account_with_transactions`: Assert that deleting an account that has associated transactions returns HTTP `409 Conflict`.

### 6.2 — Deterministic Scenario Test (FIFO Math Correctness)
Add a test in `backend/tests/test_api.py` implementing this sequence:
- **Day 1**: DEPOSIT $50,000.00
- **Day 2**: BUY 100 AAPL @ $150.00 (Total cost: $15,000.00) -> Creates Lot A (100 shares @ $150)
- **Day 5**: BUY 50 AAPL @ $160.00 (Total cost: $8,000.00) -> Creates Lot B (50 shares @ $160)
- **Day 10**: BUY 75 GOOGL @ $140.00 (Total cost: $10,500.00) -> Creates Lot C (75 shares @ $140)
- **Day 15**: SELL 120 AAPL @ $170.00 (Total proceeds: $20,400.00)
  - Must close all of Lot A (100 shares @ $150 -> Realized P&L = +$2,000.00)
  - Must close part of Lot B (20 shares @ $160 -> Realized P&L = +$200.00)
  - Remaining Lot B: 30 shares @ $160
- **Day 20**: FEE $50.00

**Expected values to assert on API responses:**
- Account Cash Balance: `$36,850.00`
- Holdings list in `/portfolio/summary`:
  - AAPL: `30` shares, `avg_cost_basis = 160.0`, `market_value` based on current price.
  - GOOGL: `75` shares, `avg_cost_basis = 140.0`.
- Realized P&L: `$2,200.00`.

### 6.3 — Performance Sanity Check
- Seed the DB with 100+ transactions across 5 tickers.
- Benchmark endpoints:
  - `/portfolio/summary` must resolve in < 2 seconds.
  - `/portfolio/history?period=1Y` must resolve in < 5 seconds on initial load, and < 500ms on subsequent requests (validates SQLite price caching).

### 6.4 — Frontend Production Build
- In the `frontend/` directory, compile the application:
  ```bash
  npm run build
  ```
  - Verify that the production build completes successfully with 0 TypeScript or lint errors.

### 6.5 — Manual QA Smoke Checklist (to be executed by Human)
Verify the following user interactions:
1. Navigation: Clicking navigation sidebar links functions without page refreshes.
2. Empty State: Loading application with zero database records renders clean empty states, not UI crashes.
3. Adding Account: Creating an account displays it immediately in form options.
4. Transaction Flow: Creating deposit updates cash cards, buying updates holdings table, and selling displays realized P&L.
5. Deletion: Deleting a transaction immediately updates holdings and P&L cards without refreshing the browser.
6. Chart Intervals: Switching between periods (1M, 3M, 6M, 1Y, ALL) renders data correctly.

## Validation Checkpoint
Verify milestone execution:
1. Run backend tests:
   ```bash
   cd backend && pytest tests/ -v --tb=short
   ```
   -> Expected: All tests pass.
2. Run frontend build:
   ```bash
   cd frontend && npm run build
   ```
   -> Expected: Build succeeds without errors.

## Completion Protocol
Once all items pass verification:
1. Write completion log to `docs/status/m6-complete.md`.
2. Add an entry under `## [v1.0.0]` in `CHANGELOG.md`.
3. Update `AGENTS.md` roadmap status to mark M6 as `[x]`.
4. Report completion to the user and request manual QA.
