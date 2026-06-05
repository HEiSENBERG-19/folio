import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
from sqlmodel import Session, select

from app.models import Account, Asset, Transaction, Holding, PriceCache, TxType
from app.services.price_service import fetch_and_cache_prices, build_price_matrix
from app.services.portfolio import get_portfolio_summary, get_portfolio_history, get_portfolio_allocation


def create_base_entities(session: Session):
    account = Account(name="Groww", cash_balance=0.0)
    asset = Asset(ticker="AAPL", name="Apple Inc.")
    session.add(account)
    session.add(asset)
    session.commit()
    session.refresh(account)
    session.refresh(asset)
    return account, asset


@patch("yfinance.download")
def test_price_cache_stores_fetched_data(mock_download, session: Session):
    _, asset = create_base_entities(session)

    # Mock yfinance.download to return data for 2026-06-01
    mock_df = pd.DataFrame(
        index=pd.to_datetime([date(2026, 6, 1)]),
        data={"Close": [150.0]}
    )
    mock_download.return_value = mock_df

    fetch_and_cache_prices(session, "AAPL", date(2026, 6, 1), date(2026, 6, 1))

    # Verify database entry
    cached = session.exec(select(PriceCache).where(PriceCache.asset_id == asset.id)).all()
    assert len(cached) == 1
    assert cached[0].price_date == date(2026, 6, 1)
    assert cached[0].close_price == 150.0


@patch("yfinance.download")
def test_price_cache_avoids_refetch(mock_download, session: Session):
    _, asset = create_base_entities(session)

    # Manually seed cache
    seed_cache = PriceCache(
        asset_id=asset.id,
        price_date=date(2026, 6, 1),
        close_price=150.0
    )
    session.add(seed_cache)
    session.commit()

    # Call service
    fetch_and_cache_prices(session, "AAPL", date(2026, 6, 1), date(2026, 6, 1))

    # Verify download was never called because data is already in cache
    mock_download.assert_not_called()


@patch("yfinance.download")
def test_forward_fill_weekends(mock_download, session: Session):
    _, asset = create_base_entities(session)

    # Friday = 2026-06-05, Saturday = 2026-06-06, Sunday = 2026-06-07
    # Friday has price in cache, Saturday and Sunday are missing
    seed_cache = PriceCache(
        asset_id=asset.id,
        price_date=date(2026, 6, 5),
        close_price=150.0
    )
    session.add(seed_cache)
    session.commit()

    # Mock download to return empty to simulate no weekend data from yf
    mock_download.return_value = pd.DataFrame()

    # Get price matrix
    matrix = build_price_matrix(session, ["AAPL"], date(2026, 6, 5), date(2026, 6, 7))

    # Check that Friday, Saturday, Sunday are all filled with 150.0
    assert matrix["AAPL"][date(2026, 6, 5)] == 150.0
    assert matrix["AAPL"][date(2026, 6, 6)] == 150.0
    assert matrix["AAPL"][date(2026, 6, 7)] == 150.0


def test_portfolio_summary_empty(session: Session):
    summary = get_portfolio_summary(session)
    assert summary.total_invested == 0.0
    assert summary.total_market_value == 0.0
    assert summary.total_cash == 0.0
    assert summary.total_realized_pnl == 0.0
    assert summary.total_unrealized_pnl == 0.0
    assert summary.net_portfolio_value == 0.0
    assert len(summary.holdings) == 0


@patch("app.services.price_service.get_current_prices")
@patch("yfinance.download")
def test_unrealized_pnl_calculation(mock_download, mock_get_current_prices, session: Session):
    account, asset = create_base_entities(session)

    # 1. Deposit 2000 cash
    account.cash_balance = 2000.0
    session.add(account)

    # 2. Buy 10 AAPL at 150 (Day 1)
    tx = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx)
    session.flush()

    # Adjust cash balance and holding
    account.cash_balance -= 1500.0
    session.add(account)
    holding = Holding(
        account_id=account.id,
        asset_id=asset.id,
        total_shares=10.0,
        total_cost=1500.0,
        realized_pnl=0.0
    )
    session.add(holding)
    session.commit()

    # Mock current price of AAPL to be 170
    mock_get_current_prices.return_value = {"AAPL": 170.0}

    summary = get_portfolio_summary(session)

    assert summary.total_invested == 1500.0
    assert summary.total_market_value == 1700.0
    assert summary.total_cash == 500.0
    assert summary.total_realized_pnl == 0.0
    assert summary.total_unrealized_pnl == 200.0
    assert summary.net_portfolio_value == 2200.0
    
    assert len(summary.holdings) == 1
    h = summary.holdings[0]
    assert h.ticker == "AAPL"
    assert h.total_shares == 10.0
    assert h.avg_cost_basis == 150.0
    assert h.current_price == 170.0
    assert h.market_value == 1700.0
    assert h.unrealized_pnl == 200.0
    assert h.unrealized_pnl_pct == pytest.approx(13.333333333333334)
    assert h.realized_pnl == 0.0


