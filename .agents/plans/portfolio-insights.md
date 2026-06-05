---
name: Portfolio Insights
status: Approved
priority: high
created: 2026-06-05
updated: 2026-06-05
progress:
  - "[x] Task 1: Create AssetMetadata model and run DB migration"
  - "[x] Task 2: Implement yfinance metadata crawler and caching service"
  - "[x] Task 3: Add currency field to Account model and migration helper"
  - "[x] Task 4: Create Portfolio Insights endpoint and schemas"
  - "[x] Task 5: Implement unit tests for backend insights endpoint"
  - "[x] Task 6: Add Insights route and navigation link in sidebar"
  - "[x] Task 7: Create Insights page component with metrics and charts"
  - "[x] Task 8: Implement Treemap Composition Heatmap"
  - "[x] Task 9: Validate E2E styling, responsiveness, and empty states"
---

# Feature: Portfolio Insights

## Summary
Introduce a comprehensive **Portfolio Insights** dashboard that provides deep financial analytics on a user's holdings. This includes asset allocations (by Sector, Country/Region, Security Type, Currency, and Account), risk composition (Beta profile), weighted valuation metrics (weighted Beta, P/E ratio, Dividend Yield, P/B ratio), 52-week high/low relative ranges, and an interactive **Treemap Composition Heatmap** color-coded by unrealized P&L. 

To power this, the backend will fetch and cache rich asset metadata from `yfinance` and support multi-currency account tracking (USD/INR) with automatic exchange rate conversion using `USDINR=X`.

## Motivation
While the existing dashboard shows overall portfolio values and historical trends, serious investors need detailed classification and risk analytics to maintain a balanced allocation. Specifically:
- **Diversification Tracking**: Visualizing concentration risk across sectors, industries, countries, and asset classes.
- **Risk Profile**: Understanding market risk exposure through Beta weighting.
- **Valuation Context**: Tracking valuation metrics like P/E and P/B to assess if the portfolio is overvalued.
- **Multi-Currency Clarity**: Supporting accounts in different currencies (USD for US stocks, INR for Indian stocks) and normalizing them using real-time exchange rates.
- **Interactive Heatmaps**: Providing a high-fidelity Treemap representation of portfolio weights and performance, standard in premium investing platforms.

## Acceptance Criteria
1. **Database Schema & Migrations**:
   - Introduce an `AssetMetadata` table to cache `yfinance` details (sector, industry, country, quote type, beta, P/E, P/B, dividend yield, 52W range) for 24 hours.
   - Add a `currency` column to the `Account` table (defaults to `USD`, supports `USD` and `INR`).
   - Run automatic SQLite migration on startup to ensure existing databases receive the new column without data loss.

2. **Backend Services & API**:
   - Add a new endpoint `GET /api/v1/portfolio/insights` returning holdings metadata, account cash balances, and the current `USDINR=X` exchange rate.
   - Handle rate-limiting and metadata crawler exceptions gracefully, falling back to safe defaults (e.g. inferring currency from ticker suffixes like `.NS`).

3. **Frontend Navigation & Routing**:
   - Register a new page route at `/insights` and place an **Insights** link in the sidebar with a dynamic icon.
   - Support inline selection of currency when creating a new account on the transactions page.

4. **Portfolio Analytics & Calculations**:
   - Dynamically convert all assets and cash balances to the active display currency (`USD` or `INR`) using the backend-provided exchange rate.
   - Calculate portfolio-weighted metrics: Beta, P/E Ratio, Dividend Yield, and P/B Ratio.
   - Construct allocation groupings by Sector, Security Type, Region (Country), Currency, and Account.

5. **Visualizations**:
   - Render beautiful donut/pie charts for the allocation categories using React and Recharts.
   - Render a risk profile bar/gauge chart (Cash vs. Low Risk [Beta <= 0.8] vs. Medium Risk [0.8 to 1.2] vs. High Risk [Beta > 1.2]).
   - Display a list/table showing 52-Week High/Low progress bar ranges for individual holdings.
   - Render a custom SVG `<Treemap>` Composition Heatmap where box size represents market value and color represents unrealized P&L % (green for profits, red for losses).

6. **Error & Edge Cases**:
   - Gracefully handle empty portfolios (zero holdings/cash) with clean dashboard empty states instead of crashes.
   - Ensure the UI responds instantly to display currency toggle switches in the sidebar.

---

## Technical Design

### Backend

#### 1. Models & Database Changes (`backend/app/models.py`)
Add `AssetMetadata` model to cache ticker information and update `Account` model:
```python
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

class Account(SQLModel, table=True):
    # Existing fields
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    cash_balance: float = Field(default=0.0)
    # New field
    currency: str = Field(default="USD")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

#### 2. Schemas (`backend/app/schemas.py`)
Add insights and update account schemas:
```python
class AccountCreate(BaseModel):
    name: str
    currency: Optional[str] = "USD"

class AccountUpdate(BaseModel):
    name: str
    currency: Optional[str] = None

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

