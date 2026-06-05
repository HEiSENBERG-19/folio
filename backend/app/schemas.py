from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator
from app.models import TxType


class AccountCreate(BaseModel):
    name: str
    currency: Optional[str] = "USD"


class AccountUpdate(BaseModel):
    name: str
    currency: Optional[str] = None


class AssetCreate(BaseModel):
    ticker: str
    name: Optional[str] = ""


class AssetUpdate(BaseModel):
    name: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str


class TransactionCreate(BaseModel):
    account_id: int
    asset_id: Optional[int] = None
    tx_type: TxType
    quantity: float = 0.0
    price_per_unit: float = 0.0
    total_amount: float = 0.0
    notes: str = ""
    executed_at: datetime

    @model_validator(mode="after")
    def validate_tx_rules(self) -> "TransactionCreate":
        if self.tx_type in (TxType.BUY, TxType.SELL):
            if self.asset_id is None:
                raise ValueError("asset_id must be provided for BUY/SELL transactions")
            if self.quantity <= 0:
                raise ValueError("quantity must be greater than 0 for BUY/SELL transactions")
            if self.price_per_unit <= 0:
                raise ValueError("price_per_unit must be greater than 0 for BUY/SELL transactions")
            self.total_amount = self.quantity * self.price_per_unit
        elif self.tx_type in (TxType.DEPOSIT, TxType.WITHDRAWAL, TxType.FEE):
            if self.total_amount <= 0:
                raise ValueError("total_amount must be greater than 0 for DEPOSIT/WITHDRAWAL/FEE transactions")
            self.quantity = 0.0
            self.price_per_unit = 0.0
            self.asset_id = None
        return self


class HoldingDetail(BaseModel):
    ticker: str
    asset_name: str
    total_shares: float
    avg_cost_basis: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float


class PortfolioSummary(BaseModel):
    total_invested: float
    total_market_value: float
    total_cash: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    net_portfolio_value: float
    holdings: list[HoldingDetail]


from datetime import date

class PortfolioHistoryPoint(BaseModel):
    date: date
    portfolio_value: float
    cash_balance: float
    total_value: float


class PortfolioHistory(BaseModel):
    period: str
    data_points: list[PortfolioHistoryPoint]


class AllocationSlice(BaseModel):
    ticker: str
    market_value: float
    percentage: float


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
    stock_value_native: float = 0.0


class PortfolioInsights(BaseModel):
    holdings: list[HoldingInsightDetail]
    cash_balances: list[CashInsightDetail]
    usd_inr_rate: float


