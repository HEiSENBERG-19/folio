---
name: "Phase 1: Remove FIFO, Remove USD, Add Weighted Average Cost"
status: Completed
priority: high
created: 2026-06-05
updated: 2026-06-05
progress:
  - "[x] Task 1: Add Holding model, keep old tables for migration"
  - "[x] Task 2: Create holdings_service.py with WAC logic"
  - "[x] Task 3: Create transaction_service.py orchestrator"
  - "[x] Task 4: Refactor portfolio.py to read from Holding"
  - "[x] Task 5: Delete fifo_engine.py entirely"
  - "[x] Task 6: Update transaction router"
  - "[x] Task 7: Strip all USD code from backend"
  - "[x] Task 8: Strip all USD code from frontend"
  - "[x] Task 9: Decompose Insights.tsx into components"
  - "[x] Task 10: Update and run backend tests"
  - "[x] Task 11: Frontend build verification"
---

# Phase 1: Remove FIFO, Remove USD, Add Weighted Average Cost

## Summary

Remove the entire FIFO lot-matching system (FIFOLot, LotClosure, fifo_engine.py) and replace it with a simple **Weighted Average Cost (WAC)** holdings model. Remove all USD support — currency toggle, conversion logic, USD-INR rate fetching. Hardcode everything to INR. Decompose the monolithic Insights page.

## Motivation

1. **FIFO is unnecessary complexity.** The user tracks Indian stocks through a single-user portfolio app. Weighted Average Cost is the standard method used by Indian brokers and is far simpler. FIFO requires lot tracking, lot closures, and complex matching — all of which slow down the codebase and make CSV import harder.

2. **USD is dead weight.** The user doesn't trade US stocks. The currency toggle, the `USDINR=X` yfinance call on every Insights page load, the `convert()` function, the CurrencyContext toggle — all waste code, complexity, and API calls.

3. **WAC is simpler and correct.** One `Holding` row per (account, asset) pair. BUY adds shares and cost. SELL removes proportional cost and records realized P&L. No lots, no closures.

## Acceptance Criteria

