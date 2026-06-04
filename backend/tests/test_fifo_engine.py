import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select
from fastapi.testclient import TestClient

from app.models import Account, Asset, Transaction, FIFOLot, LotClosure, TxType
from app.services.fifo_engine import process_transaction, replay_ledger


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


def test_buy_creates_lot(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 2000.0
    session.add(account)
    session.commit()

    tx = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime.now(timezone.utc)
    )
    session.add(tx)
    session.flush()

    process_transaction(session, tx)
    session.commit()

    # Check cash decreased
    session.refresh(account)
    assert account.cash_balance == 500.0

    # Check lot created
    lots = session.exec(select(FIFOLot).where(FIFOLot.account_id == account.id)).all()
    assert len(lots) == 1
    lot = lots[0]
    assert lot.asset_id == asset.id
    assert lot.open_transaction_id == tx.id
    assert lot.quantity_purchased == 10.0
    assert lot.quantity_remaining == 10.0
    assert lot.cost_per_unit == 150.0


def test_sell_partial_lot(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 2000.0
    session.add(account)
    session.commit()

    # Buy 10 AAPL at 150
    tx_buy = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy)
    session.flush()
    process_transaction(session, tx_buy)

    # Sell 4 AAPL at 170
    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=4.0,
        price_per_unit=170.0,
        total_amount=680.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    session.refresh(account)
    # Cash balance should be: 2000 - 1500 + 680 = 1180
    assert account.cash_balance == 1180.0

    # Check lots
    lots = session.exec(select(FIFOLot).where(FIFOLot.account_id == account.id)).all()
    assert len(lots) == 1
    assert lots[0].quantity_remaining == 6.0

    # Check closures
    closures = session.exec(select(LotClosure)).all()
    assert len(closures) == 1
    closure = closures[0]
    assert closure.fifo_lot_id == lots[0].id
    assert closure.sell_transaction_id == tx_sell.id
    assert closure.quantity_closed == 4.0
    assert closure.cost_per_unit == 150.0
    assert closure.sell_price_per_unit == 170.0
    assert closure.realized_pnl == (170.0 - 150.0) * 4.0  # 80.0


def test_sell_consumes_oldest_lot_first(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 4000.0
    session.add(account)
    session.commit()

    # Buy Lot 1: 10 AAPL at 150 on Day 1
    tx_buy1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy1)
    session.flush()
    process_transaction(session, tx_buy1)

    # Buy Lot 2: 10 AAPL at 160 on Day 2
    tx_buy2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=160.0,
        total_amount=1600.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy2)
    session.flush()
    process_transaction(session, tx_buy2)

    # Sell: 5 AAPL at 170 on Day 3
    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=5.0,
        price_per_unit=170.0,
        total_amount=850.0,
        executed_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    lots = session.exec(
        select(FIFOLot).where(FIFOLot.account_id == account.id).order_by(FIFOLot.id.asc())
    ).all()
    assert len(lots) == 2
    # First lot should be consumed partially (5 remaining)
    assert lots[0].quantity_remaining == 5.0
    # Second lot should remain fully untouched (10 remaining)
    assert lots[1].quantity_remaining == 10.0


def test_sell_spans_multiple_lots(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 4000.0
    session.add(account)
    session.commit()

    # Buy Lot 1: 10 AAPL at 150 on Day 1
    tx_buy1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy1)
    session.flush()
    process_transaction(session, tx_buy1)

    # Buy Lot 2: 10 AAPL at 160 on Day 2
    tx_buy2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=160.0,
        total_amount=1600.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy2)
    session.flush()
    process_transaction(session, tx_buy2)

    # Sell 15 shares (spans Lot 1 completely and Lot 2 partially)
    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=15.0,
        price_per_unit=170.0,
        total_amount=2550.0,
        executed_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    lots = session.exec(
        select(FIFOLot).where(FIFOLot.account_id == account.id).order_by(FIFOLot.id.asc())
    ).all()
    assert len(lots) == 2
    # Lot 1 fully consumed
    assert lots[0].quantity_remaining == 0.0
    # Lot 2 partially consumed
    assert lots[1].quantity_remaining == 5.0

    # PnL Check:
    # Lot 1: 10 * (170 - 150) = 200
    # Lot 2: 5 * (170 - 160) = 50
    closures = session.exec(select(LotClosure).order_by(LotClosure.id.asc())).all()
    assert len(closures) == 2
    assert closures[0].realized_pnl == 200.0
    assert closures[1].realized_pnl == 50.0


def test_sell_exact_full_lot(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 2000.0
    session.add(account)
    session.commit()

    tx_buy = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy)
    session.flush()
    process_transaction(session, tx_buy)

    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=10.0,
        price_per_unit=170.0,
        total_amount=1700.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    lots = session.exec(select(FIFOLot).where(FIFOLot.account_id == account.id)).all()
    assert len(lots) == 1
    assert lots[0].quantity_remaining == 0.0


