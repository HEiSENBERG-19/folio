# Folio — Technical Architecture

> A lightweight, single-user stock portfolio tracker with weighted average cost (WAC) P&L and automated charting via yfinance.

---

## 1. Database Schema (SQLModel)

All tables live in a single SQLite file (`folio.db`). SQLModel is used for ORM models with Pydantic validation baked in.

```mermaid
erDiagram
    Account ||--o{ Transaction : has
    Asset ||--o{ Transaction : references
    Account ||--o{ Holding : belongs_to
    Asset ||--o{ Holding : references
    Asset ||--o{ PriceCache : cached_for
    Asset ||--o| AssetMetadata : has

    Account {
        int id PK
        string name "UNIQUE, e.g. 'Zerodha', 'IBKR'"
        float cash_balance "Running cash balance"
        string currency "Account base currency, e.g. 'INR'"
        datetime created_at
        datetime updated_at
    }

    Asset {
        int id PK
        string ticker "UNIQUE, e.g. 'AAPL', 'RELIANCE.NS'"
        string name "Human-readable name"
        datetime created_at
    }

    Transaction {
        int id PK
        int account_id FK
        int asset_id FK "NULLABLE — null for DEPOSIT/WITHDRAWAL/FEE"
        string tx_type "BUY | SELL | DEPOSIT | WITHDRAWAL | FEE"
        float quantity "Shares — 0 for DEPOSIT/WITHDRAWAL/FEE"
        float price_per_unit "Execution price — 0 for non-trade txns"
        float total_amount "quantity * price_per_unit, or cash amount"
        string notes "Optional user notes"
        datetime executed_at "User-supplied trade date"
        datetime created_at "Record creation timestamp"
    }

    Holding {
        int id PK
        int account_id FK
        int asset_id FK
        float total_shares "Current number of shares held"
        float total_cost "Total cost basis of shares held"
        float realized_pnl "Accumulated realized P&L from sells"
        datetime created_at
        datetime updated_at
    }

    PriceCache {
        int id PK
        int asset_id FK
        date price_date "Calendar date"
        float close_price "Adjusted close"
        datetime fetched_at "When we fetched this from yfinance"
    }

    AssetMetadata {
        int id PK
        int asset_id FK "UNIQUE"
        string currency "e.g. 'USD', 'INR'"
        string asset_class "e.g. 'Equity', 'ETF', 'Mutual Fund', 'Crypto'"
        string sector "NULLABLE"
        string industry "NULLABLE"
        string country "NULLABLE"
        string exchange "NULLABLE"
        float beta "NULLABLE"
        float market_cap "NULLABLE"
        string long_name "NULLABLE"
        float fifty_two_week_high "NULLABLE"
        float fifty_two_week_low "NULLABLE"
        float trailing_pe "NULLABLE"
        float dividend_yield "NULLABLE"
        float price_to_book "NULLABLE"
        datetime fetched_at
    }
```

### Table Definitions (SQLModel Python)

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
    currency: str = Field(default="INR")
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

