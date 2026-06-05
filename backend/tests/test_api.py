import pytest
import time
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch
import pandas as pd
from fastapi.testclient import TestClient

from app.models import TxType


# ─── 6.1 — API Integration Tests ──────────────────────────────────────────────

def test_full_trade_lifecycle(client):
    # 1. Create account
    acc_resp = client.post("/api/v1/accounts", json={"name": "Lifecycle Account"})
    assert acc_resp.status_code == 201
    account_id = acc_resp.json()["id"]

    # 2. Create asset
    asset_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    assert asset_resp.status_code == 201
    asset_id = asset_resp.json()["id"]

    # 3. Deposit
    dep_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 10000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    assert dep_resp.status_code == 201

    # 4. Buy 10 AAPL @ 150.00
    buy1_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "BUY",
        "quantity": 10.0,
        "price_per_unit": 150.0,
        "executed_at": "2026-06-02T10:00:00Z"
    })
    assert buy1_resp.status_code == 201

    # 5. Buy 5 AAPL @ 160.00
    buy2_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "BUY",
        "quantity": 5.0,
        "price_per_unit": 160.0,
        "executed_at": "2026-06-03T10:00:00Z"
    })
    assert buy2_resp.status_code == 201

    # 6. Sell 12 AAPL @ 170.00
    sell_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "SELL",
        "quantity": 12.0,
        "price_per_unit": 170.0,
        "executed_at": "2026-06-04T10:00:00Z"
    })
    assert sell_resp.status_code == 201

    # 7. Verify stats
    with patch("app.services.price_service.get_current_prices") as mock_prices:
        mock_prices.return_value = {"AAPL": 170.0}
        
        summary_resp = client.get("/api/v1/portfolio/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        
        # Expected remaining: 3 shares of Lot 2 (cost = 160, current = 170)
        # Total invested = 3 * 160 = 480.00
        # Total market value = 3 * 170 = 510.00
        # Cash: 10000 - 1500 - 800 + 2040 = 9740.00
        # Net portfolio value: 510 + 9740 = 10250.00
        # Realized PNL:
        # Lot 1 (10 shares): cost 150, sell 170 -> PNL = 10 * 20 = 200
        # Lot 2 (2 shares closed): cost 160, sell 170 -> PNL = 2 * 10 = 20
        # Total realized PNL = 220
        # Unrealized PNL: 3 * (170 - 160) = 30
        
        assert summary["total_invested"] == 480.00
        assert summary["total_market_value"] == 510.00
        assert summary["total_cash"] == 9740.00
        assert summary["total_realized_pnl"] == 220.00
        assert summary["total_unrealized_pnl"] == 30.00
        assert summary["net_portfolio_value"] == 10250.00
        
        assert len(summary["holdings"]) == 1
        h = summary["holdings"][0]
        assert h["ticker"] == "AAPL"
        assert h["total_shares"] == 3.0
        assert h["avg_cost_basis"] == 160.0
        assert h["current_price"] == 170.0
        assert h["market_value"] == 510.0
        assert h["unrealized_pnl"] == 30.0
        assert h["realized_pnl"] == 220.0


def test_delete_transaction_replays(client):
    # Create account
    acc_resp = client.post("/api/v1/accounts", json={"name": "Replay Account"})
    account_id = acc_resp.json()["id"]

    # Create asset
    asset_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple Inc."})
    asset_id = asset_resp.json()["id"]

    # Create 5 transactions
    # 1. Deposit
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 10000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    
    # 2. Buy 10 AAPL @ 150
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "BUY",
        "quantity": 10.0,
        "price_per_unit": 150.0,
        "executed_at": "2026-06-02T10:00:00Z"
    })
    
    # 3. Buy 5 AAPL @ 160 (The middle transaction to delete)
    t3_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "BUY",
        "quantity": 5.0,
        "price_per_unit": 160.0,
        "executed_at": "2026-06-03T10:00:00Z"
    })
    t3_id = t3_resp.json()["id"]
    
    # 4. Sell 3 AAPL @ 170
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "SELL",
        "quantity": 3.0,
        "price_per_unit": 170.0,
        "executed_at": "2026-06-04T10:00:00Z"
    })
    
    # 5. Fee
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "FEE",
        "total_amount": 50.0,
        "executed_at": "2026-06-05T10:00:00Z"
    })

    # Assert cash before deletion
    acc_check = client.get(f"/api/v1/accounts/{account_id}")
    # 10000 - 1500 - 800 + 510 - 50 = 8160.0
    assert acc_check.json()["cash_balance"] == 8160.0

    # Delete the middle transaction (t3: Buy 5 AAPL @ 160)
    del_resp = client.delete(f"/api/v1/transactions/{t3_id}")
    assert del_resp.status_code == 204

    # Verify cash/lots are correctly recalculated.
    # Recalculated cash: 10000 - 1500 (buy 10 AAPL) + 510 (sell 3 AAPL) - 50 (fee) = 8960.0
    acc_check_post = client.get(f"/api/v1/accounts/{account_id}")
    assert acc_check_post.json()["cash_balance"] == 8960.0

    # Verify holdings
    with patch("app.services.price_service.get_current_prices") as mock_prices:
        mock_prices.return_value = {"AAPL": 170.0}
        summary = client.get("/api/v1/portfolio/summary").json()
        
        # Remaining: 10 - 3 = 7 shares of Lot 1 (cost 150, current 170)
        # Total invested: 7 * 150 = 1050.00
        # Total realized PNL: 3 * (170 - 150) = 60.0
        # Total unrealized PNL: 7 * (170 - 150) = 140.0
        assert summary["total_invested"] == 1050.00
        assert summary["total_cash"] == 8960.0
        assert summary["total_realized_pnl"] == 60.0
        assert summary["total_unrealized_pnl"] == 140.0
        assert len(summary["holdings"]) == 1
        assert summary["holdings"][0]["total_shares"] == 7.0
        assert summary["holdings"][0]["avg_cost_basis"] == 150.0


