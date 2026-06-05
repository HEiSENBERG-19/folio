import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.models import Account, Asset, Transaction, Holding, TxType
from app.services.holdings_service import apply_buy, apply_sell
from app.services.transaction_service import process_transaction, replay_account_holdings


def create_base_data(session: Session):
    account = Account(name="Zerodha", cash_balance=0.0)
    asset = Asset(ticker="AAPL", name="Apple Inc.")
    session.add(account)
    session.add(asset)
    session.commit()
    session.refresh(account)
    session.refresh(asset)
    return account, asset


def test_deposit_increases_cash(session: Session):
    account, _ = create_base_data(session)
    tx = Transaction(
        account_id=account.id,
        tx_type=TxType.DEPOSIT,
        total_amount=10000.0,
        executed_at=datetime.now(timezone.utc)
    )
    session.add(tx)
    session.flush()

    process_transaction(session, tx)
    session.commit()

    session.refresh(account)
    assert account.cash_balance == 10000.0


def test_withdrawal_insufficient_cash(session: Session):
    account, _ = create_base_data(session)
    
    # 0 balance initially, withdraw 100 should fail
    tx = Transaction(
        account_id=account.id,
        tx_type=TxType.WITHDRAWAL,
        total_amount=100.0,
        executed_at=datetime.now(timezone.utc)
    )
    session.add(tx)
    session.flush()

    with pytest.raises(ValueError, match="Insufficient cash for withdrawal."):
        process_transaction(session, tx)


def test_fee_decreases_cash(session: Session):
    account, _ = create_base_data(session)
    account.cash_balance = 500.0
    session.add(account)
    session.commit()

    tx = Transaction(
        account_id=account.id,
        tx_type=TxType.FEE,
        total_amount=50.0,
        executed_at=datetime.now(timezone.utc)
    )
    session.add(tx)
    session.flush()

    process_transaction(session, tx)
    session.commit()

    session.refresh(account)
    assert account.cash_balance == 450.0


def test_buy_creates_holding(session: Session):
    # BUY 100 shares @ ₹50 -> holding: shares=100, cost=5000
    account, asset = create_base_data(session)
    account.cash_balance = 10000.0
    session.add(account)
    session.commit()

    tx = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=100.0,
        price_per_unit=50.0,
        total_amount=5000.0,
        executed_at=datetime.now(timezone.utc)
    )
    session.add(tx)
    session.flush()

    process_transaction(session, tx)
    session.commit()

    # Check cash decreased
    session.refresh(account)
    assert account.cash_balance == 5000.0

    # Check holding created
    holdings = session.exec(select(Holding).where(Holding.account_id == account.id)).all()
    assert len(holdings) == 1
    h = holdings[0]
    assert h.asset_id == asset.id
    assert h.total_shares == 100.0
    assert h.total_cost == 5000.0
    assert h.realized_pnl == 0.0


def test_multiple_buys_weighted_average(session: Session):
    # BUY 100 @ ₹50 (cost=5000), BUY 100 @ ₹60 (cost=6000)
    # -> holding: shares=200, cost=11000, avg=55
    account, asset = create_base_data(session)
    account.cash_balance = 20000.0
    session.add(account)
    session.commit()

    tx1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=100.0,
        price_per_unit=50.0,
        total_amount=5000.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    tx2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=100.0,
        price_per_unit=60.0,
        total_amount=6000.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx1)
    session.add(tx2)
    session.flush()

    process_transaction(session, tx1)
    process_transaction(session, tx2)
    session.commit()

    holding = session.exec(select(Holding).where(Holding.account_id == account.id).where(Holding.asset_id == asset.id)).one()
    assert holding.total_shares == 200.0
    assert holding.total_cost == 11000.0
    avg_cost = holding.total_cost / holding.total_shares
    assert avg_cost == 55.0