class Holding(SQLModel, table=True):
    """Tracks current position per (account, asset) using Weighted Average Cost."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id")
    asset_id: int = Field(foreign_key="asset.id")
    total_shares: float = Field(default=0.0)
    total_cost: float = Field(default=0.0)
    realized_pnl: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PriceCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    price_date: date = Field(index=True)
    close_price: float
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("asset_id", "price_date", name="uq_asset_price_date"),
    )

class AssetMetadata(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", unique=True)
    currency: str = Field(default="USD")
    asset_class: str = Field(default="Equity")
    sector: Optional[str] = Field(default=None)
    industry: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    exchange: Optional[str] = Field(default=None)
    beta: Optional[float] = Field(default=None)
    market_cap: Optional[float] = Field(default=None)
    long_name: Optional[str] = Field(default=None)
    fifty_two_week_high: Optional[float] = Field(default=None)
    fifty_two_week_low: Optional[float] = Field(default=None)
    trailing_pe: Optional[float] = Field(default=None)
    dividend_yield: Optional[float] = Field(default=None)
    price_to_book: Optional[float] = Field(default=None)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

## 2. REST API Endpoints

Base URL: `http://localhost:8000/api/v1`

### Accounts

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|-------------|----------|
| `GET` | `/accounts` | List all accounts | — | `Account[]` |
| `POST` | `/accounts` | Create a new account | `{ name: str, currency?: str }` | `Account` |
| `GET` | `/accounts/{id}` | Get account details | — | `Account` |
| `PUT` | `/accounts/{id}` | Update account name/currency | `{ name: str, currency?: str }` | `Account` |
| `DELETE` | `/accounts/{id}` | Delete account (fails if transactions exist) | — | `204` |

### Assets

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|-------------|----------|
| `GET` | `/assets` | List all tracked assets | — | `Asset[]` |
| `POST` | `/assets` | Add a new asset/ticker | `{ ticker: str, name?: str }` | `Asset` |
| `GET` | `/assets/{id}` | Get asset details | — | `Asset` |
| `DELETE` | `/assets/{id}` | Delete asset (fails if transactions reference it) | — | `204` |

### Transactions

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|-------------|----------|
| `GET` | `/transactions` | List transactions (filterable by `account_id`, `asset_id`, `tx_type`, paginated) | Query params | `Transaction[]` |
| `POST` | `/transactions` | Create a new transaction (triggers holdings calculation) | `TransactionCreate` | `Transaction` |
| `POST` | `/transactions/import` | Import trades from a CSV file | Form Data (`file`) | `CSVImportResult` |
| `GET` | `/transactions/{id}` | Get single transaction | — | `Transaction` |
| `DELETE` | `/transactions/{id}` | Delete transaction (triggers ledger replay and holdings recalculation) | — | `204` |

#### `TransactionCreate` Schema

```python
class TransactionCreate(BaseModel):
    account_id: int
    asset_id: Optional[int] = None     # Required for BUY/SELL
    tx_type: TxType
    quantity: float = 0.0              # Required for BUY/SELL
    price_per_unit: float = 0.0        # Required for BUY/SELL
    total_amount: float = 0.0          # Required for DEPOSIT/WITHDRAWAL/FEE
    notes: str = ""
    executed_at: datetime
```

> [!IMPORTANT]
> **On DELETE of a transaction:** Because holdings and cash balances are updated sequentially, deleting a transaction requires a **ledger replay**. The backend will **delete all Holding records** for that account, reset its cash balance to zero, and **replay all remaining transactions** chronologically. This is described in §3.

### Portfolio (Computed / Read-Only)

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/portfolio/summary` | Current holdings, unrealized P&L per ticker, total portfolio value | `PortfolioSummary` |
| `GET` | `/portfolio/history?period=1Y` | Day-by-day portfolio valuation time-series | `PortfolioHistory` |
| `GET` | `/portfolio/allocation` | Pie-chart data: current market value per ticker | `AllocationSlice[]` |
| `GET` | `/portfolio/insights` | In-depth portfolio metadata analytics, cash holdings and totals | `PortfolioInsights` |

#### Response Schemas

```python
class HoldingDetail(BaseModel):
    ticker: str
    asset_name: str
    total_shares: float
    avg_cost_basis: float        # Weighted average cost of shares held
    current_price: float         # Latest from yfinance
    market_value: float          # total_shares * current_price
    unrealized_pnl: float        # market_value - total_cost
    unrealized_pnl_pct: float    # unrealized_pnl / total_cost * 100
    realized_pnl: float          # Accumulated realized P&L from sells

class PortfolioSummary(BaseModel):
    total_invested: float        # Sum of all holdings' total_cost
    total_market_value: float    # Sum of all holdings' market_value
    total_cash: float            # Sum of all account cash_balances
    total_realized_pnl: float
    total_unrealized_pnl: float
    net_portfolio_value: float   # total_market_value + total_cash
    holdings: list[HoldingDetail]

class PortfolioHistoryPoint(BaseModel):
    date: date
    portfolio_value: float       # Sum of (shares_held * close_price) for each ticker
    cash_balance: float          # Running cash at this point
    total_value: float           # portfolio_value + cash_balance

class PortfolioHistory(BaseModel):
    period: str
    data_points: list[PortfolioHistoryPoint]

class AllocationSlice(BaseModel):
    ticker: str
    market_value: float
    percentage: float

class HoldingInsightDetail(BaseModel):
    ticker: str
    asset_name: str
    total_shares: float
    market_value_native: float
    currency: str
    asset_class: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    beta: Optional[float] = None
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    trailing_pe: Optional[float] = None
    dividend_yield: Optional[float] = None
    price_to_book: Optional[float] = None
    unrealized_pnl_native: float

class CashInsightDetail(BaseModel):
    account_id: int
    account_name: str
    cash_balance_native: float
    currency: str
    stock_value_native: float = 0.0

class PortfolioInsights(BaseModel):
    holdings: list[HoldingInsightDetail]
    cash_balances: list[CashInsightDetail]
```

---

## 3. Holdings Engine — Service Layer Design

### 3.1 Core Principle

Position tracking and P&L calculations are handled using the **Weighted Average Cost (WAC)** method.
- A `BUY` transaction increases the held shares and accumulates the cost basis:
  $$\text{shares}_{\text{new}} = \text{shares}_{\text{old}} + Q$$
  $$\text{cost}_{\text{new}} = \text{cost}_{\text{old}} + (Q \times P)$$
- The average cost basis per share is dynamically computed as:
  $$\text{avg\_cost} = \frac{\text{total\_cost}}{\text{total\_shares}}$$
- A `SELL` transaction reduces the shares and cost basis proportionally based on the current average cost, realizing P&L:
  $$\text{realized\_pnl} = (P_{\text{sell}} - \text{avg\_cost}) \times Q$$
  $$\text{cost}_{\text{new}} = \text{cost}_{\text{old}} - (\text{avg\_cost} \times Q)$$
  $$\text{shares}_{\text{new}} = \text{shares}_{\text{old}} - Q$$

### 3.2 Transaction Processing Pipeline

```mermaid
flowchart TD
    A[New Transaction Received] --> B{tx_type?}
    B -->|DEPOSIT| C[Add total_amount to Account.cash_balance]
    B -->|WITHDRAWAL| D[Subtract total_amount from Account.cash_balance]
    B -->|FEE| E[Subtract total_amount from Account.cash_balance]
    B -->|BUY| F[Subtract total_amount from Account.cash_balance]
    F --> G[Update Holding: Add shares & cost basis]
    B -->|SELL| H[Add total_amount to Account.cash_balance]
    H --> I[Update Holding: Deduct shares & cost basis, accumulate realized_pnl]
```

### 3.3 Holdings Calculation — Python Logic

```python
def apply_buy(session: Session, tx: Transaction) -> None:
    """Apply a BUY transaction: increase total shares and total cost basis."""
    holding = get_or_create_holding(session, tx.account_id, tx.asset_id)
    holding.total_shares += tx.quantity
    holding.total_cost += tx.total_amount
    holding.updated_at = datetime.now(timezone.utc)
    session.add(holding)


def apply_sell(session: Session, tx: Transaction) -> None:
    """Apply a SELL transaction: deduct shares and cost basis, accumulate realized P&L."""
    holding = get_or_create_holding(session, tx.account_id, tx.asset_id)

    if holding.total_shares < tx.quantity:
        raise ValueError(
            f"Insufficient shares to sell. "
            f"Tried to sell {tx.quantity} shares of asset_id={tx.asset_id}, "
            f"but only {holding.total_shares} available."
        )

    avg_cost = holding.total_cost / holding.total_shares if holding.total_shares > 0 else 0.0
    realized = (tx.price_per_unit - avg_cost) * tx.quantity

    holding.realized_pnl += realized
    holding.total_cost -= avg_cost * tx.quantity
    holding.total_shares -= tx.quantity
    holding.updated_at = datetime.now(timezone.utc)

    # Clean up floating point representation issues
    if holding.total_shares < 1e-9:
        holding.total_shares = 0.0
        holding.total_cost = 0.0

    session.add(holding)
```

### 3.4 Full Transaction Processor

```python
def process_transaction(session: Session, tx: Transaction) -> None:
    """Process a single transaction with cash balance validation."""
    account = session.get(Account, tx.account_id)
    if not account:
        raise ValueError(f"Account with id {tx.account_id} not found.")

    # 1. Cash balance updates
    if tx.tx_type == TxType.DEPOSIT:
        account.cash_balance += tx.total_amount
    elif tx.tx_type == TxType.WITHDRAWAL:
        if account.cash_balance < tx.total_amount:
            raise ValueError("Insufficient cash for withdrawal.")
        account.cash_balance -= tx.total_amount
    elif tx.tx_type == TxType.FEE:
        account.cash_balance -= tx.total_amount
    elif tx.tx_type == TxType.BUY:
        if account.cash_balance < tx.total_amount:
            raise ValueError("Insufficient cash for purchase.")
        account.cash_balance -= tx.total_amount
    elif tx.tx_type == TxType.SELL:
        account.cash_balance += tx.total_amount
    session.add(account)

    # 2. Holdings updates
    if tx.tx_type == TxType.BUY:
        apply_buy(session, tx)
    elif tx.tx_type == TxType.SELL:
        apply_sell(session, tx)
```

### 3.5 Ledger Replay (for Transaction Deletion)

When a transaction is deleted, the running cash balances and holdings must be rebuilt to ensure mathematical consistency. The backend wipes the computed holdings and replays all transactions chronologically:

```python
def replay_account_holdings(session: Session, account_id: int) -> None:
    """Rebuild holdings and cash balances for a single account from scratch."""
    account = session.get(Account, account_id)
    if not account:
        raise ValueError(f"Account with id {account_id} not found.")

    # 1. Delete holdings for this account
    holdings = session.exec(
        select(Holding).where(Holding.account_id == account_id)
    ).all()
    for h in holdings:
        session.delete(h)
    session.flush()

    # 2. Reset cash balance
    account.cash_balance = 0.0
    session.add(account)
    session.flush()

    # 3. Replay account transactions in order (without validating negative cash intermediate states)
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.executed_at.asc(), Transaction.id.asc())
    ).all()

    for tx in transactions:
        process_transaction_no_cash_check(session, tx)
```

> [!WARNING]
> Replay cost scales linearly with the number of transactions per account. For a single-user personal tracker this is acceptable (hundreds to low-thousands of transactions).

---

## 4. Portfolio Valuation Time-Series — yfinance Integration

### 4.1 Problem Statement

To render a "Portfolio Value Over Time" line chart, the backend must produce a data point for **every calendar day** from the first transaction to today. Each data point is:

```
total_value(day) = cash_balance(day) + Σ (shares_held(ticker, day) × close_price(ticker, day))
```

The challenges:
1. **Markets are closed on weekends and holidays** — yfinance has no data for those days.
2. **Different tickers may have different trading calendars** (e.g., NYSE vs NSE).
3. **New holdings appear mid-stream** — the share count for a ticker can be 0 before the first BUY.

### 4.2 Algorithm: Ledger Snapshots × Price Matrix

The algorithm has two independent phases that are then joined.

#### Phase A — Build the Daily Ledger Snapshots

Walk through all transactions in chronological order and produce a **running snapshot** of `{ticker: shares_held}` and `cash_balance` for each calendar day.

```python
from datetime import date, timedelta
from collections import defaultdict

def build_daily_snapshots(
    transactions: list[Transaction],
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Returns a list of daily snapshots:
    [
        {
            "date": date(2026, 1, 15),
            "holdings": {"AAPL": 10, "GOOGL": 5},
            "cash": 5000.0,
        },
        ...
    ]
    """
    # Sort transactions by executed_at
    txns_sorted = sorted(transactions, key=lambda t: (t.executed_at, t.id))

    # Build a dict: date -> list of transactions on that date
    txns_by_date: dict[date, list[Transaction]] = defaultdict(list)
    for tx in txns_sorted:
        txns_by_date[tx.executed_at.date()].append(tx)

    snapshots = []
    current_holdings: dict[str, float] = defaultdict(float)  # ticker -> shares
    current_cash: float = 0.0

    current_day = start_date
    while current_day <= end_date:
        # Apply any transactions that occurred on this day
        for tx in txns_by_date.get(current_day, []):
            ticker = get_ticker(tx.asset_id) if tx.asset_id else None
            if tx.tx_type == TxType.DEPOSIT:
                current_cash += tx.total_amount
            elif tx.tx_type == TxType.WITHDRAWAL:
                current_cash -= tx.total_amount
            elif tx.tx_type == TxType.FEE:
                current_cash -= tx.total_amount
            elif tx.tx_type == TxType.BUY:
                current_cash -= tx.total_amount
                if ticker:
                    current_holdings[ticker] += tx.quantity
            elif tx.tx_type == TxType.SELL:
                current_cash += tx.total_amount
                if ticker:
                    current_holdings[ticker] -= tx.quantity

        snapshots.append({
            "date": current_day,
            "holdings": dict(current_holdings),  # copy
            "cash": current_cash,
        })
        current_day += timedelta(days=1)

    return snapshots
