from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File
from sqlmodel import Session, select
from typing import Optional

from app.database import get_session
from app.models import Transaction, Account, Asset, TxType
from app.schemas import TransactionCreate
from app.services.transaction_service import process_transaction, replay_account_holdings
from app.services.csv_import import parse_csv, import_transactions

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[Transaction])
def list_transactions(
    account_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    tx_type: Optional[TxType] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    session: Session = Depends(get_session)
):
    query = select(Transaction)
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if asset_id is not None:
        query = query.where(Transaction.asset_id == asset_id)
    if tx_type is not None:
        query = query.where(Transaction.tx_type == tx_type)
    
    query = query.offset(skip).limit(limit)
    transactions = session.exec(query).all()
    return transactions


@router.post("", response_model=Transaction, status_code=201)
def create_transaction(payload: TransactionCreate, session: Session = Depends(get_session)):
    # Check if account exists
    account = session.get(Account, payload.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check if asset exists if asset_id is provided
    if payload.asset_id is not None:
        asset = session.get(Asset, payload.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

    tx = Transaction(
        account_id=payload.account_id,
        asset_id=payload.asset_id,
        tx_type=payload.tx_type,
        quantity=payload.quantity,
        price_per_unit=payload.price_per_unit,
        total_amount=payload.total_amount,
        notes=payload.notes,
        executed_at=payload.executed_at,
    )

    session.add(tx)
    try:
        session.flush()
        process_transaction(session, tx)
        session.commit()
    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    session.refresh(tx)
    return tx


@router.post("/import")
async def import_csv_endpoint(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Import transactions from a CSV file.

    Expected columns: Account, Ticker, Action, Quantity, Price, Date
    Optional: Amount (defaults to Quantity × Price)

    Auto-creates missing accounts (INR) and assets.
    Skips duplicate rows. Reports errors per-row.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    # Read content
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    # Parse
    parsed_rows, parse_errors = parse_csv(text)

    if parse_errors and not parsed_rows:
        # All rows failed parsing or header error
        return {
            "total_rows": 0,
            "imported_count": 0,
            "skipped_count": 0,
            "errors": [{"row": e.row, "message": e.message} for e in parse_errors],
            "created_accounts": [],
            "created_assets": [],
        }

    # Import valid rows
    try:
        result = import_transactions(session, parsed_rows)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    # Merge parse errors + import errors
    all_errors = [{"row": e.row, "message": e.message} for e in parse_errors]
    all_errors += [{"row": e.row, "message": e.message} for e in result.errors]

    return {
        "total_rows": len(parsed_rows) + len(parse_errors),
        "imported_count": result.imported_count,
        "skipped_count": result.skipped_count,
        "errors": all_errors,
        "created_accounts": result.created_accounts,
        "created_assets": result.created_assets,
    }


@router.get("/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: int, session: Session = Depends(get_session)):
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, session: Session = Depends(get_session)):
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    account_id = tx.account_id
    session.delete(tx)

    try:
        session.flush()
        replay_account_holdings(session, account_id)
        session.commit()
    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=204)
