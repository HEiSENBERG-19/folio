from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator
from app.models import TxType


class AccountCreate(BaseModel):
    name: str


class AccountUpdate(BaseModel):
    name: str


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