def test_sell_insufficient_shares(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 2000.0
    session.add(account)
    session.commit()

    tx_buy = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy)
    session.flush()
    process_transaction(session, tx_buy)

    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=11.0,
        price_per_unit=170.0,
        total_amount=1870.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()

    with pytest.raises(ValueError, match="Insufficient shares to sell."):
        process_transaction(session, tx_sell)


def test_realized_pnl_calculation(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 5000.0
    session.add(account)
    session.commit()

    # Buy 10 shares at 150
    tx_buy1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy1)
    session.flush()
    process_transaction(session, tx_buy1)

    # Buy 10 shares at 160
    tx_buy2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=160.0,
        total_amount=1600.0,
        executed_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_buy2)
    session.flush()
    process_transaction(session, tx_buy2)

    # Sell 15 shares at 170
    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=15.0,
        price_per_unit=170.0,
        total_amount=2550.0,
        executed_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    # Realized PnL:
    # Day 1 lot: 10 * (170 - 150) = 200
    # Day 2 lot: 5 * (170 - 160) = 50
    closures = session.exec(select(LotClosure).order_by(LotClosure.id.asc())).all()
    assert len(closures) == 2
    assert closures[0].realized_pnl == 200.0
    assert closures[1].realized_pnl == 50.0
    assert sum(c.realized_pnl for c in closures) == 250.0


def test_replay_ledger(session: Session):
    account, asset = create_base_data(session)

    # Sequence:
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

    lots_initial = session.exec(select(FIFOLot).order_by(FIFOLot.id.asc())).all()
    assert len(lots_initial) == 2
    assert lots_initial[0].quantity_remaining == 5.0
    assert lots_initial[1].quantity_remaining == 10.0

    closures_initial = session.exec(select(LotClosure)).all()
    assert len(closures_initial) == 1
    assert closures_initial[0].quantity_closed == 5.0
    assert closures_initial[0].realized_pnl == 100.0

    # Delete the second BUY (tx_buy2)
    session.delete(tx_buy2)
    session.flush()

    # Run replay_ledger
    replay_ledger(session, account.id)
    session.commit()

    # Replayed state check:
    # Transactions left: Deposit 10000, Buy1 10 at 150, Sell 5 at 170.
    # Cash: 10000 - 1500 + 850 = 9350.
    session.refresh(account)
    assert account.cash_balance == 9350.0

    lots_replayed = session.exec(select(FIFOLot).order_by(FIFOLot.id.asc())).all()
    assert len(lots_replayed) == 1
    assert lots_replayed[0].quantity_remaining == 5.0
    assert lots_replayed[0].quantity_purchased == 10.0

    closures_replayed = session.exec(select(LotClosure)).all()
    assert len(closures_replayed) == 1
    assert closures_replayed[0].quantity_closed == 5.0
    assert closures_replayed[0].realized_pnl == 100.0


def test_fifo_order_with_same_date(session: Session):
    account, asset = create_base_data(session)
    account.cash_balance = 4000.0
    session.add(account)
    session.commit()

    # Both BUYs have the exact same executed_at date/time
    same_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Buy 1: 10 shares at 150
    tx_buy1 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=150.0,
        total_amount=1500.0,
        executed_at=same_time
    )
    session.add(tx_buy1)
    session.flush()
    process_transaction(session, tx_buy1)

    # Buy 2: 10 shares at 160
    tx_buy2 = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.BUY,
        quantity=10.0,
        price_per_unit=160.0,
        total_amount=1600.0,
        executed_at=same_time
    )
    session.add(tx_buy2)
    session.flush()
    process_transaction(session, tx_buy2)

    # Sell 5 shares at 170
    tx_sell = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        tx_type=TxType.SELL,
        quantity=5.0,
        price_per_unit=170.0,
        total_amount=850.0,
        executed_at=same_time
    )
    session.add(tx_sell)
    session.flush()
    process_transaction(session, tx_sell)
    session.commit()

    # Verify that the lot with the smaller id (lot 1) is consumed first.
    lots = session.exec(select(FIFOLot).order_by(FIFOLot.id.asc())).all()
    assert len(lots) == 2
    assert lots[0].id < lots[1].id
    # First lot (which has cost_per_unit = 150) should be partially consumed
    assert lots[0].quantity_remaining == 5.0
    assert lots[1].quantity_remaining == 10.0

    closures = session.exec(select(LotClosure)).all()
    assert len(closures) == 1
    assert closures[0].fifo_lot_id == lots[0].id
    assert closures[0].cost_per_unit == 150.0


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