1. `FIFOLot` and `LotClosure` model classes are removed from `models.py`. The database tables can remain (SQLite doesn't need cleanup), but no code references them.
2. `fifo_engine.py` is deleted entirely.
3. A new `Holding` model exists with fields: `account_id`, `asset_id`, `total_shares`, `total_cost`, `realized_pnl`.
4. New `holdings_service.py` handles WAC buy/sell logic.
5. New `transaction_service.py` orchestrates: persist tx → update holding → update cash balance.
6. `portfolio.py` reads from `Holding` instead of `FIFOLot`.
7. All USD references removed: no currency toggle in sidebar, no `CurrencyContext` toggle state, no `convert()` function in Insights, no `usd_inr_rate` in API, no `get_usd_inr_rate()` call.
8. `formatCurrency` always formats INR with `en-IN` locale.
9. `Insights.tsx` is under 450 lines via extracted chart components.
10. All backend tests pass. `npm run build` passes.
11. On first startup after migration, existing transactions are replayed to populate the `Holding` table.

---

## Technical Design

### Backend

---

#### Task 1: Update `models.py`

**Remove these classes entirely:**
- `FIFOLot`
- `LotClosure`

**Add this class:**

```python
class Holding(SQLModel, table=True):
    """Tracks current position per (account, asset) using Weighted Average Cost."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id")
    asset_id: int = Field(foreign_key="asset.id")
    total_shares: float = Field(default=0.0)
    total_cost: float = Field(default=0.0)      # total cost basis of shares held
    realized_pnl: float = Field(default=0.0)     # accumulated realized P&L from sells
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**Keep everything else** (`Account`, `Asset`, `Transaction`, `PriceCache`, `AssetMetadata`, `TxType`).

**Important:** Leave the `Account.currency` column in the DB (defaults to `'INR'`) — removing a column from SQLite is painful. Just stop exposing any USD choice.

The final `models.py` will contain: `TxType`, `Account`, `Asset`, `Transaction`, `Holding`, `PriceCache`, `AssetMetadata`.

---

#### Task 2: Create `holdings_service.py`

**New file:** `backend/app/services/holdings_service.py`

```python
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models import Holding, Transaction, TxType


def get_or_create_holding(session: Session, account_id: int, asset_id: int) -> Holding:
    """Get existing holding or create a new one."""
    holding = session.exec(
        select(Holding)
        .where(Holding.account_id == account_id)
        .where(Holding.asset_id == asset_id)
    ).first()
    if not holding:
        holding = Holding(
            account_id=account_id,
            asset_id=asset_id,
            total_shares=0.0,
            total_cost=0.0,
            realized_pnl=0.0,
        )
        session.add(holding)
        session.flush()
    return holding


def apply_buy(session: Session, tx: Transaction) -> None:
    """Apply a BUY transaction using Weighted Average Cost.

    WAC BUY logic:
      holding.total_shares += tx.quantity
      holding.total_cost   += tx.total_amount
      (avg cost recalculates automatically as total_cost / total_shares)
    """
    holding = get_or_create_holding(session, tx.account_id, tx.asset_id)
    holding.total_shares += tx.quantity
    holding.total_cost += tx.total_amount
    holding.updated_at = datetime.now(timezone.utc)
    session.add(holding)


def apply_sell(session: Session, tx: Transaction) -> None:
    """Apply a SELL transaction using Weighted Average Cost.

    WAC SELL logic:
      avg_cost = holding.total_cost / holding.total_shares
      realized = (tx.price_per_unit - avg_cost) * tx.quantity
      holding.realized_pnl  += realized
      holding.total_cost     -= avg_cost * tx.quantity
      holding.total_shares   -= tx.quantity

    Raises ValueError if insufficient shares.
    """
    holding = get_or_create_holding(session, tx.account_id, tx.asset_id)

    if holding.total_shares < tx.quantity:
        raise ValueError(
            f"Insufficient shares to sell. "
            f"Tried to sell {tx.quantity} shares of asset_id={tx.asset_id}, "
            f"but only {holding.total_shares} available in account_id={tx.account_id}."
        )

    avg_cost = holding.total_cost / holding.total_shares if holding.total_shares > 0 else 0.0
    realized = (tx.price_per_unit - avg_cost) * tx.quantity

    holding.realized_pnl += realized
    holding.total_cost -= avg_cost * tx.quantity
    holding.total_shares -= tx.quantity
    holding.updated_at = datetime.now(timezone.utc)

    # Clean up floating point: if shares are effectively zero, zero out cost too
    if holding.total_shares < 1e-9:
        holding.total_shares = 0.0
        holding.total_cost = 0.0

    session.add(holding)
```

---

#### Task 3: Create `transaction_service.py`

**New file:** `backend/app/services/transaction_service.py`

```python
from sqlmodel import Session, select
from app.models import Transaction, Account, Holding, TxType
from app.services.holdings_service import apply_buy, apply_sell


def process_transaction(session: Session, tx: Transaction) -> None:
    """Process a single transaction: update cash balance + update holding.

    Called by:
      - Transaction router (single transaction create)
      - replay_all_holdings (bulk rebuild)
      - CSV import service (batch import)
    """
    account = session.get(Account, tx.account_id)
    if not account:
        raise ValueError(f"Account with id {tx.account_id} not found.")

    # 1. Cash balance effects
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

    # 2. Holding effects (only for BUY/SELL)
    if tx.tx_type == TxType.BUY:
        apply_buy(session, tx)
    elif tx.tx_type == TxType.SELL:
        apply_sell(session, tx)


def process_transaction_no_cash_check(session: Session, tx: Transaction) -> None:
    """Process a transaction WITHOUT cash balance validation.

    Used by CSV import where the user is recording historical trades
    that already happened on a broker. Cash still gets updated
    (so the running balance stays correct), but negative balances
    are allowed for BUY and WITHDRAWAL.
    """
    account = session.get(Account, tx.account_id)
    if not account:
        raise ValueError(f"Account with id {tx.account_id} not found.")

    # Cash balance effects (no validation)
    if tx.tx_type == TxType.DEPOSIT:
        account.cash_balance += tx.total_amount
    elif tx.tx_type == TxType.WITHDRAWAL:
        account.cash_balance -= tx.total_amount
    elif tx.tx_type == TxType.FEE:
        account.cash_balance -= tx.total_amount
    elif tx.tx_type == TxType.BUY:
        account.cash_balance -= tx.total_amount
    elif tx.tx_type == TxType.SELL:
        account.cash_balance += tx.total_amount
    session.add(account)

    # Holding effects
    if tx.tx_type == TxType.BUY:
        apply_buy(session, tx)
    elif tx.tx_type == TxType.SELL:
        apply_sell(session, tx)


def replay_all_holdings(session: Session) -> None:
    """Rebuild ALL holdings and cash balances from scratch.

    Steps:
      1. Delete all Holding rows.
      2. Reset all account cash_balances to 0.
      3. Fetch all transactions sorted by (executed_at, id).
      4. Replay each through process_transaction_no_cash_check.

    This is the migration path and the recovery mechanism.
    Called on startup if Holding table is empty but transactions exist.
    """
    # 1. Delete all holdings
    holdings = session.exec(select(Holding)).all()
    for h in holdings:
        session.delete(h)
    session.flush()

    # 2. Reset cash balances
    accounts = session.exec(select(Account)).all()
    for account in accounts:
        account.cash_balance = 0.0
        session.add(account)
    session.flush()

    # 3. Replay all transactions
    transactions = session.exec(
        select(Transaction)
        .order_by(Transaction.executed_at.asc(), Transaction.id.asc())
    ).all()

    for tx in transactions:
        process_transaction_no_cash_check(session, tx)

    session.commit()


def replay_account_holdings(session: Session, account_id: int) -> None:
    """Rebuild holdings for a single account. Used after deleting a transaction."""
    account = session.get(Account, account_id)
    if not account:
        raise ValueError(f"Account with id {account_id} not found.")

    # Delete holdings for this account
    holdings = session.exec(
        select(Holding).where(Holding.account_id == account_id)
    ).all()
    for h in holdings:
        session.delete(h)
    session.flush()

    # Reset cash balance
    account.cash_balance = 0.0
    session.add(account)
    session.flush()

    # Replay account transactions
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.executed_at.asc(), Transaction.id.asc())
    ).all()

    for tx in transactions:
        process_transaction_no_cash_check(session, tx)
