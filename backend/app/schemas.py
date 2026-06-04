from pydantic import BaseModel
from typing import Optional


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
