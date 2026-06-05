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
    currency: str = Field(default="INR")
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


class PriceCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    price_date: date = Field(index=True)
    close_price: float
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("asset_id", "price_date", name="uq_asset_price_date"),
    )


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