```

---

#### Task 4: Refactor `portfolio.py`

**Replace all `FIFOLot` and `LotClosure` references with `Holding`.**

Key changes to `get_portfolio_summary()`:

```python
# OLD: Read open FIFOLots, group by asset, sum remaining quantities
# NEW: Read Holdings with total_shares > 0

def get_portfolio_summary(session: Session) -> PortfolioSummary:
    assets = session.exec(select(Asset)).all()
    asset_map = {a.id: a for a in assets}

    # Get all holdings with shares > 0
    holdings_db = session.exec(
        select(Holding).where(Holding.total_shares > 0)
    ).all()

    # Group by asset_id (merge holdings across accounts)
    asset_holdings: dict[int, list[Holding]] = {}
    for h in holdings_db:
        asset_holdings.setdefault(h.asset_id, []).append(h)

    # Get active tickers for price fetch
    active_assets = [asset_map[aid] for aid in asset_holdings if aid in asset_map]
    active_tickers = [a.ticker for a in active_assets]

    current_prices = {}
    if active_tickers:
        current_prices = price_service.get_current_prices(session, active_tickers)

    holdings = []
    total_invested = 0.0
    total_market_value = 0.0

    for asset in active_assets:
        h_list = asset_holdings[asset.id]
        total_shares = sum(h.total_shares for h in h_list)
        total_cost = sum(h.total_cost for h in h_list)
        avg_cost_basis = total_cost / total_shares if total_shares > 0 else 0.0

        current_price = current_prices.get(asset.ticker, 0.0)
        market_value = total_shares * current_price
        unrealized_pnl = market_value - total_cost
        unrealized_pnl_pct = (unrealized_pnl / total_cost * 100.0) if total_cost > 0 else 0.0

        # Realized PNL for this asset (sum across accounts)
        realized_pnl = sum(h.realized_pnl for h in h_list)

        holdings.append(HoldingDetail(
            ticker=asset.ticker,
            asset_name=asset.name,
            total_shares=total_shares,
            avg_cost_basis=avg_cost_basis,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            realized_pnl=realized_pnl,
        ))

        total_invested += total_cost
        total_market_value += market_value

    # Total realized PNL
    all_holdings = session.exec(select(Holding)).all()
    total_realized_pnl = sum(h.realized_pnl for h in all_holdings)

    # Total cash
    accounts = session.exec(select(Account)).all()
    total_cash = sum(acc.cash_balance for acc in accounts)

    total_unrealized_pnl = total_market_value - total_invested
    net_portfolio_value = total_market_value + total_cash

    return PortfolioSummary(
        total_invested=total_invested,
        total_market_value=total_market_value,
        total_cash=total_cash,
        total_realized_pnl=total_realized_pnl,
        total_unrealized_pnl=total_unrealized_pnl,
        net_portfolio_value=net_portfolio_value,
        holdings=holdings,
    )