class PortfolioInsights(BaseModel):
    holdings: list[HoldingInsightDetail]
    cash_balances: list[CashInsightDetail]
    usd_inr_rate: float
```

#### 3. Automatic Database Migration (`backend/app/database.py`)
Modify `create_db_and_tables()` to run a safe SQLite migration:
```python
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    from sqlalchemy import text
    with engine.begin() as conn:
        try:
            conn.execute(text("SELECT currency FROM account LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE account ADD COLUMN currency VARCHAR DEFAULT 'USD'"))
            except Exception as e:
                print(f"Migration error: {e}")
```

#### 4. Metadata Crawling and Insights Service (`backend/app/services/portfolio.py`)
Add metadata fetcher and USDINR exchange rate resolver:
```python
def get_usd_inr_rate() -> float:
    try:
        ticker = yf.Ticker("USDINR=X")
        price = ticker.fast_info.get("lastPrice", None)
        if price is None:
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
        if price is not None:
            return float(price)
    except Exception:
        pass
    return 83.5 # Standard fallback

def fetch_and_cache_metadata(session: Session, asset: Asset) -> AssetMetadata:
    metadata = session.exec(select(AssetMetadata).where(AssetMetadata.asset_id == asset.id)).first()
    now = datetime.now(timezone.utc)
    if metadata and (now - metadata.fetched_at.replace(tzinfo=timezone.utc)).days < 1:
        return metadata

    try:
        ticker_obj = yf.Ticker(asset.ticker)
        info = ticker_obj.info
        
        quote_type = info.get("quoteType", "EQUITY")
        asset_class = "Equity"
        if quote_type == "ETF":
            asset_class = "ETF"
        elif quote_type == "MUTUALFUND":
            asset_class = "Mutual Fund"
        elif quote_type == "CRYPTOCURRENCY":
            asset_class = "Crypto"

        currency = info.get("currency")
        if not currency:
            currency = "INR" if (asset.ticker.endswith(".NS") or asset.ticker.endswith(".BO")) else "USD"

        long_name = info.get("longName", asset.name or asset.ticker)
        if not asset.name and long_name:
            asset.name = long_name
            session.add(asset)

        data = {
            "currency": currency,
            "asset_class": asset_class,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country") or ("India" if currency == "INR" else "United States"),
            "exchange": info.get("exchange"),
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
            "long_name": long_name,
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "trailing_pe": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "price_to_book": info.get("priceToBook"),
            "fetched_at": now
        }

        if not metadata:
            metadata = AssetMetadata(asset_id=asset.id, **data)
        else:
            for k, v in data.items():
                setattr(metadata, k, v)
        
        session.add(metadata)
        session.commit()
        session.refresh(metadata)
    except Exception:
        session.rollback()
        # Create minimal fallback to avoid failure loops
        if not metadata:
            currency = "INR" if (asset.ticker.endswith(".NS") or asset.ticker.endswith(".BO")) else "USD"
            metadata = AssetMetadata(
                asset_id=asset.id,
                currency=currency,
                asset_class="Equity",
                sector="Other",
                country="India" if currency == "INR" else "United States",
                long_name=asset.name or asset.ticker,
                fetched_at=now
            )
            session.add(metadata)
            session.commit()
            session.refresh(metadata)
    return metadata

def get_portfolio_insights(session: Session) -> PortfolioInsights:
    summary = get_portfolio_summary(session)
    usd_inr_rate = get_usd_inr_rate()
    
    # Pre-fetch and cache metadata for all active assets
    assets = session.exec(select(Asset)).all()
    asset_map = {a.ticker: a for a in assets}
    
    holdings_insights = []
    for h in summary.holdings:
        asset = asset_map.get(h.ticker)
        if asset:
            meta = fetch_and_cache_metadata(session, asset)
            holdings_insights.append(
                HoldingInsightDetail(
                    ticker=h.ticker,
                    asset_name=h.asset_name,
                    total_shares=h.total_shares,
                    market_value_native=h.market_value,  # holding.market_value is native in summary
                    currency=meta.currency,
                    asset_class=meta.asset_class,
                    sector=meta.sector,
                    industry=meta.industry,
                    country=meta.country,
                    exchange=meta.exchange,
                    beta=meta.beta,
                    market_cap=meta.market_cap,
                    fifty_two_week_high=meta.fifty_two_week_high,
                    fifty_two_week_low=meta.fifty_two_week_low,
                    trailing_pe=meta.trailing_pe,
                    dividend_yield=meta.dividend_yield,
                    price_to_book=meta.price_to_book,
                    unrealized_pnl_native=h.unrealized_pnl
                )
            )
            
    # Fetch accounts & cash
    accounts = session.exec(select(Account)).all()
    cash_details = [
        CashInsightDetail(
            account_id=acc.id,
            account_name=acc.name,
            cash_balance_native=acc.cash_balance,
            currency=acc.currency
        )
        for acc in accounts
    ]
    
    return PortfolioInsights(
        holdings=holdings_insights,
        cash_balances=cash_details,
        usd_inr_rate=usd_inr_rate
    )
