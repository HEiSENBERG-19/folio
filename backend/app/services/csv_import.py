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

    headers = {h.strip() for h in reader.fieldnames if h}
    required = {'Account', 'Ticker', 'Action', 'Quantity', 'Price', 'Date'}
    missing = required - headers
    if missing:
        errors.append(RowError(row=0, message=f"Missing required columns: {', '.join(sorted(missing))}"))
        return rows, errors

    for row_num, row in enumerate(reader, start=2):  # Row 1 = header
        try:
            # Clean keys and values
            row = {k.strip(): (v.strip() if v else '') for k, v in row.items() if k is not None}

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