```

**Changes to `get_portfolio_insights()`:**

Replace this block (currently reads FIFOLot for stock value per account):
```python
# OLD
open_lots = session.exec(select(FIFOLot).where(FIFOLot.quantity_remaining > 0)).all()
account_stock_val = {}
for lot in open_lots:
    ...
```

With:
```python
# NEW
holdings_db = session.exec(select(Holding).where(Holding.total_shares > 0)).all()
account_stock_val: dict[int, float] = {}
for h in holdings_db:
    asset = asset_id_map.get(h.asset_id)
    if asset:
        price = price_map.get(asset.ticker, 0.0)
        val = h.total_shares * price
        account_stock_val[h.account_id] = account_stock_val.get(h.account_id, 0.0) + val
```

**Remove `get_usd_inr_rate()` function entirely.** (~13 lines, saves a yfinance API call)

**Remove `usd_inr_rate` from the `get_portfolio_insights()` return value.**

**`get_portfolio_history()`** — NO CHANGES. It already uses a running shares model from transactions, not FIFO.

**`get_portfolio_allocation()`** — NO CHANGES. It calls `get_portfolio_summary()` which we're updating.

---

#### Task 5: Delete `fifo_engine.py`

**Delete the entire file:** `backend/app/services/fifo_engine.py`

No other file should import from it after the refactor.

---

#### Task 6: Update transaction router

**Modify:** `backend/app/routers/transactions.py`

Change imports:
```python
# OLD
from app.services.fifo_engine import process_transaction, replay_ledger

# NEW
from app.services.transaction_service import process_transaction, replay_account_holdings
```

Change the delete handler:
```python
# OLD
replay_ledger(session, account_id)

# NEW
replay_account_holdings(session, account_id)
```

Everything else stays the same — `process_transaction()` has the same signature.

---

#### Task 7: Strip all USD code from backend

**Modify:** `backend/app/schemas.py`

1. Remove `usd_inr_rate` field from `PortfolioInsights`:
```python
# OLD
class PortfolioInsights(BaseModel):
    holdings: list[HoldingInsightDetail]
    cash_balances: list[CashInsightDetail]
    usd_inr_rate: float

# NEW
class PortfolioInsights(BaseModel):
    holdings: list[HoldingInsightDetail]
    cash_balances: list[CashInsightDetail]
```

2. Change `AccountCreate` default currency to `'INR'`:
```python
class AccountCreate(BaseModel):
    name: str
    currency: Optional[str] = "INR"
