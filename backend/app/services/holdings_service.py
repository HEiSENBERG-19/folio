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