```

#### 5. Router Endpoint (`backend/app/routers/portfolio.py`)
```python
from app.schemas import PortfolioInsights
from app.services.portfolio import get_portfolio_insights

@router.get("/insights", response_model=PortfolioInsights)
def read_portfolio_insights(session: Session = Depends(get_session)):
    return get_portfolio_insights(session)
```

---

### Frontend

#### 1. React Query Hook (`frontend/src/hooks/usePortfolio.ts`)
```typescript
export function usePortfolioInsights() {
  return useQuery<PortfolioInsights>({
    queryKey: ['portfolio', 'insights'],
    queryFn: async () => {
      const response = await api.get('/portfolio/insights');
      return response.data;
    },
  });
}
```

#### 2. Insights Page Layout (`frontend/src/pages/Insights.tsx`)
Create a modern, responsive analytical dashboard using CSS glassmorphism, high-contrast typography, and Recharts.

##### Calculations in UI:
- Normalization logic:
  ```typescript
  const convert = (val: number, from: string) => {
    if (from === currency) return val;
    return currency === 'USD' ? val / data.usd_inr_rate : val * data.usd_inr_rate;
  };
  ```
- **Portfolio-Weighted Metrics**:
  - `Weighted Beta` = $\sum(Beta \times MV) / \sum(MV)$ (calculated across equity/ETF holdings, cash as 0).
  - `Weighted P/E` = $\sum(PE \times MV) / \sum(MV)$ (calculated across equities with valid trailing P/E).
  - `Weighted Div Yield` = $\sum(Yield \times MV) / \sum(MV)$ (handling dividend yield as percentage or decimal correctly).
- **Groupings**:
  - Sector allocation: Sum(MV) grouped by `holding.sector || 'Other'`.
  - Country/Region: Sum(MV) grouped by `holding.country || 'Other'`.
  - Currency allocation: Group both holdings and cash by currency.
  - Security Type: Equity vs. ETF vs. Cash.
  - Account allocation: Cash + holding values grouped by account name.
- **Treemap Heatmap**:
  - Format data in a hierarchical format.
  - Use `ResponsiveContainer` and `<Treemap data={treemapData} dataKey="size">` with a custom content renderer to color boxes based on `unrealized_pnl_pct`.
  - Color gradient: deep red for losses <= -15%, transition to dark grey at 0%, up to deep green for gains >= 15%.

##### 52-Week Range Display:
- Display horizontal tracks showing where the current price sits relative to the 52-Week Low and 52-Week High:
  $$\text{Progress \%} = \frac{\text{Current} - \text{Low}}{\text{High} - \text{Low}} \times 100$$
- Renders as a sleek slider track showing `Low` on the left, `High` on the right, and a colored node at the current price position.

#### 3. Update Sidebar & Routing (`frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`)
- Import `BarChart3` (or `PieChart`) from `lucide-react`.
- Add the `Insights` tab pointing to `/insights`.
- Register the route in `App.tsx`.

#### 4. Support Account Currency in Forms (`frontend/src/pages/Transactions.tsx`)
- Add a dropdown for Currency (`USD` / `INR`) next to the account name input when creating a new account.
- Pass `currency` in the `createAccount.mutate` payload.
- Render account cash balances in the account select dropdown labeled with their corresponding currency symbol (e.g. `Main Account (₹2,50,000.00)` vs `US Brokerage ($12,450.00)`).

---

## Database Changes
No new tables outside of caching.
- New table `AssetMetadata`
- New column `currency` on `Account` table (defaults to `'USD'`)

---

## Edge Cases
- **Zero assets/cash**: Ensure math doesn't result in `NaN` or division by zero. Fall back to placeholder displays with call-to-action messages (e.g. "Add a transaction to see insights").
- **Asset without Beta/Sector**: Fall back to `"Other"` or `"Not Available"` sector and skip or assign 0 beta for cash/risk-free assets.
- **YFinance Offline**: The crawler handles network exceptions, saves default values, and prevents blocking user requests.
- **Multiple currencies in accounts**: Normalized to the active display currency chosen in the sidebar so all values sum correctly.

---

## Testing Strategy

### Backend
- **Metadata Cache Tests**: Write a test verifying that `fetch_and_cache_metadata` successfully caches ticker info and updates an asset's missing name.
- **Exchange Rate Test**: Mock `yfinance.Ticker` to verify `get_usd_inr_rate` falls back to `83.5` if offline, or returns the correct live float.
- **Insights Endpoint test**: Add unit tests in `tests/test_portfolio.py` validating the JSON structure of `/api/v1/portfolio/insights`.

### Frontend
- **Type Checking & Linting**: Run `npm run lint` and `npx tsc --noEmit` to verify type safety.
- **UI Verification**:
  - Verify toggling USD/INR switches currency symbols and converts values on the charts.
  - Verify that the Treemap renders cleanly and supports tooltips.
  - Verify account creation with custom currency saves and loads correctly.