```

**Modify:** `backend/app/models.py`

Change `Account.currency` default:
```python
currency: str = Field(default="INR")
```

**Modify:** `backend/app/services/portfolio.py`

- Delete the `get_usd_inr_rate()` function entirely
- Remove `usd_inr_rate` from `get_portfolio_insights()` return

**Modify:** `backend/app/database.py`

Update the migration to default existing accounts to `'INR'`:
```python
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    from sqlalchemy import text
    with engine.begin() as conn:
        # Migrate: add currency column if missing
        try:
            conn.execute(text("SELECT currency FROM account LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE account ADD COLUMN currency VARCHAR DEFAULT 'INR'"))
            except Exception as e:
                print(f"Migration error: {e}")

    # Auto-replay: populate Holding table if empty but transactions exist
    from app.models import Holding, Transaction
    from sqlmodel import Session
    with Session(engine) as session:
        has_holdings = session.exec(select(Holding).limit(1)).first()
        has_transactions = session.exec(select(Transaction).limit(1)).first()
        if not has_holdings and has_transactions:
            from app.services.transaction_service import replay_all_holdings
            replay_all_holdings(session)
```

---

#### Task 8: Strip all USD code from frontend

**Modify:** `frontend/src/context/CurrencyContext.tsx`

Remove toggle state, remove localStorage, hardcode INR:

```tsx
import React, { createContext, useContext } from 'react';

interface CurrencyContextType {
  formatCurrency: (value: number | null | undefined) => string;
  currencySymbol: string;
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

export const CurrencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const currencySymbol = '₹';

  const formatCurrency = (value: number | null | undefined) => {
    const val = value ?? 0;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(val);
  };

  return (
    <CurrencyContext.Provider value={{ formatCurrency, currencySymbol }}>
      {children}
    </CurrencyContext.Provider>
  );
};

export const useCurrency = () => {
  const context = useContext(CurrencyContext);
  if (context === undefined) {
    throw new Error('useCurrency must be used within a CurrencyProvider');
  }
  return context;
};
```

**Modify:** `frontend/src/components/layout/Sidebar.tsx`

- Remove `import { useCurrency } from '../../context/CurrencyContext';`
- Remove the `const { currency, setCurrency } = useCurrency();` line
- Remove the entire currency toggle `<div>` block (lines 42-67)
- Keep the version number div

**Modify:** `frontend/src/pages/Dashboard.tsx`

- Remove `currency` from the `useCurrency()` destructure (keep `formatCurrency` and `currencySymbol`)
- Remove the conditional `currency === 'INR' ? IndianRupee : DollarSign` — always use `IndianRupee`
- Remove `DollarSign` from the lucide imports

**Modify:** `frontend/src/pages/Insights.tsx`

- Remove `usd_inr_rate` from the destructured `data` object
- Remove the entire `convert()` function
- Replace all `convert(h.market_value_native, h.currency)` with just `h.market_value_native`
- Replace all `convert(h.unrealized_pnl_native, h.currency)` with just `h.unrealized_pnl_native`
- Replace all `convert(c.cash_balance_native, c.currency)` with just `c.cash_balance_native`
- Replace all `convert(c.stock_value_native, c.currency)` with just `c.stock_value_native`
- Replace all `convert(h.fifty_two_week_low, h.currency)` with just `h.fifty_two_week_low`
- Replace all `convert(h.fifty_two_week_high, h.currency)` with just `h.fifty_two_week_high`

**Modify:** `frontend/src/types/index.ts`

- Remove `usd_inr_rate` from `PortfolioInsights` interface

**Modify:** `frontend/src/pages/Transactions.tsx`

- Remove the currency selector dropdown from the new account inline form (the `<select>` with USD/INR options)
- When creating an account, always pass `currency: 'INR'`
- Remove `currencySymbol` from form labels — hardcode `₹` or use `useCurrency().currencySymbol`
- Remove the inline currency formatting in the account select dropdown (`en-IN` / `en-US` branching) — always use `en-IN` with INR

---

#### Task 9: Decompose Insights.tsx into components

**New file:** `frontend/src/components/charts/AllocationDonutChart.tsx`

```tsx
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { useCurrency } from '../../context/CurrencyContext';

interface AllocationItem {
  name: string;
  value: number;
  percentage: number;
  color?: string;
}

interface Props {
  title: string;
  subtitle: string;
  data: AllocationItem[];
  colors: string[];
  colorOffset?: number;
  maxLegendItems?: number;
}