def test_sell_uses_weighted_average(session: Session):
    # BUY 100 @ ₹50, BUY 100 @ ₹60 -> avg=55
    # SELL 50 @ ₹70 -> realized = (70-55)*50 = ₹750
    # -> holding: shares=150, cost=8250, realized=750
    account, asset = create_base_data(session)
    account.cash_balance = 20000.0
    session.add(account)
    session.commit()

    tx1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=100.0,
        price_per_unit=50.0,
        total_amount=5000.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    tx2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=100.0,
        price_per_unit=60.0,
        total_amount=6000.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx1)
    session.add(tx2)
    session.flush()

    process_transaction(session, tx1)
    process_transaction(session, tx2)

    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=50.0,
        price_per_unit=70.0,
        total_amount=3500.0,
        executed_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()

    process_transaction(session, tx_sell)
    session.commit()

    holding = session.exec(select(Holding).where(Holding.account_id == account.id).where(Holding.asset_id == asset.id)).one()
    assert holding.total_shares == 150.0
    assert holding.total_cost == 8250.0
    assert holding.realized_pnl == 750.0


def test_sell_all_shares(session: Session):
    # BUY 100 @ ₹50, SELL 100 @ ₹60
    # -> holding: shares=0, cost=0, realized=1000
    account, asset = create_base_data(session)
    account.cash_balance = 10000.0
    session.add(account)
    session.commit()

    tx1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=100.0,
        price_per_unit=50.0,
        total_amount=5000.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx1)
    session.flush()
    process_transaction(session, tx1)

    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=100.0,
        price_per_unit=60.0,
        total_amount=6000.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    holding = session.exec(select(Holding).where(Holding.account_id == account.id).where(Holding.asset_id == asset.id)).one()
    assert holding.total_shares == 0.0
    assert holding.total_cost == 0.0
    assert holding.realized_pnl == 1000.0


def test_sell_insufficient_shares(session: Session):
    # BUY 10 @ ₹50, SELL 20 -> ValueError
    account, asset = create_base_data(session)
    account.cash_balance = 1000.0
    session.add(account)
    session.commit()

    tx1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=50.0,
        total_amount=500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx1)
    session.flush()
    process_transaction(session, tx1)

    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=20.0,
        price_per_unit=60.0,
        total_amount=1200.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()

    with pytest.raises(ValueError, match="Insufficient shares to sell."):
        process_transaction(session, tx_sell)


def test_sell_then_rebuy(session: Session):
    # BUY 100 @ ₹50, SELL 100 @ ₹60, BUY 50 @ ₹70
    # -> holding: shares=50, cost=3500, realized=1000
    account, asset = create_base_data(session)
    account.cash_balance = 10000.0
    session.add(account)
    session.commit()

    tx1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=100.0,
        price_per_unit=50.0,
        total_amount=5000.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx1)
    session.flush()
    process_transaction(session, tx1)

    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=100.0,
        price_per_unit=60.0,
        total_amount=6000.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)

    tx2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=50.0,
        price_per_unit=70.0,
        total_amount=3500.0,
        executed_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx2)
    session.flush()
    process_transaction(session, tx2)
    session.commit()

    holding = session.exec(select(Holding).where(Holding.account_id == account.id).where(Holding.asset_id == asset.id)).one()
    assert holding.total_shares == 50.0
    assert holding.total_cost == 3500.0
    assert holding.realized_pnl == 1000.0