@patch("app.services.price_service.build_price_matrix")
def test_portfolio_history_data_integrity(mock_build_matrix, client):
    acc_resp = client.post("/api/v1/accounts", json={"name": "History Account"})
    account_id = acc_resp.json()["id"]

    asset1_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple"})
    asset1_id = asset1_resp.json()["id"]

    asset2_resp = client.post("/api/v1/assets", json={"ticker": "MSFT", "name": "Microsoft"})
    asset2_id = asset2_resp.json()["id"]

    # Let's align dates relative to today:
    end_date = datetime.now(timezone.utc).date()
    
    # Day 1: Deposit $1000 cash (5 days ago)
    d1 = end_date - timedelta(days=5)
    d1_str = datetime.combine(d1, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 1000.0,
        "executed_at": d1_str
    })

    # Day 3: Buy 2 AAPL @ 100 (3 days ago)
    d3 = end_date - timedelta(days=3)
    d3_str = datetime.combine(d3, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset1_id,
        "tx_type": "BUY",
        "quantity": 2.0,
        "price_per_unit": 100.0,
        "executed_at": d3_str
    })

    # Day 5: Buy 1 MSFT @ 200 (1 day ago)
    d5 = end_date - timedelta(days=1)
    d5_str = datetime.combine(d5, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset2_id,
        "tx_type": "BUY",
        "quantity": 1.0,
        "price_per_unit": 200.0,
        "executed_at": d5_str
    })

    # Mock build_price_matrix for AAPL and MSFT for the past 30 days
    # Return 120.0 for AAPL and 250.0 for MSFT
    mock_dates = [end_date - timedelta(days=i) for i in range(31)]
    mock_build_matrix.return_value = {
        "AAPL": {d: 120.0 for d in mock_dates},
        "MSFT": {d: 250.0 for d in mock_dates}
    }

    history_resp = client.get("/api/v1/portfolio/history?period=1M")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["period"] == "1M"
    assert len(history["data_points"]) == 31

    # Assert calculations of value per day
    # Day 1 (5 days ago): cash=1000, portfolio=0, total=1000
    dp5 = next(dp for dp in history["data_points"] if dp["date"] == d1.isoformat())
    assert dp5["cash_balance"] == 1000.0
    assert dp5["portfolio_value"] == 0.0
    assert dp5["total_value"] == 1000.0

    # Day 3 (3 days ago): cash=800, portfolio=2*120=240, total=1040
    dp3 = next(dp for dp in history["data_points"] if dp["date"] == d3.isoformat())
    assert dp3["cash_balance"] == 800.0
    assert dp3["portfolio_value"] == 240.0
    assert dp3["total_value"] == 1040.0

    # Day 5 (1 day ago): cash=600, portfolio=2*120 + 1*250 = 490, total=1090
    dp1 = next(dp for dp in history["data_points"] if dp["date"] == d5.isoformat())
    assert dp1["cash_balance"] == 600.0
    assert dp1["portfolio_value"] == 490.0
    assert dp1["total_value"] == 1090.0