export default function AllocationDonutChart({
  title, subtitle, data, colors, colorOffset = 0, maxLegendItems = 4,
}: Props) {
  const { formatCurrency } = useCurrency();

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl shadow-lg backdrop-blur-md">
          <p className="text-xs font-semibold text-slate-400">{d.name}</p>
          <p className="text-sm font-bold text-white mt-1">Value: {formatCurrency(d.value)}</p>
          <p className="text-xs font-semibold text-emerald-400">Share: {d.percentage.toFixed(2)}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md flex flex-col justify-between h-[360px]">
      <div>
        <h2 className="text-base font-bold text-white">{title}</h2>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>
      <div className="h-48 my-2 relative">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} cx="50%" cy="50%" innerRadius={50} outerRadius={70} paddingAngle={2} dataKey="value">
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={colors[(index + colorOffset) % colors.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-slate-500 text-xs">No data available</div>
        )}
      </div>
      <div className="text-xs text-slate-400 flex items-center justify-center gap-1.5 flex-wrap overflow-y-auto max-h-12">
        {data.slice(0, maxLegendItems).map((d, index) => (
          <span key={d.name} className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: colors[(index + colorOffset) % colors.length] }} />
            <span>{d.name} ({d.percentage.toFixed(0)}%)</span>
          </span>
        ))}
        {data.length > maxLegendItems && <span>+ {data.length - maxLegendItems} more</span>}
      </div>
    </div>
  );
}
```

**Then in `Insights.tsx`**, replace each of the 6 pie chart blocks with:
```tsx
<AllocationDonutChart title="Sector Allocation" subtitle="Breakdown by industry sector" data={sectorData} colors={COLORS} />
<AllocationDonutChart title="Asset Class" subtitle="Distribution across asset classes & cash" data={typeData} colors={COLORS} colorOffset={2} />
<AllocationDonutChart title="Geographic" subtitle="Exposures by listing country" data={countryData} colors={COLORS} colorOffset={4} />
<AllocationDonutChart title="Currency" subtitle="Valuation by native currency" data={currencyData} colors={COLORS} colorOffset={1} />
<AllocationDonutChart title="Account" subtitle="Value per brokerage account" data={accountData} colors={COLORS} colorOffset={3} />
```

The Risk Composition chart keeps its custom colors, so it uses the component with the `color` field on each data item — or stays inline (it's a single instance, not copy-pasted).

---

#### Task 10: Update backend tests

**Files to update:**
- `backend/tests/test_fifo_engine.py` → **Rename** to `backend/tests/test_holdings_service.py`
  - Replace all FIFO lot assertions with Holding assertions
  - Test `apply_buy` creates/updates holding correctly
  - Test `apply_sell` computes WAC realized P&L correctly
  - Test sell with insufficient shares raises ValueError
  - Test multiple buys at different prices → correct weighted average
  - Test buy-sell-buy-sell sequence → correct running P&L

- `backend/tests/test_api.py`
  - Replace all assertions checking FIFOLot/LotClosure with Holding checks
  - Update imports from `fifo_engine` to `transaction_service`

- `backend/tests/test_portfolio.py`
  - Replace lot-based setup with holding-based setup
  - Verify portfolio summary reads from Holding model
  - Remove any `usd_inr_rate` assertions from insights tests

- `backend/tests/conftest.py` — no changes expected (session fixture is model-agnostic)

**Specific WAC test cases for `test_holdings_service.py`:**

```python
def test_buy_creates_holding():
    # BUY 100 shares @ ₹50 → holding: shares=100, cost=5000, avg=50

def test_multiple_buys_weighted_average():
    # BUY 100 @ ₹50 (cost=5000), BUY 100 @ ₹60 (cost=6000)
    # → holding: shares=200, cost=11000, avg=55

def test_sell_uses_weighted_average():
    # BUY 100 @ ₹50, BUY 100 @ ₹60 → avg=55
    # SELL 50 @ ₹70 → realized = (70-55)*50 = ₹750
    # → holding: shares=150, cost=8250, realized=750

def test_sell_all_shares():
    # BUY 100 @ ₹50, SELL 100 @ ₹60
    # → holding: shares=0, cost=0, realized=1000

def test_sell_insufficient_shares():
    # BUY 10 @ ₹50, SELL 20 → ValueError