def test_replay_account_holdings(session: Session):
    account, asset = create_base_data(session)

    # 1. Deposit 10000
    tx_dep = Transaction(
        account_id=account.id,
        tx_type=TxType.DEPOSIT,
        total_amount=10000.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_dep)
    session.flush()
    process_transaction(session, tx_dep)

    # 2. Buy 10 AAPL at 150
    tx_buy1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy1)
    session.flush()
    process_transaction(session, tx_buy1)

    # 3. Buy 10 AAPL at 160
    tx_buy2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=160.0,
        total_amount=1600.0,
        executed_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy2)
    session.flush()
    process_transaction(session, tx_buy2)

    # 4. Sell 5 AAPL at 170
    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=5.0,
        price_per_unit=170.0,
        total_amount=850.0,
        executed_at=datetime(2026, 6, 4, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    # Now verify initial state
    session.refresh(account)
    # Cash: 10000 - 1500 - 1600 + 850 = 7750
    assert account.cash_balance == 7750.0

    holding = session.exec(select(Holding).where(Holding.account_id == account.id).where(Holding.asset_id == asset.id)).one()
    # Average cost was (1500+1600)/20 = 155
    # Realized PNL: (170-155)*5 = 75
    # Remaining cost: 155*15 = 2325
    assert holding.total_shares == 15.0
    assert holding.total_cost == 2325.0
    assert holding.realized_pnl == 75.0

    # Delete the second BUY (tx_buy2)
    session.delete(tx_buy2)
    session.flush()

    # Run replay_account_holdings
    replay_account_holdings(session, account.id)
    session.commit()

    # Replayed state check:
    # Transactions left: Deposit 10000, Buy1 10 at 150, Sell 5 at 170.
    # Cash: 10000 - 1500 + 850 = 9350.
    session.refresh(account)
    assert account.cash_balance == 9350.0

    holding = session.exec(select(Holding).where(Holding.account_id == account.id).where(Holding.asset_id == asset.id)).one()
    # Average cost was 150
    # Realized PNL: (170-150)*5 = 100
    # Remaining cost: 150*5 = 750
    assert holding.total_shares == 5.0
    assert holding.total_cost == 750.0
    assert holding.realized_pnl == 100.0


# ─── API Router Tests ─────────────────────────────────────────────────────────

def test_api_list_transactions(client):
    acc_resp = client.post("/api/v1/accounts", json={"name": "API Account"})
    assert acc_resp.status_code == 201
    account_id = acc_resp.json()["id"]

    asset_resp = client.post("/api/v1/assets", json={"ticker": "MSFT", "name": "Microsoft"})
    assert asset_resp.status_code == 201
    asset_id = asset_resp.json()["id"]

    dep_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 1000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    assert dep_resp.status_code == 201

    buy_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": asset_id,
        "tx_type": "BUY",
        "quantity": 5.0,
        "price_per_unit": 100.0,
        "executed_at": "2026-06-02T10:00:00Z"
    })
    assert buy_resp.status_code == 201

    list_resp = client.get("/api/v1/transactions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    list_filtered = client.get(f"/api/v1/transactions?account_id={account_id}&tx_type=BUY")
    assert list_filtered.status_code == 200
    assert len(list_filtered.json()) == 1
    assert list_filtered.json()[0]["tx_type"] == "BUY"


def test_api_create_transaction_errors(client):
    acc_resp = client.post("/api/v1/accounts", json={"name": "API Account Error"})
    account_id = acc_resp.json()["id"]

    resp = client.post("/api/v1/transactions", json={
        "account_id": 9999,
        "tx_type": "DEPOSIT",
        "total_amount": 100.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    assert resp.status_code == 404

    resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "asset_id": 9999,
        "tx_type": "BUY",
        "quantity": 1.0,
        "price_per_unit": 100.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    assert resp.status_code == 404

    resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "WITHDRAWAL",
        "total_amount": 500.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Insufficient cash for withdrawal."


def test_api_get_delete_transaction(client):
    acc_resp = client.post("/api/v1/accounts", json={"name": "API Account Delete"})
    account_id = acc_resp.json()["id"]

    dep_resp = client.post("/api/v1/transactions", json={
        "account_id": account_id,
        "tx_type": "DEPOSIT",
        "total_amount": 1000.0,
        "executed_at": "2026-06-01T10:00:00Z"
    })
    tx_id = dep_resp.json()["id"]

    get_resp = client.get(f"/api/v1/transactions/{tx_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["total_amount"] == 1000.0

    assert client.get("/api/v1/transactions/9999").status_code == 404

    del_resp = client.delete(f"/api/v1/transactions/{tx_id}")
    assert del_resp.status_code == 204

    assert client.get(f"/api/v1/transactions/{tx_id}").status_code == 404

    assert client.delete("/api/v1/transactions/9999").status_code == 404