def test_sell_more_than_owned(client):
    # Create account
    acc_resp = client.post("/api/v1/accounts", json={"name": "Sell Insufficient Account"})
    account_id = acc_resp.json()["id"]

    # Create asset
    asset_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple"})
    asset_id = asset_resp.json()["id"]

    # Deposit
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 10000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })

    # Sell 5 AAPL without owning any
    sell_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "SELL",
        "quantity": 5.0,
        "price_per_unit": 150.0,
        "executed_at": "2026-06-02T10:00:00Z"
    })
    assert sell_resp.status_code == 400
    assert "Insufficient shares" in sell_resp.json()["detail"]


def test_withdraw_more_than_cash(client):
    # Create account
    acc_resp = client.post("/api/v1/accounts", json={"name": "Withdraw Account"})
    account_id = acc_resp.json()["id"]

    # Withdraw more than cash (cash is 0)
    withdraw_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "WITHDRAWAL",
        "total_amount": 100.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    assert withdraw_resp.status_code == 400
    assert "Insufficient cash" in withdraw_resp.json()["detail"]


def test_delete_account_with_transactions(client):
    # Create account
    acc_resp = client.post("/api/v1/accounts", json={"name": "Delete Account With Tx"})
    account_id = acc_resp.json()["id"]

    # Deposit (associated transaction)
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 1000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })

    # Try to delete account
    del_resp = client.delete(f"/api/v1/accounts/{account_id}")
    assert del_resp.status_code == 409
    assert "Cannot delete account with existing transactions" in del_resp.json()["detail"]


# ─── 6.2 — Deterministic Scenario Test (FIFO Math Correctness) ────────────────

