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