def test_sell_then_rebuy():
    # BUY 100 @ ₹50, SELL 100 @ ₹60, BUY 50 @ ₹70
    # → holding: shares=50, cost=3500, realized=1000
```

---

#### Task 11: Frontend build verification

Run and verify:
```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npm run lint
```

Fix any type errors caused by:
- Removed `usd_inr_rate` from `PortfolioInsights` type
- Removed `currency` / `setCurrency` from `useCurrency()` hook
- Changed import paths

---

### Database Changes

| Change | Type | Details |
|--------|------|---------|
| Add `Holding` table | New table | `id`, `account_id`, `asset_id`, `total_shares`, `total_cost`, `realized_pnl`, timestamps |
| Stop using `FIFOLot` | Soft removal | Table stays in DB, code stops referencing it |
| Stop using `LotClosure` | Soft removal | Table stays in DB, code stops referencing it |
| `Account.currency` default | Change default | `'USD'` → `'INR'` |
| Auto-migration on startup | Logic | If `Holding` table is empty and transactions exist, replay all transactions to populate holdings |

## Edge Cases

- **Existing database with FIFO data:** On first startup, the `Holding` table will be created empty. The auto-migration detects transactions exist but no holdings → replays all transactions to build WAC holdings. FIFO tables are left untouched (harmless).
- **Floating-point cleanup:** After selling all shares, `total_shares` and `total_cost` are explicitly zeroed to avoid `1e-15` residuals.
- **Sell more than held:** ValueError with clear message showing attempted vs available shares.
- **Division by zero:** `avg_cost = total_cost / total_shares` guarded by `if total_shares > 0`.
- **Account with USD currency in DB:** Stays as-is in the DB row. The frontend just won't display any currency picker. If user creates a new account, it defaults to INR.

## Testing Strategy

### Backend
- Run `python -m pytest -v` after all changes
- All existing test_api.py tests pass (with updated assertions)
- All existing test_portfolio.py tests pass (with updated model references)
- New test_holdings_service.py covers WAC math comprehensively

### Frontend
- `npm run build` passes
- `npx tsc --noEmit` passes
- Manual verification:
  - Sidebar has no currency toggle
  - All pages show ₹ with Indian numbering (lakhs/crores)
  - Dashboard, Holdings, Insights render correctly
  - Insights page loads faster (no USDINR=X fetch)

## Files to Modify

- `backend/app/models.py` — remove FIFOLot/LotClosure, add Holding, change Account.currency default
- `backend/app/schemas.py` — remove usd_inr_rate from PortfolioInsights, change AccountCreate default
- `backend/app/database.py` — add Holding auto-migration on startup
- `backend/app/routers/transactions.py` — change imports to transaction_service
- `backend/app/services/portfolio.py` — read from Holding, remove get_usd_inr_rate, remove usd_inr_rate from insights
- `backend/app/main.py` — no changes (router registration stays the same)
- `backend/tests/test_api.py` — update assertions for Holding model
- `backend/tests/test_portfolio.py` — update for Holding model, remove usd_inr_rate
- `frontend/src/context/CurrencyContext.tsx` — hardcode INR, remove toggle
- `frontend/src/components/layout/Sidebar.tsx` — remove currency toggle UI
- `frontend/src/pages/Dashboard.tsx` — remove USD icon logic
- `frontend/src/pages/Insights.tsx` — remove convert(), use chart component, remove usd_inr_rate
- `frontend/src/pages/Transactions.tsx` — remove currency selector from account creation
- `frontend/src/types/index.ts` — remove usd_inr_rate from PortfolioInsights

## New Files

- `backend/app/services/holdings_service.py` — WAC buy/sell logic
- `backend/app/services/transaction_service.py` — transaction processing orchestrator
- `backend/tests/test_holdings_service.py` — WAC unit tests
- `frontend/src/components/charts/AllocationDonutChart.tsx` — reusable donut chart

## Files to Delete

- `backend/app/services/fifo_engine.py` — replaced entirely by holdings_service + transaction_service
- `backend/tests/test_fifo_engine.py` — replaced by test_holdings_service.py