```

#### Phase B — Build the Price Matrix (with Forward-Fill)

For every unique ticker that has ever been held, fetch historical daily closes from yfinance. Then **forward-fill** to cover weekends, holidays, and any missing dates.

```python
import yfinance as yf
import pandas as pd

def build_price_matrix(
    tickers: list[str],
    start_date: date,
    end_date: date,
    session: Session,  # for PriceCache reads/writes
) -> dict[str, dict[date, float]]:
    """
    Returns: { "AAPL": { date(2024,1,2): 185.5, date(2024,1,3): 186.0, ... }, ... }
    Gaps (weekends/holidays) are forward-filled with the last known close.
    """
    price_matrix: dict[str, dict[date, float]] = {}
    full_date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    for ticker in tickers:
        # Step 1: Check PriceCache for existing data
        cached = load_cached_prices(session, ticker, start_date, end_date)

        # Step 2: Determine the date range we still need from yfinance
        missing_start, missing_end = find_missing_range(cached, start_date, end_date)

        # Step 3: Fetch missing data from yfinance
        if missing_start and missing_end:
            df = yf.download(
                ticker,
                start=str(missing_start),
                end=str(missing_end + timedelta(days=1)),
                progress=False,
            )
            if not df.empty:
                # Store in PriceCache
                for row_date, row in df.iterrows():
                    upsert_price_cache(
                        session, ticker, row_date.date(), float(row["Close"])
                    )

        # Step 4: Build the final series from cache
        all_prices = load_cached_prices(session, ticker, start_date, end_date)

        # Step 5: Convert to a pandas Series and forward-fill
        price_series = pd.Series(
            {p.price_date: p.close_price for p in all_prices},
            dtype=float,
        )
        # Reindex to the full date range (daily) and forward-fill
        price_series = price_series.reindex(
            full_date_range.date
        ).ffill().bfill()  # bfill only for days before the first trade date

        price_matrix[ticker] = price_series.to_dict()

    return price_matrix
