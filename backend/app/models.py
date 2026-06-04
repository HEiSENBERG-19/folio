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


class FIFOLot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id")
    asset_id: int = Field(foreign_key="asset.id")
    open_transaction_id: int = Field(foreign_key="transaction.id")
    quantity_purchased: float
    quantity_remaining: float
    cost_per_unit: float
    opened_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LotClosure(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fifo_lot_id: int = Field(foreign_key="fifolot.id")
    sell_transaction_id: int = Field(foreign_key="transaction.id")
    quantity_closed: float
    cost_per_unit: float
    sell_price_per_unit: float
    realized_pnl: float
    closed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PriceCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    price_date: date = Field(index=True)
    close_price: float
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("asset_id", "price_date", name="uq_asset_price_date"),
    )
