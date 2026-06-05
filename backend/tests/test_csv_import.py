"""Tests for CSV import service and endpoint."""
import pytest
import io
from datetime import datetime, timezone
from sqlmodel import select
from app.models import Account, Asset, Transaction, Holding, TxType
from app.services.csv_import import parse_csv, import_transactions, RowError

# --- Parser tests ---

SAMPLE_CSV = """Account,Ticker,Action,Quantity,Price,Date,Amount
account1,TRIDENT.NS,BUY,445.0,55.1,2022-04-22,24519.5
account2,TRIDENT.NS,BUY,500.0,51.8,2022-05-02,25900.0
account1,SUZLON.NS,BUY,2500.0,8.95,2022-05-16,22375.0
account2,SUZLON.NS,BUY,2000.0,8.95,2022-05-16,17900.0
account1,LICI.NS,BUY,15.0,904.0,2022-05-17,13560.0
account2,LICI.NS,BUY,15.0,904.0,2022-05-17,13560.0
account2,TATAPOWER.NS,BUY,125.0,230.0,2022-05-24,28750.0
account2,IEX.NS,BUY,500.0,130.0,2023-11-10,65000.0
account2,IEX.NS,SELL,500.0,164.1,2024-01-02,82050.0
account2,LICI.NS,SELL,15.0,1130.0,2024-01-03,16950.0
account1,LICI.NS,SELL,15.0,1000.0,2024-01-04,15000.0
account2,BAJAJHIND.NS,BUY,2905.0,28.05,2024-01-11,81485.25
account1,ALOKINDS.NS,BUY,1085.0,29.4,2024-02-16,31899.0
account2,BAJAJHIND.NS,SELL,2905.0,27.63,2025-01-15,80265.15
"""


def test_parse_csv_valid():
    rows, errors = parse_csv(SAMPLE_CSV)
    assert len(rows) == 14
    assert len(errors) == 0
    assert rows[0].account_name == "account1"
    assert rows[0].ticker == "TRIDENT.NS"
    assert rows[0].action == TxType.BUY


def test_parse_csv_missing_columns():
    csv_data = "Account,Action,Quantity\na,BUY,10"
    rows, errors = parse_csv(csv_data)
    assert len(rows) == 0
    assert len(errors) == 1
    assert "Missing required columns" in errors[0].message


def test_parse_csv_invalid_action():
    csv_data = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,DIVIDEND,10,5,2024-01-01"
    rows, errors = parse_csv(csv_data)
    assert len(rows) == 0
    assert len(errors) == 1
    assert "Invalid action" in errors[0].message


def test_parse_csv_bad_quantity():
    csv_data = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,BUY,-5,10,2024-01-01"
    rows, errors = parse_csv(csv_data)
    assert len(rows) == 0
    assert len(errors) == 1


def test_parse_csv_bad_date():
    csv_data = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,BUY,10,5,2024/01/01"
    rows, errors = parse_csv(csv_data)
    assert len(rows) == 0
    assert len(errors) == 1
    assert "Invalid date" in errors[0].message


def test_parse_csv_amount_fallback():
    csv_data = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,BUY,10,50,2024-01-01"
    rows, errors = parse_csv(csv_data)
    assert len(rows) == 1
    assert rows[0].amount == 500.0  # 10 * 50


# --- Import tests (use test DB session from conftest) ---

def test_import_creates_accounts(session):
    rows, _ = parse_csv(SAMPLE_CSV)
    result = import_transactions(session, rows)
    assert "account1" in result.created_accounts
    assert "account2" in result.created_accounts


def test_import_creates_assets(session):
    rows, _ = parse_csv(SAMPLE_CSV)
    result = import_transactions(session, rows)
    assert "TRIDENT.NS" in result.created_assets
    assert "SUZLON.NS" in result.created_assets


def test_import_count(session):
    rows, _ = parse_csv(SAMPLE_CSV)
    result = import_transactions(session, rows)
    assert result.imported_count == 14
    assert result.skipped_count == 0
    assert len(result.errors) == 0


def test_import_duplicate_skip(session):
    rows, _ = parse_csv(SAMPLE_CSV)
    import_transactions(session, rows)
    # Import again
    rows2, _ = parse_csv(SAMPLE_CSV)
    result2 = import_transactions(session, rows2)
    assert result2.imported_count == 0
    assert result2.skipped_count == 14


def test_import_sell_before_buy_error(session):
    csv_data = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,SELL,10,50,2024-01-01"
    rows, _ = parse_csv(csv_data)
    result = import_transactions(session, rows)
    assert result.imported_count == 0
    assert len(result.errors) == 1
    assert "Insufficient shares" in result.errors[0].message


def test_import_holdings_correct(session):
    """After importing sample CSV, verify WAC holdings are correct."""
    rows, _ = parse_csv(SAMPLE_CSV)
    import_transactions(session, rows)

    # Check account1 TRIDENT.NS: bought 445 @ 55.1, never sold
    asset = session.exec(select(Asset).where(Asset.ticker == "TRIDENT.NS")).first()
    account = session.exec(select(Account).where(Account.name == "account1")).first()
    holding = session.exec(
        select(Holding)
        .where(Holding.account_id == account.id)
        .where(Holding.asset_id == asset.id)
    ).first()
    assert holding.total_shares == 445.0
    assert abs(holding.total_cost - 24519.5) < 0.01

    # Check account2 IEX.NS: bought 500 @ 130, sold 500 @ 164.1
    # Realized PNL = (164.1 - 130) * 500 = 17050
    asset_iex = session.exec(select(Asset).where(Asset.ticker == "IEX.NS")).first()
    account2 = session.exec(select(Account).where(Account.name == "account2")).first()
    holding_iex = session.exec(
        select(Holding)
        .where(Holding.account_id == account2.id)
        .where(Holding.asset_id == asset_iex.id)
    ).first()
    assert holding_iex.total_shares == 0.0
    assert abs(holding_iex.realized_pnl - 17050.0) < 0.01


# --- Endpoint integration test ---

def test_import_endpoint(client):
    """Test the /api/v1/transactions/import endpoint."""
    response = client.post(
        "/api/v1/transactions/import",
        files={"file": ("trades.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] == 14
    assert len(data["created_accounts"]) == 2
    assert len(data["created_assets"]) > 0