def test_deterministic_scenario_fifo_math(client):
    # Create account
    acc_resp = client.post("/api/v1/accounts", json={"name": "FIFO Math Account"})
    account_id = acc_resp.json()["id"]

    # Create assets AAPL and GOOGL
    aapl_resp = client.post("/api/v1/assets", json={"ticker": "AAPL", "name": "Apple"})
    aapl_id = aapl_resp.json()["id"]

    googl_resp = client.post("/api/v1/assets", json={"ticker": "GOOGL", "name": "Google"})
    googl_id = googl_resp.json()["id"]

    # Sequence:
    # Day 1: DEPOSIT $50,000.00
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 50000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })

    # Day 2: BUY 100 AAPL @ $150.00 (Total cost: $15,000.00) -> Lot A (100 @ 150)
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": aapl_id,
        "tx_type": "BUY",
        "quantity": 100.0,
        "price_per_unit": 150.0,
        "executed_at": "2026-06-02T10:00:00Z"
    })

    # Day 5: BUY 50 AAPL @ $160.00 (Total cost: $8,000.00) -> Lot B (50 @ 160)
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": aapl_id,
        "tx_type": "BUY",
        "quantity": 50.0,
        "price_per_unit": 160.0,
        "executed_at": "2026-06-05T10:00:00Z"
    })

    # Day 10: BUY 75 GOOGL @ $140.00 (Total cost: $10,500.00) -> Lot C (75 @ 140)
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": googl_id,
        "tx_type": "BUY",
        "quantity": 75.0,
        "price_per_unit": 140.0,
        "executed_at": "2026-06-10T10:00:00Z"
    })

    # Day 15: SELL 120 AAPL @ $170.00 (Total proceeds: $20,400.00)
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": aapl_id,
        "tx_type": "SELL",
        "quantity": 120.0,
        "price_per_unit": 170.0,
        "executed_at": "2026-06-15T10:00:00Z"
    })

    # Day 20: FEE $50.00
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "FEE",
        "total_amount": 50.0,
        "executed_at": "2026-06-20T10:00:00Z"
    })

    # Assert cash balance = 36,850.00
    acc_check = client.get(f"/api/v1/accounts/{account_id}")
    assert acc_check.status_code == 200
    assert acc_check.json()["cash_balance"] == 36850.00

    # Assert summary stats with custom mock prices
    # e.g. Current prices: AAPL = 175.0, GOOGL = 145.0
    with patch("app.services.price_service.get_current_prices") as mock_prices:
        mock_prices.return_value = {"AAPL": 175.0, "GOOGL": 145.0}

        summary_resp = client.get("/api/v1/portfolio/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()

        # Expected:
        # AAPL: 30 shares remaining (avg_cost_basis = 160.0), market_value = 30 * 175 = 5250.0
        # GOOGL: 75 shares remaining (avg_cost_basis = 140.0), market_value = 75 * 145 = 10875.0
        # Realized PNL: 2200.0
        # Total cash: 36850.0
        
        assert summary["total_cash"] == 36850.0
        assert summary["total_realized_pnl"] == 2200.0

        holdings = summary["holdings"]
        assert len(holdings) == 2

        aapl_h = next(h for h in holdings if h["ticker"] == "AAPL")
        googl_h = next(h for h in holdings if h["ticker"] == "GOOGL")

        assert aapl_h["total_shares"] == 30.0
        assert aapl_h["avg_cost_basis"] == 160.0
        assert aapl_h["current_price"] == 175.0
        assert aapl_h["market_value"] == 5250.0
        assert aapl_h["realized_pnl"] == 2200.0

        assert googl_h["total_shares"] == 75.0
        assert googl_h["avg_cost_basis"] == 140.0
        assert googl_h["current_price"] == 145.0
        assert googl_h["market_value"] == 10875.0
        assert googl_h["realized_pnl"] == 0.0


# ─── 6.3 — Performance Sanity Check ───────────────────────────────────────────

def test_performance_sanity_check(client):
    # 1. Create account
    acc_resp = client.post("/api/v1/accounts", json={"name": "Perf Account"})
    account_id = acc_resp.json()["id"]

    # 2. Create 5 assets
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    asset_ids = {}
    for ticker in tickers:
        asset_resp = client.post("/api/v1/assets", json={"ticker": ticker, "name": f"{ticker} Inc."})
        asset_ids[ticker] = asset_resp.json()["id"]

    # 3. Deposit money
    client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 1000000.0,
        "executed_at": "2025-06-01T10:00:00Z"
    })

    # 4. Generate 105 transactions (21 for each of the 5 tickers)
    # Spanning across multiple days
    # Say starting from 100 days ago to today
    base_date = datetime.now(timezone.utc) - timedelta(days=100)
    for i in range(105):
        ticker = tickers[i % 5]
        # Alternate between BUY and SELL, ensuring we always have shares to sell
        # Buy on even steps, Sell on odd steps (but only if we already bought some shares)
        # E.g. Buy 10, then Sell 2.
        tx_type = "BUY" if (i // 5) % 2 == 0 else "SELL"
        qty = 10.0 if tx_type == "BUY" else 2.0
        price = 150.0 + (i % 10)
        
        tx_date = base_date + timedelta(days=i)
        tx_date_str = tx_date.isoformat()
        
        client.post("/api/v1/transactions", json={
            "account_id": account_id,
            "asset_id": asset_ids[ticker],
            "tx_type": tx_type,
            "quantity": qty,
            "price_per_unit": price,
            "executed_at": tx_date_str
        })

    # 5. Benchmark endpoints:
    # - /portfolio/summary must resolve in < 2 seconds.
    # For /portfolio/summary, we mock get_current_prices
    with patch("app.services.price_service.get_current_prices") as mock_prices:
        mock_prices.return_value = {t: 200.0 for t in tickers}
        
        start_time = time.time()
        summary_resp = client.get("/api/v1/portfolio/summary")
        end_time = time.time()
        
        duration = end_time - start_time
        assert summary_resp.status_code == 200
        assert duration < 2.0

    # - /portfolio/history?period=1Y must resolve in < 5 seconds on initial load,
    #   and < 500ms on subsequent requests (validates SQLite price caching).
    #
    # To simulate the actual build_price_matrix caching mechanism without real network,
    # we patch yfinance.download.
    # Let's create a DataFrame with daily dates covering 1 year to today
    hist_end_date = datetime.now(timezone.utc).date()
    hist_start_date = hist_end_date - timedelta(days=365)
    all_dates = pd.date_range(start=hist_start_date, end=hist_end_date, freq="D")
    dummy_df = pd.DataFrame(index=all_dates, data={"Close": [150.0] * len(all_dates)})
    
    with patch("yfinance.download") as mock_download:
        mock_download.return_value = dummy_df
        
        # Initial load: Cache is empty for the 5 tickers. It should fetch and cache them.
        start_time_initial = time.time()
        history_resp_1 = client.get("/api/v1/portfolio/history?period=1Y")
        end_time_initial = time.time()
        
        duration_initial = end_time_initial - start_time_initial
        assert history_resp_1.status_code == 200
        assert duration_initial < 5.0
        
        # Assert that yfinance.download was called at least once
        assert mock_download.call_count > 0
        
        # Reset mock call count to verify no more downloads happen
        mock_download.reset_mock()
        
        # Subsequent load: All dates should be in PriceCache, so yfinance.download should NOT be called.
        start_time_cached = time.time()
        history_resp_2 = client.get("/api/v1/portfolio/history?period=1Y")
        end_time_cached = time.time()
        
        duration_cached = end_time_cached - start_time_cached
        assert history_resp_2.status_code == 200
        assert duration_cached < 0.5
        
        # Assert that yfinance.download was NEVER called during the subsequent cached request
        mock_download.assert_not_called()