@patch("app.services.price_service.build_price_matrix")
def test_portfolio_history_shape(mock_build_matrix, session: Session):
    account, asset = create_base_entities(session)

    # Day 1: Deposit 1000 cash (e.g. 5 days ago)
    end_date = datetime.now(timezone.utc).date()
    day1_datetime = datetime.combine(end_date - timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc)
    
    tx_dep = Transaction(
        account_id=account.id,
        tx_type=TxType.DEPOSIT,
        total_amount=1000.0,
        executed_at=day1_datetime
    )
    session.add(tx_dep)
    account.cash_balance += 1000.0
    session.add(account)

    # Day 3: Buy 2 AAPL at 100
    day3_datetime = datetime.combine(end_date - timedelta(days=3), datetime.min.time(), tzinfo=timezone.utc)
    tx_buy = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=2.0,
        price_per_unit=100.0,
        total_amount=200.0,
        executed_at=day3_datetime
    )
    session.add(tx_buy)
    session.flush()
    account.cash_balance -= 200.0
    session.add(account)


    holding = Holding(
        account_id=account.id,
        asset_id=asset.id,
        total_shares=2.0,
        total_cost=200.0,
        realized_pnl=0.0
    )
    session.add(holding)
    session.commit()

    # Mock price matrix for AAPL for the past 30 days
    # Return 120.0 for every date
    mock_dates = [end_date - timedelta(days=i) for i in range(31)]
    mock_build_matrix.return_value = {
        "AAPL": {d: 120.0 for d in mock_dates}
    }

    history = get_portfolio_history(session, "1M")

    # 1M period should return 31 data points (30 days ago to today inclusive)
    assert len(history.data_points) == 31
    assert history.period == "1M"

    # Verify shape and progression:
    # Before day 3: cash=1000, portfolio_value=0, total_value=1000
    # On and after day 3: cash=800, portfolio_value=2 * 120 = 240, total_value=1040
    
    # We can check specific dates:
    # day1 (5 days ago):
    d1 = end_date - timedelta(days=5)
    dp1 = next(dp for dp in history.data_points if dp.date == d1)
    assert dp1.cash_balance == 1000.0
    assert dp1.portfolio_value == 0.0
    assert dp1.total_value == 1000.0

    # day3 (3 days ago):
    d3 = end_date - timedelta(days=3)
    dp3 = next(dp for dp in history.data_points if dp.date == d3)
    assert dp3.cash_balance == 800.0
    assert dp3.portfolio_value == 240.0
    assert dp3.total_value == 1040.0


@patch("app.services.price_service.get_current_prices")
def test_portfolio_allocation(mock_get_prices, session: Session):
    account, asset = create_base_entities(session)
    asset2 = Asset(ticker="MSFT", name="Microsoft")
    session.add(asset2)
    
    account.cash_balance = 5000.0
    session.add(account)
    session.commit()

    # AAPL lot: cost 1500, current price 1700 (10 shares at 150/170)
    tx1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime.now(timezone.utc)
    )
    session.add(tx1)
    session.flush()
    holding1 = Holding(
        account_id=account.id,
        asset_id=asset.id,
        total_shares=10.0,
        total_cost=1500.0,
        realized_pnl=0.0
    )
    session.add(holding1)

    # MSFT lot: cost 2000, current price 3400 (10 shares at 200/340)
    tx2 = Transaction(
        account_id=account.id,
        asset_id=asset2.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=200.0,
        total_amount=2000.0,
        executed_at=datetime.now(timezone.utc)
    )
    session.add(tx2)
    session.flush()
    holding2 = Holding(
        account_id=account.id,
        asset_id=asset2.id,
        total_shares=10.0,
        total_cost=2000.0,
        realized_pnl=0.0
    )
    session.add(holding2)
    session.commit()

    mock_get_prices.return_value = {"AAPL": 170.0, "MSFT": 340.0}

    allocation = get_portfolio_allocation(session)

    # Total market value = 1700 + 3400 = 5100
    # AAPL percentage = 1700 / 5100 = 33.33%
    # MSFT percentage = 3400 / 5100 = 66.67%
    assert len(allocation) == 2
    aapl_slice = next(s for s in allocation if s.ticker == "AAPL")
    msft_slice = next(s for s in allocation if s.ticker == "MSFT")

    assert aapl_slice.market_value == 1700.0
    assert aapl_slice.percentage == pytest.approx(33.33333333333333)

    assert msft_slice.market_value == 3400.0
    assert msft_slice.percentage == pytest.approx(66.66666666666666)


# ─── API Router Tests ─────────────────────────────────────────────────────────

