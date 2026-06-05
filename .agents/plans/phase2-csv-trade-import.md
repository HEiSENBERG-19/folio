---
name: "Phase 2: CSV Trade Import"
status: Planned
priority: high
created: 2026-06-05
updated: 2026-06-05
depends_on: phase1-architecture-cleanup
progress:
  - "[ ] Task 1: Create CSV parsing service with row validation"
  - "[ ] Task 2: Create import orchestrator service"
  - "[ ] Task 3: Add POST /api/v1/transactions/import endpoint"
  - "[ ] Task 4: Add backend tests for CSV import"
  - "[ ] Task 5: Add frontend types and hook for CSV import"
  - "[ ] Task 6: Add CSV upload UI to Transactions page"
  - "[ ] Task 7: End-to-end manual QA with sample CSV"
---

# Phase 2: CSV Trade Import

## Summary

Add a CSV upload endpoint that parses a trade history file, validates all rows, auto-creates missing accounts (always INR) and assets, and batch-inserts the transactions with WAC holding updates. Returns a detailed result with successes, skips, and errors. Frontend gets an "Import CSV" button with a results modal.

## Motivation

Manually entering 15+ historical transactions is tedious. The user has a CSV export ([trades_with_amount.csv](file:///home/heisenberg/projects/folio/docs/trades_with_amount.csv)) with this format:

```
Account,Ticker,Action,Quantity,Price,Date,Amount
account1,TRIDENT.NS,BUY,445.0,55.1,2022-04-22,24519.5
account2,IEX.NS,SELL,500.0,164.1,2024-01-02,82050.0
```

Key rules (from user feedback):
- CSV has **only BUY/SELL** — no deposits/withdrawals.
- **Negative cash is allowed** — this is a tracker, not a bank. The user records trades that already happened.
- Missing accounts are **auto-created as INR**.
- Missing tickers are **auto-created**.
- **Partial imports** — import what's valid, report what's not.
- **Duplicate detection** — skip rows that already exist in DB.

## Acceptance Criteria

1. `POST /api/v1/transactions/import` accepts `multipart/form-data` with a CSV file.
2. Required columns: `Account`, `Ticker`, `Action`, `Quantity`, `Price`, `Date`. Optional: `Amount`.
3. `Amount` defaults to `Quantity × Price` if missing or zero.
4. `Action` must be `BUY` or `SELL` (case-insensitive). Other values reject the row.
5. Missing accounts auto-created with `currency='INR'`.
6. Missing tickers auto-created as `Asset` records.
7. Rows processed in **chronological order** (sorted by Date).
8. SELL validation: rejected if insufficient shares (from existing holdings + earlier CSV buys in same batch).
9. Partial success: valid rows import, invalid rows reported with row number and reason.
10. Duplicate rows skipped (same account, asset, type, quantity, price, date).
11. Response: `{ total_rows, imported_count, skipped_count, errors[], created_accounts[], created_assets[] }`.
12. Frontend: "Import CSV" button on Transactions page, file picker, result summary modal.

---

## Technical Design

### Backend

#### Task 1: CSV Parsing Service

**New file:** `backend/app/services/csv_import.py`

This file contains the parser and the import orchestrator.

```python
import csv
import io
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlmodel import Session, select
from app.models import Account, Asset, Transaction, Holding, TxType
from app.services.holdings_service import apply_buy, apply_sell


@dataclass
class ParsedRow:
    """A single validated row from the CSV."""
    row_number: int
    account_name: str
    ticker: str
    action: TxType
    quantity: float
    price: float
    date: datetime
    amount: float


@dataclass
class RowError:
    """A row that failed validation or import."""
    row: int
    message: str


@dataclass
class ImportResult:
    """Complete result of a CSV import operation."""
    total_rows: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    errors: list[RowError] = field(default_factory=list)
    created_accounts: list[str] = field(default_factory=list)
    created_assets: list[str] = field(default_factory=list)


def parse_csv(file_content: str) -> tuple[list[ParsedRow], list[RowError]]:
    """Parse and validate CSV content.

    Expected columns: Account, Ticker, Action, Quantity, Price, Date
    Optional column: Amount

    Returns (valid_rows, errors).
    """
    rows: list[ParsedRow] = []
    errors: list[RowError] = []

    reader = csv.DictReader(io.StringIO(file_content))

    # Validate headers
    if not reader.fieldnames:
        errors.append(RowError(row=0, message="CSV file is empty or has no headers"))
        return rows, errors

    headers = {h.strip() for h in reader.fieldnames}
    required = {'Account', 'Ticker', 'Action', 'Quantity', 'Price', 'Date'}
    missing = required - headers
    if missing:
        errors.append(RowError(row=0, message=f"Missing required columns: {', '.join(sorted(missing))}"))
        return rows, errors

    for row_num, row in enumerate(reader, start=2):  # Row 1 = header
        try:
            row = {k.strip(): (v.strip() if v else '') for k, v in row.items() if k}

            account = row.get('Account', '')
            ticker = row.get('Ticker', '').upper()
            action_str = row.get('Action', '').upper()
            qty_str = row.get('Quantity', '')
            price_str = row.get('Price', '')
            date_str = row.get('Date', '')
            amount_str = row.get('Amount', '')

            # Validate each field
            if not account:
                errors.append(RowError(row=row_num, message="Account name is empty"))
                continue
            if not ticker:
                errors.append(RowError(row=row_num, message="Ticker is empty"))
                continue
            if action_str not in ('BUY', 'SELL'):
                errors.append(RowError(row=row_num, message=f"Invalid action '{action_str}'. Must be BUY or SELL"))
                continue

            action = TxType.BUY if action_str == 'BUY' else TxType.SELL

            try:
                quantity = float(qty_str)
                if quantity <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(RowError(row=row_num, message=f"Invalid quantity: '{qty_str}'"))
                continue

            try:
                price = float(price_str)
                if price <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append(RowError(row=row_num, message=f"Invalid price: '{price_str}'"))
                continue

            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                errors.append(RowError(row=row_num, message=f"Invalid date: '{date_str}'. Expected YYYY-MM-DD"))
                continue

            # Amount: use CSV value if present and > 0, else compute
            amount = quantity * price
            if amount_str:
                try:
                    csv_amount = float(amount_str)
                    if csv_amount > 0:
                        amount = csv_amount
                except (ValueError, TypeError):
                    pass  # Fall back to computed

            rows.append(ParsedRow(
                row_number=row_num,
                account_name=account,
                ticker=ticker,
                action=action,
                quantity=quantity,
                price=price,
                date=date,
                amount=amount,
            ))
        except Exception as e:
            errors.append(RowError(row=row_num, message=f"Unexpected error: {str(e)}"))

    return rows, errors


def import_transactions(session: Session, parsed_rows: list[ParsedRow]) -> ImportResult:
    """Import parsed CSV rows into the database.

    Steps:
      1. Sort rows chronologically.
      2. Auto-create missing accounts (currency='INR').
      3. Auto-create missing assets.
      4. For each row:
         a. Check for duplicate → skip if found.
         b. Create Transaction, flush to get ID.
         c. Update cash balance (no validation — negative OK).
         d. Update holding via WAC (apply_buy or apply_sell).
         e. If sell fails (insufficient shares), record error, delete tx.
      5. Commit.
    """
    result = ImportResult(total_rows=len(parsed_rows))

    # Sort chronologically, stable by row number
    sorted_rows = sorted(parsed_rows, key=lambda r: (r.date, r.row_number))

    # --- Phase 1: Auto-create accounts ---
    unique_accounts = sorted(set(r.account_name for r in sorted_rows))
    account_map: dict[str, int] = {}  # name -> id

    for name in unique_accounts:
        existing = session.exec(
            select(Account).where(Account.name == name)
        ).first()
        if existing:
            account_map[name] = existing.id
        else:
            account = Account(name=name, currency="INR")
            session.add(account)
            session.flush()
            account_map[name] = account.id
            result.created_accounts.append(name)

    # --- Phase 2: Auto-create assets ---
    unique_tickers = sorted(set(r.ticker for r in sorted_rows))
    asset_map: dict[str, int] = {}  # ticker -> id

    for ticker in unique_tickers:
        existing = session.exec(
            select(Asset).where(Asset.ticker == ticker)
        ).first()
        if existing:
            asset_map[ticker] = existing.id
        else:
            asset = Asset(ticker=ticker, name=ticker)
            session.add(asset)
            session.flush()
            asset_map[ticker] = asset.id
            result.created_assets.append(ticker)

    # --- Phase 3: Import rows ---
    for row in sorted_rows:
        account_id = account_map[row.account_name]
        asset_id = asset_map[row.ticker]

        # Duplicate check
        existing_tx = session.exec(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .where(Transaction.asset_id == asset_id)
            .where(Transaction.tx_type == row.action)
            .where(Transaction.quantity == row.quantity)
            .where(Transaction.price_per_unit == row.price)
            .where(Transaction.executed_at == row.date)
        ).first()

        if existing_tx:
            result.skipped_count += 1
            continue

        # Create transaction
        tx = Transaction(
            account_id=account_id,
            asset_id=asset_id,
            tx_type=row.action,
            quantity=row.quantity,
            price_per_unit=row.price,
            total_amount=row.amount,
            notes=f"CSV import row {row.row_number}",
            executed_at=row.date,
        )
        session.add(tx)
        session.flush()  # Get tx.id

        # Update cash balance (no validation — negative allowed)
        account = session.get(Account, account_id)
        if row.action == TxType.BUY:
            account.cash_balance -= row.amount
        elif row.action == TxType.SELL:
            account.cash_balance += row.amount
        session.add(account)

        # Update holding via WAC
        try:
            if row.action == TxType.BUY:
                apply_buy(session, tx)
            elif row.action == TxType.SELL:
                apply_sell(session, tx)
            result.imported_count += 1
        except ValueError as e:
            # SELL failed (insufficient shares) — rollback this tx
            result.errors.append(RowError(row=row.row_number, message=str(e)))
            # Undo cash effect
            if row.action == TxType.BUY:
                account.cash_balance += row.amount
            elif row.action == TxType.SELL:
                account.cash_balance -= row.amount
            session.add(account)
            session.delete(tx)
            session.flush()

    session.commit()
    return result
```

#### Task 3: Add endpoint to transaction router

**Modify:** `backend/app/routers/transactions.py`

Add this new route **before** the `/{transaction_id}` routes (FastAPI matches routes in order):

```python
from fastapi import UploadFile, File
from app.services.csv_import import parse_csv, import_transactions


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
```

**Important placement:** The `/import` route MUST be defined **before** `/{transaction_id}` routes in the router file. Otherwise FastAPI will try to parse "import" as a transaction_id integer and return 422.

#### Task 4: Backend tests

**New file:** `backend/tests/test_csv_import.py`

```python
"""Tests for CSV import service and endpoint."""
import pytest
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
    csv = "Account,Action,Quantity\na,BUY,10"
    rows, errors = parse_csv(csv)
    assert len(rows) == 0
    assert len(errors) == 1
    assert "Missing required columns" in errors[0].message


def test_parse_csv_invalid_action():
    csv = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,DIVIDEND,10,5,2024-01-01"
    rows, errors = parse_csv(csv)
    assert len(rows) == 0
    assert len(errors) == 1
    assert "Invalid action" in errors[0].message


def test_parse_csv_bad_quantity():
    csv = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,BUY,-5,10,2024-01-01"
    rows, errors = parse_csv(csv)
    assert len(rows) == 0
    assert len(errors) == 1


def test_parse_csv_bad_date():
    csv = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,BUY,10,5,2024/01/01"
    rows, errors = parse_csv(csv)
    assert len(rows) == 0
    assert len(errors) == 1
    assert "Invalid date" in errors[0].message


def test_parse_csv_amount_fallback():
    csv = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,BUY,10,50,2024-01-01"
    rows, errors = parse_csv(csv)
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
    csv = "Account,Ticker,Action,Quantity,Price,Date\na,X.NS,SELL,10,50,2024-01-01"
    rows, _ = parse_csv(csv)
    result = import_transactions(session, rows)
    assert result.imported_count == 0
    assert len(result.errors) == 1
    assert "Insufficient shares" in result.errors[0].message


def test_import_holdings_correct(session):
    """After importing sample CSV, verify WAC holdings are correct."""
    rows, _ = parse_csv(SAMPLE_CSV)
    import_transactions(session, rows)

    # Check account1 TRIDENT.NS: bought 445 @ 55.1, never sold
    from app.models import Holding, Account, Asset
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
    import io
    response = client.post(
        "/api/v1/transactions/import",
        files={"file": ("trades.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] == 14
    assert len(data["created_accounts"]) == 2
    assert len(data["created_assets"]) > 0
```

---

### Frontend

#### Task 5: Types and Hook

**Add to:** `frontend/src/types/index.ts`

```typescript
export interface CsvImportResult {
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  errors: Array<{ row: number; message: string }>;
  created_accounts: string[];
  created_assets: string[];
}
```

**Add to:** `frontend/src/hooks/useTransactions.ts`

```typescript
import type { CsvImportResult } from '../types';

export function useImportCsv() {
  const queryClient = useQueryClient();
  return useMutation<CsvImportResult, Error, File>({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post('/transactions/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}
```

#### Task 6: CSV Upload UI on Transactions Page

**Modify:** `frontend/src/pages/Transactions.tsx`

**Add import to lucide:** `Upload` icon.

**Add state variables:**
```tsx
const [isImportModalOpen, setIsImportModalOpen] = useState(false);
const [importFile, setImportFile] = useState<File | null>(null);
const [importResult, setImportResult] = useState<CsvImportResult | null>(null);
```

**Add "Import CSV" button** next to "Add Trade":
```tsx
<div className="flex gap-3">
  <button onClick={() => setIsImportModalOpen(true)}
    className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 font-semibold text-sm rounded-xl transition-all duration-200 cursor-pointer">
    <Upload className="h-5 w-5" />
    Import CSV
  </button>
  <button onClick={() => { /* existing Add Trade logic */ }}
    className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 ...">
    <Plus className="h-5 w-5 stroke-[2.5]" />
    Add Trade
  </button>
</div>
```

**Add Import Modal** (rendered conditionally when `isImportModalOpen` is true):

```tsx
{isImportModalOpen && (
  <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
    <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h2 className="text-xl font-bold text-white">Import CSV</h2>
        <button onClick={() => { setIsImportModalOpen(false); setImportFile(null); setImportResult(null); }}
          className="text-slate-400 hover:text-slate-200 cursor-pointer">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* BEFORE import: file picker */}
      {!importResult ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Upload a CSV with columns: <span className="text-slate-300 font-medium">Account, Ticker, Action, Quantity, Price, Date</span>.
            Optional: <span className="text-slate-300 font-medium">Amount</span>.
          </p>

          {/* Drop zone / file input */}
          <label className="flex flex-col items-center justify-center h-32 border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl cursor-pointer bg-slate-950/50 transition-colors">
            <Upload className="h-8 w-8 text-slate-600 mb-2" />
            <span className="text-sm text-slate-500">
              {importFile ? importFile.name : 'Click to select CSV file'}
            </span>
            <input type="file" accept=".csv" className="hidden"
              onChange={(e) => setImportFile(e.target.files?.[0] || null)} />
          </label>

          <div className="flex gap-3 justify-end pt-2">
            <button onClick={() => { setIsImportModalOpen(false); setImportFile(null); }}
              className="px-5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm font-semibold text-slate-400 cursor-pointer">
              Cancel
            </button>
            <button disabled={!importFile || importCsv.isPending}
              onClick={() => {
                if (importFile) {
                  importCsv.mutate(importFile, {
                    onSuccess: (data) => setImportResult(data),
                    onError: (err) => showToast(err.message, 'error'),
                  });
                }
              }}
              className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold text-sm rounded-xl cursor-pointer disabled:opacity-55">
              {importCsv.isPending ? 'Importing...' : 'Import'}
            </button>
          </div>
        </div>
      ) : (
        /* AFTER import: results summary */
        <div className="space-y-4">
          {/* Success count */}
          <div className="flex items-center gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
            <span className="text-2xl font-bold text-emerald-400">{importResult.imported_count}</span>
            <span className="text-sm text-emerald-300">transactions imported</span>
          </div>

          {/* Skipped */}
          {importResult.skipped_count > 0 && (
            <div className="flex items-center gap-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl">
              <span className="text-lg font-bold text-blue-400">{importResult.skipped_count}</span>
              <span className="text-sm text-blue-300">duplicates skipped</span>
            </div>
          )}

          {/* Auto-created entities */}
          {importResult.created_accounts.length > 0 && (
            <div className="text-xs text-slate-400">
              <span className="font-medium text-slate-300">Accounts created: </span>
              {importResult.created_accounts.join(', ')}
            </div>
          )}
          {importResult.created_assets.length > 0 && (
            <div className="text-xs text-slate-400">
              <span className="font-medium text-slate-300">Assets registered: </span>
              {importResult.created_assets.join(', ')}
            </div>
          )}

          {/* Errors */}
          {importResult.errors.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-red-400 uppercase tracking-wider">Errors ({importResult.errors.length})</p>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {importResult.errors.map((err, i) => (
                  <div key={i} className="text-xs text-red-300 bg-red-500/5 border border-red-500/10 px-3 py-1.5 rounded-lg">
                    Row {err.row}: {err.message}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button onClick={() => { setIsImportModalOpen(false); setImportFile(null); setImportResult(null); }}
              className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold text-sm rounded-xl cursor-pointer">
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  </div>
)}
```

---

### Database Changes

None — reuses tables from Phase 1 (`Account`, `Asset`, `Transaction`, `Holding`).

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Empty CSV (headers only) | `total_rows: 0`, no errors, nothing imported |
| Missing required columns | Error on row 0 listing missing columns |
| Duplicate rows within same CSV | First occurrence imports, subsequent skipped |
| Duplicate of existing DB transaction | Skipped (not an error, counted in `skipped_count`) |
| SELL before any BUY for that ticker | Error: "Insufficient shares to sell" — row skipped |
| Account already exists in DB | Reused, not duplicated |
| Ticker already exists in DB | Reused, not duplicated |
| Amount column missing entirely | Computed as `Quantity × Price` for all rows |
| Amount differs from Q×P | CSV Amount used (trust the broker statement) |
| Non-UTF-8 encoding | 400 error: "File must be UTF-8 encoded" |
| Not a .csv file | 400 error: "File must be a .csv file" |
| Negative cash balance after BUY | **Allowed** — cash_balance goes negative, no validation |
| Empty file (0 bytes) | Error: "CSV file is empty or has no headers" |

## Testing Strategy

### Backend
- 12+ test cases in `test_csv_import.py` covering parser, importer, and endpoint
- Run with: `cd backend && source .venv/bin/activate && python -m pytest tests/test_csv_import.py -v`

### Frontend
- `npm run build` passes
- `npx tsc --noEmit` passes
- Manual QA: upload `docs/trades_with_amount.csv`, verify:
  - 14 transactions imported
  - 2 accounts created (account1, account2)
  - 7+ assets created
  - Holdings page shows correct positions
  - Dashboard shows correct portfolio values

## Files to Modify

- `backend/app/routers/transactions.py` — add `/import` endpoint (must be before `/{transaction_id}`)
- `frontend/src/pages/Transactions.tsx` — add Import CSV button, file picker modal, results display
- `frontend/src/hooks/useTransactions.ts` — add `useImportCsv` mutation hook
- `frontend/src/types/index.ts` — add `CsvImportResult` interface

## New Files

- `backend/app/services/csv_import.py` — CSV parsing + import orchestration
- `backend/tests/test_csv_import.py` — comprehensive test suite
