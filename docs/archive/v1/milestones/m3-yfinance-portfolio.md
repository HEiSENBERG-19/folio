# Milestone 3: yfinance Integration & Portfolio API Endpoints

## Goal
Implement historical stock price fetching from yfinance with local SQLite caching (forward-filling market closures), and expose computed portfolio metrics (real-time summary, historical value charts, asset allocation).

## Scope Constraints
- **DO**: Implement yfinance HTTP retrieval for missing calendar dates, caching fetched closes in `PriceCache` table.
- **DO**: Handle market closed days (weekends, holidays) by forward-filling the last known price.
- **DO**: Expose computed read-only portfolio endpoints: summary, historical time-series, and allocation slices.
- **DO NOT**: Implement any frontend screens, frontend layouts, frontend routing, or dashboard chart visualization. Keep this backend-only.

## Prerequisites
- Milestone 1 and 2 completed and verified.

## Tasks

### 3.1 — Price Service
- **`backend/app/services/price_service.py`**:
  - Implement price download and caching with the following operations:
    1. `fetch_and_cache_prices(session, ticker, start_date, end_date)`:
       - Check `PriceCache` for cached dates. Identify any gaps.
       - Download missing date ranges from yfinance: `yf.download(ticker, start=missing_start, end=missing_end)`.
       - Write new dates back to `PriceCache`. Handle yfinance exceptions gracefully (log warning, return cached fallback).
    2. `get_current_prices(tickers: list[str]) -> dict[str, float]`:
       - Fetch current market prices using `yf.Ticker(ticker).fast_info.get("lastPrice", None)` or standard history calls.
       - Fallback to the latest price in `PriceCache` if yfinance is unreachable.
    3. `build_price_matrix(session, tickers, start_date, end_date) -> dict[str, dict[date, float]]`:
       - Construct daily prices dictionary matching every calendar date in range.
       - Use Pandas to reindex and forward-fill weekend/holiday price gaps (and backward-fill `bfill()` for start of range gaps).
       - Returns structure: `{"AAPL": {date(2026, 6, 1): 180.0, ...}}`.

### 3.2 — Portfolio Service
- **`backend/app/services/portfolio.py`**: Implement core portfolio calculators:
  - `get_portfolio_summary(session) -> PortfolioSummary`:
    - Aggregate open lots (where `quantity_remaining > 0`) per asset.
    - Calculate weighted average cost basis (`avg_cost_basis`) from original transaction prices.
    - Fetch current prices via `price_service.get_current_prices()`.
    - Compute `market_value` (`total_shares * current_price`), `unrealized_pnl` (`market_value - (shares * avg_cost)`), `unrealized_pnl_pct`.
    - Fetch total realized P&L from `LotClosure` rows.
    - Return full summary aggregates.
  - `get_portfolio_history(session, period: str) -> PortfolioHistory`:
    - Parse period (1M, 3M, 6M, 1Y, ALL) to determine start date.
    - Walk transactions in chronological order to build running snapshots of `{ticker: shares_held}` and `cash_balance` for every calendar day.
    - Generate price matrix for active tickers across the period.
    - Join snapshots with prices to compute the daily portfolio value:
      `total_value = cash + sum(shares * price)`.
  - `get_portfolio_allocation(session) -> list[AllocationSlice]`:
    - Calculate holdings' current market values and return percentage shares of the total portfolio value.

### 3.3 — Portfolio API Router
- **`backend/app/schemas.py`**: Add response Pydantic models:
  ```python
  from datetime import date
  from pydantic import BaseModel
  from typing import List

  class HoldingDetail(BaseModel):
      ticker: str
      asset_name: str
      total_shares: float
      avg_cost_basis: float
      current_price: float
      market_value: float
      unrealized_pnl: float
      unrealized_pnl_pct: float
      realized_pnl: float

  class PortfolioSummary(BaseModel):
      total_invested: float
      total_market_value: float
      total_cash: float
      total_realized_pnl: float
      total_unrealized_pnl: float
      net_portfolio_value: float
      holdings: List[HoldingDetail]

  class PortfolioHistoryPoint(BaseModel):
      date: date
      portfolio_value: float
      cash_balance: float
      total_value: float

  class PortfolioHistory(BaseModel):
      period: str
      data_points: List[PortfolioHistoryPoint]

  class AllocationSlice(BaseModel):
      ticker: str
      market_value: float
      percentage: float
  ```
- **`backend/app/routers/portfolio.py`**: Expose endpoints:
  - `GET /portfolio/summary` -> returns `PortfolioSummary`
  - `GET /portfolio/history?period=1Y` -> returns `PortfolioHistory`
  - `GET /portfolio/allocation` -> returns `List[AllocationSlice]`

### 3.4 — pytest Suite for Pricing/Portfolio
- **`backend/tests/test_portfolio.py`**: Add tests:
  - `test_price_cache_stores_fetched_data`: Fetch stores rows in cache.
  - `test_price_cache_avoids_refetch`: Subsequent call mock verifies yfinance is bypassed.
  - `test_forward_fill_weekends`: Friday close forward-fills Saturday and Sunday.
  - `test_portfolio_summary_empty`: Empty states return zero values.
  - `test_unrealized_pnl_calculation`: Test portfolio summary equations.
  - `test_portfolio_history_shape`: Check date counts return correctly.

## Validation Checkpoint
Verify milestone execution:
1. Run pytest suite:
   ```bash
   cd backend && pytest tests/ -v
   ```
   -> Expected: All M2 & M3 tests pass.
2. Run manual endpoint integration with live tickers:
   - Perform cash DEPOSIT and buy standard live tickers (e.g. `AAPL`, `MSFT`).
   - Call portfolio endpoints:
     ```bash
     curl http://localhost:8000/api/v1/portfolio/summary
     curl "http://localhost:8000/api/v1/portfolio/history?period=1M"
     curl http://localhost:8000/api/v1/portfolio/allocation
     ```
   - Verify `PriceCache` table populated using `sqlite3 folio.db "SELECT * FROM pricecache;"`.
   - Assert second history call completes instantly due to cached data.

## Completion Protocol
Once all items pass verification:
1. Write completion log to `docs/status/m3-complete.md`.
2. Add an entry under `## [v0.3.0]` in `CHANGELOG.md`.
3. Update `AGENTS.md` roadmap status to mark M3 as `[x]`.
4. Report completion to the user and request manual QA.
