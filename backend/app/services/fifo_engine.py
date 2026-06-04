from sqlmodel import Session, select
from app.models import FIFOLot, LotClosure, Transaction, Account, TxType


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


def process_transaction(session: Session, tx: Transaction) -> None:
    account = session.get(Account, tx.account_id)
    if not account:
        raise ValueError(f"Account with id {tx.account_id} not found.")

    if tx.tx_type == TxType.DEPOSIT:
        account.cash_balance += tx.total_amount
        session.add(account)

    elif tx.tx_type == TxType.WITHDRAWAL:
        if account.cash_balance < tx.total_amount:
            raise ValueError("Insufficient cash for withdrawal.")
        account.cash_balance -= tx.total_amount
        session.add(account)

    elif tx.tx_type == TxType.FEE:
        account.cash_balance -= tx.total_amount
        session.add(account)

    elif tx.tx_type == TxType.BUY:
        if account.cash_balance < tx.total_amount:
            raise ValueError("Insufficient cash for purchase.")
        account.cash_balance -= tx.total_amount
        session.add(account)

        # Create new FIFOLot
        lot = FIFOLot(
            account_id=tx.account_id,
            asset_id=tx.asset_id,
            open_transaction_id=tx.id,
            quantity_purchased=tx.quantity,
            quantity_remaining=tx.quantity,
            cost_per_unit=tx.price_per_unit,
            opened_at=tx.executed_at
        )
        session.add(lot)

    elif tx.tx_type == TxType.SELL:
        account.cash_balance += tx.total_amount
        session.add(account)

        # Run process_sell
        process_sell(session, tx)


def replay_ledger(session: Session, account_id: int) -> None:
    account = session.get(Account, account_id)
    if not account:
        raise ValueError(f"Account with id {account_id} not found.")

    # 1. Delete all LotClosure rows associated with the account's lots.
    lots = session.exec(
        select(FIFOLot).where(FIFOLot.account_id == account_id)
    ).all()
    lot_ids = [lot.id for lot in lots]
    if lot_ids:
        closures = session.exec(
            select(LotClosure).where(LotClosure.fifo_lot_id.in_(lot_ids))
        ).all()
        for closure in closures:
            session.delete(closure)

    # 2. Delete all FIFOLot rows associated with the account.
    for lot in lots:
        session.delete(lot)

    # Flush deletes to avoid any conflict before reprocessing
    session.flush()

    # 3. Reset Account.cash_balance to 0.0.
    account.cash_balance = 0.0
    session.add(account)

    # 4. Fetch all remaining transactions for the account, ordered by executed_at (ascending) and id (ascending).
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.executed_at.asc(), Transaction.id.asc())
    ).all()

    # 5. Reprocess each transaction in order using process_transaction.
    for tx in transactions:
        process_transaction(session, tx)
