from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from app.database import get_session
from app.models import Account, Transaction
from app.schemas import AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[Account])
def list_accounts(session: Session = Depends(get_session)):
    accounts = session.exec(select(Account)).all()
    return accounts


@router.post("", response_model=Account, status_code=201)
def create_account(payload: AccountCreate, session: Session = Depends(get_session)):
    # Check for duplicate name
    existing = session.exec(
        select(Account).where(Account.name == payload.name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Account name already exists")

    account = Account(name=payload.name)
    session.add(account)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Account name already exists")
    session.refresh(account)
    return account


@router.get("/{account_id}", response_model=Account)
def get_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.put("/{account_id}", response_model=Account)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    session: Session = Depends(get_session),
):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check for duplicate name (excluding current account)
    existing = session.exec(
        select(Account)
        .where(Account.name == payload.name)
        .where(Account.id != account_id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Account name already exists")

    account.name = payload.name
    account.updated_at = datetime.now(timezone.utc)
    session.add(account)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Account name already exists")
    session.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check for transactions referencing this account
    txn = session.exec(
        select(Transaction).where(Transaction.account_id == account_id).limit(1)
    ).first()
    if txn:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete account with existing transactions",
        )

    session.delete(account)
    session.commit()
    return Response(status_code=204)
