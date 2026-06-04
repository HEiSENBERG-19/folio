from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.models import Asset, Transaction
from app.schemas import AssetCreate

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Asset])
def list_assets(session: Session = Depends(get_session)):
    assets = session.exec(select(Asset)).all()
    return assets


@router.post("", response_model=Asset, status_code=201)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)):
    ticker = payload.ticker.upper()

    # Check for duplicate ticker
    existing = session.exec(
        select(Asset).where(Asset.ticker == ticker)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Asset ticker already exists")

    asset = Asset(ticker=ticker, name=payload.name or "")
    session.add(asset)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Asset ticker already exists")
    session.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=Asset)
def get_asset(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Check for transactions referencing this asset
    txn = session.exec(
        select(Transaction).where(Transaction.asset_id == asset_id).limit(1)
    ).first()
    if txn:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete asset with existing transactions",
        )

    session.delete(asset)
    session.commit()
    return Response(status_code=204)