```

> [!TIP]
> **Why `bfill()` at the end?** If the portfolio's `start_date` falls on a Saturday but the first yfinance data point is the preceding Friday, the Saturday–Sunday gap at the start would be `NaN`. A single backward-fill handles this edge case. After that, only forward-fill is used.

#### Phase C — Join Snapshots × Prices

```python
def compute_portfolio_history(
    snapshots: list[dict],
    price_matrix: dict[str, dict[date, float]],
) -> list[PortfolioHistoryPoint]:
    """
    For each daily snapshot, compute the total portfolio value.
    """
    history = []
    for snap in snapshots:
        stock_value = 0.0
        for ticker, shares in snap["holdings"].items():
            if shares > 0:
                price = price_matrix.get(ticker, {}).get(snap["date"], 0.0)
                stock_value += shares * price

        history.append(PortfolioHistoryPoint(
            date=snap["date"],
            portfolio_value=round(stock_value, 2),
            cash_balance=round(snap["cash"], 2),
            total_value=round(stock_value + snap["cash"], 2),
        ))
    return history
```

### 4.3 Price Caching Strategy

| Aspect | Strategy |
|--------|----------|
| **Cache key** | `(asset_id, price_date)` — unique constraint |
| **Cache invalidation** | Today's price is re-fetched on every request (TTL: 0 for current day). Historical dates are immutable once fetched. |
| **Fetch granularity** | One `yf.download()` call per ticker per missing date range. Batch all tickers in a single API layer call. |
| **Storage** | SQLite `PriceCache` table — survives server restarts. |
| **Fallback** | If yfinance fails for a ticker (e.g., delisted), return the last cached price and log a warning. |

### 4.4 Current Price Fetching (for Unrealized P&L)

For the `/portfolio/summary` and `/portfolio/allocation` endpoints, the backend fetches the **latest available price** for each held ticker:

```python
def get_current_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest prices using yfinance Ticker.fast_info or history(period='1d')."""
    prices = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            # fast_info provides the last price without downloading full history
            prices[ticker] = t.fast_info.get("lastPrice", 0.0)
        except Exception:
            # Fallback: use last cached price
            prices[ticker] = get_last_cached_price(ticker)
    return prices
```

### 4.5 Architecture Diagram — Request Flow

```mermaid
sequenceDiagram
    participant FE as React Frontend
    participant API as FastAPI
    participant SVC as Service Layer
    participant DB as SQLite (SQLModel)
    participant YF as yfinance

    Note over FE,YF: Transaction Flow
    FE->>API: POST /api/v1/transactions
    API->>SVC: process_transaction(tx)
    SVC->>DB: INSERT Transaction
    SVC->>DB: INSERT/UPDATE Holding
    SVC->>DB: UPDATE Account.cash_balance
    SVC-->>API: Transaction created
    API-->>FE: 201 Created

    Note over FE,YF: Portfolio History Flow
    FE->>API: GET /api/v1/portfolio/history?period=1Y
    API->>SVC: compute_portfolio_history()
    SVC->>DB: SELECT all Transactions (for snapshots)
    SVC->>DB: SELECT PriceCache (for cached prices)
    SVC->>YF: yf.download() (for missing dates)
    YF-->>SVC: Historical close prices
    SVC->>DB: INSERT into PriceCache (new prices)
    SVC->>SVC: build_daily_snapshots()
    SVC->>SVC: build_price_matrix() (forward-fill)
    SVC->>SVC: join snapshots × prices
    SVC-->>API: PortfolioHistory
    API-->>FE: 200 OK (JSON time-series)

    Note over FE,YF: Summary / Allocation Flow
    FE->>API: GET /api/v1/portfolio/summary
    API->>SVC: get_portfolio_summary()
    SVC->>DB: SELECT Holdings (total_shares > 0)
    SVC->>YF: get_current_prices(tickers)
    SVC->>SVC: Compute unrealized P&L per holding
    SVC->>DB: SELECT realized_pnl from Holdings
    SVC-->>API: PortfolioSummary
    API-->>FE: 200 OK
```

---

## 5. Project Structure

```
folio/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory, CORS, lifespan
│   │   ├── config.py            # Settings (DB path, etc.)
│   │   ├── database.py          # Engine, Session, create_all
│   │   ├── models.py            # All SQLModel table definitions
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── accounts.py      # /api/v1/accounts
│   │   │   ├── assets.py        # /api/v1/assets
│   │   │   ├── transactions.py  # /api/v1/transactions
│   │   │   └── portfolio.py     # /api/v1/portfolio/*
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── holdings_service.py    # Weighted Average Cost holdings logic
│   │   │   ├── transaction_service.py # Transaction processing and ledger replay
│   │   │   ├── portfolio.py           # Summary, history, allocation, insights
│   │   │   ├── price_service.py       # yfinance fetching & PriceCache
│   │   │   └── csv_import.py          # CSV parser and trade history import
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_csv_import.py
│   │   ├── test_holdings_service.py
│   │   ├── test_portfolio.py
│   │   └── test_m1.py
│   ├── requirements.txt
│   └── folio.db                 # SQLite file (gitignored)
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios client and endpoints
│   │   ├── components/
│   │   │   ├── layout/          # Sidebar, Header, Shell
│   │   │   ├── dashboard/       # Summary cards
│   │   │   ├── transactions/    # Table, add trade modal, CSV import modal
│   │   │   ├── ui/              # Reusable primitives
│   │   │   └── charts/          # AllocationDonutChart
│   │   ├── hooks/               # TanStack Query custom hooks
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Transactions.tsx
│   │   │   ├── Holdings.tsx
│   │   │   └── Insights.tsx
│   │   ├── types/               # TypeScript interfaces mirroring backend schemas
│   │   ├── context/             # CurrencyContext
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css            # Global styles and Tailwind imports
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── package.json
└── README.md
```