@patch("app.services.price_service.get_current_prices")
def test_api_portfolio_summary_and_allocation(mock_get_prices, client):
    # Setup database via API
    acc_resp = client.post("/api/v1/accounts", json={"name": "Portfolio Account"})
    account_id = acc_resp.json()["id"]

    asset_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    asset_id = asset_resp.json()["id"]

    # Deposit
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 5000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })

    # Buy
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "BUY",
        "quantity": 10.0,
        "price_per_unit": 150.0,
        "executed_at": "2026-06-02T10:00:00Z"
    })

    mock_get_prices.return_value = {"AAPL": 170.0}

    # Summary
    summary_resp = client.get("/api/v1/portfolio/summary")
    assert summary_resp.status_code == 200
    data = summary_resp.json()
    assert data["total_invested"] == 1500.0
    assert data["total_market_value"] == 1700.0
    assert data["total_cash"] == 3500.0
    assert data["net_portfolio_value"] == 5200.0
    assert len(data["holdings"]) == 1
    assert data["holdings"][0]["ticker"] == "AAPL"

    # Allocation
    allocation_resp = client.get("/api/v1/portfolio/allocation")
    assert allocation_resp.status_code == 200
    alloc_data = allocation_resp.json()
    assert len(alloc_data) == 1
    assert alloc_data[0]["ticker"] == "AAPL"
    assert alloc_data[0]["market_value"] == 1700.0
    assert alloc_data[0]["percentage"] == 100.0


@patch("app.services.price_service.build_price_matrix")
def test_api_portfolio_history(mock_build_matrix, client):
    acc_resp = client.post("/api/v1/accounts", json={"name": "History Account"})
    account_id = acc_resp.json()["id"]

    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 1000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })

    # Return empty price matrix since there are no stock holdings
    mock_build_matrix.return_value = {}

    resp = client.get("/api/v1/portfolio/history?period=1M")
    assert resp.status_code == 200
    history_data = resp.json()
    assert history_data["period"] == "1M"
    assert len(history_data["data_points"]) == 31
    assert history_data["data_points"][-1]["cash_balance"] == 1000.0
    assert history_data["data_points"][-1]["total_value"] == 1000.0

    # Test invalid period
    invalid_resp = client.get("/api/v1/portfolio/history?period=INVALID")
    assert invalid_resp.status_code == 400



@patch("yfinance.Ticker")
def test_fetch_and_cache_metadata(mock_ticker, session: Session):
    _, asset = create_base_entities(session)
    
    mock_instance = MagicMock()
    mock_instance.info = {
        "quoteType": "EQUITY",
        "currency": "USD",
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "exchange": "NMS",
        "beta": 1.2,
        "marketCap": 2500000000000,
        "fiftyTwoWeekHigh": 180.0,
        "fiftyTwoWeekLow": 130.0,
        "trailingPE": 28.5,
        "dividendYield": 0.005,
        "priceToBook": 40.0,
    }
    mock_ticker.return_value = mock_instance

    from app.services.portfolio import fetch_and_cache_metadata
    meta = fetch_and_cache_metadata(session, asset)
    assert meta.asset_id == asset.id
    assert meta.currency == "USD"
    assert meta.sector == "Technology"
    assert meta.beta == 1.2
    
    # Check that it's stored in db
    from app.models import AssetMetadata
    db_meta = session.exec(select(AssetMetadata).where(AssetMetadata.asset_id == asset.id)).first()
    assert db_meta is not None
    assert db_meta.sector == "Technology"


@patch("app.services.portfolio.fetch_and_cache_metadata")
@patch("app.services.price_service.get_current_prices")
def test_api_portfolio_insights(mock_get_current_prices, mock_fetch_meta, client, session: Session):
    # Setup account and asset
    acc_resp = client.post("/api/v1/accounts", json={"name": "Insights Account", "currency": "INR"})
    account_id = acc_resp.json()["id"]

    asset_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    asset_id = asset_resp.json()["id"]

    # Deposit INR cash
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 100000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })

    # Buy AAPL
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "BUY",
        "quantity": 5.0,
        "price_per_unit": 12000.0,
        "executed_at": "2026-06-02T10:00:00Z"
    })

    mock_get_current_prices.return_value = {"AAPL": 13000.0}
    
    from app.models import AssetMetadata
    mock_meta = AssetMetadata(
        asset_id=asset_id,
        currency="INR",
        asset_class="Equity",
        sector="Technology",
        country="India",
        beta=1.1,
        fifty_two_week_high=15000.0,
        fifty_two_week_low=10000.0,
        unrealized_pnl_native=5000.0
    )
    mock_fetch_meta.return_value = mock_meta

    resp = client.get("/api/v1/portfolio/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["holdings"]) == 1
    assert data["holdings"][0]["ticker"] == "AAPL"
    assert data["holdings"][0]["currency"] == "INR"
    assert data["holdings"][0]["sector"] == "Technology"
    assert data["holdings"][0]["beta"] == 1.1

    assert len(data["cash_balances"]) == 1
    assert data["cash_balances"][0]["account_name"] == "Insights Account"
    assert data["cash_balances"][0]["currency"] == "INR"
    assert data["cash_balances"][0]["cash_balance_native"] == 40000.0

