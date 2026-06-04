from sqlmodel import Session, select
from app.models import Asset, FIFOLot, LotClosure, Account, Transaction, TxType
from app.schemas import HoldingDetail, PortfolioSummary, PortfolioHistoryPoint, PortfolioHistory, AllocationSlice
from app.services import price_service
from datetime import date, datetime, timezone, timedelta


def get_portfolio_summary(session: Session) -> PortfolioSummary:
    # 1. Fetch all assets
    assets = session.exec(select(Asset)).all()

    # 2. Get all open lots (where quantity_remaining > 0)
    open_lots = session.exec(
        select(FIFOLot)
        .where(FIFOLot.quantity_remaining > 0)
    ).all()

    # Group open lots by asset_id
    lots_by_asset = {}
    for lot in open_lots:
        lots_by_asset.setdefault(lot.asset_id, []).append(lot)

    # Get active tickers
    active_tickers = []
    active_assets = []
    for asset in assets:
        if asset.id in lots_by_asset:
            active_tickers.append(asset.ticker)
            active_assets.append(asset)

    # 3. Fetch current prices
    current_prices = {}
    if active_tickers:
        current_prices = price_service.get_current_prices(session, active_tickers)

    holdings = []
    total_invested = 0.0
    total_market_value = 0.0

    for asset in active_assets:
        lots = lots_by_asset[asset.id]
        total_shares = sum(lot.quantity_remaining for lot in lots)
        total_cost = sum(lot.quantity_remaining * lot.cost_per_unit for lot in lots)
        avg_cost_basis = total_cost / total_shares if total_shares > 0 else 0.0

        current_price = current_prices.get(asset.ticker, 0.0)
        market_value = total_shares * current_price
        unrealized_pnl = market_value - total_cost
        unrealized_pnl_pct = (unrealized_pnl / total_cost * 100.0) if total_cost > 0 else 0.0

        # Realized PNL for this asset
        closures = session.exec(
            select(LotClosure)
            .join(FIFOLot)
            .where(FIFOLot.asset_id == asset.id)
        ).all()
        realized_pnl = sum(c.realized_pnl for c in closures)

        holdings.append(
            HoldingDetail(
                ticker=asset.ticker,
                asset_name=asset.name,
                total_shares=total_shares,
                avg_cost_basis=avg_cost_basis,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                realized_pnl=realized_pnl
            )
        )

        total_invested += total_cost
        total_market_value += market_value

    # Total realized PNL across all closed lots in the system
    all_closures = session.exec(select(LotClosure)).all()
    total_realized_pnl = sum(c.realized_pnl for c in all_closures)

    # Total cash
    accounts = session.exec(select(Account)).all()
    total_cash = sum(acc.cash_balance for acc in accounts)

    total_unrealized_pnl = total_market_value - total_invested
    net_portfolio_value = total_market_value + total_cash

    return PortfolioSummary(
        total_invested=total_invested,
        total_market_value=total_market_value,
        total_cash=total_cash,
        total_realized_pnl=total_realized_pnl,
        total_unrealized_pnl=total_unrealized_pnl,
        net_portfolio_value=net_portfolio_value,
        holdings=holdings
    )


def get_portfolio_history(session: Session, period: str) -> PortfolioHistory:
    end_date = datetime.now(timezone.utc).date()
    if period == "1M":
        start_date = end_date - timedelta(days=30)
    elif period == "3M":
        start_date = end_date - timedelta(days=90)
    elif period == "6M":
        start_date = end_date - timedelta(days=180)
    elif period == "1Y":
        start_date = end_date - timedelta(days=365)
    elif period == "ALL":
        first_tx = session.exec(
            select(Transaction).order_by(Transaction.executed_at.asc()).limit(1)
        ).first()
        if first_tx:
            start_date = first_tx.executed_at.date()
        else:
            start_date = end_date - timedelta(days=365)
    else:
        # Default to 1Y
        start_date = end_date - timedelta(days=365)

    # Ensure start_date is not in the future relative to end_date
    start_date = min(start_date, end_date)

    # Fetch all transactions up to end_date to compute running state
    txs = session.exec(
        select(Transaction)
        .order_by(Transaction.executed_at.asc(), Transaction.id.asc())
    ).all()

    # Asset ticker mapping
    assets = session.exec(select(Asset)).all()
    asset_map = {a.id: a.ticker for a in assets}

    # Set earliest date to start tracking from
    if txs:
        earliest_date = min(txs[0].executed_at.date(), start_date)
    else:
        earliest_date = start_date

    all_days = [earliest_date + timedelta(days=i) for i in range((end_date - earliest_date).days + 1)]

    daily_snapshots = {}
    running_shares = {a.ticker: 0.0 for a in assets}
    running_cash = 0.0

    tx_idx = 0
    num_txs = len(txs)

    for d in all_days:
        while tx_idx < num_txs and txs[tx_idx].executed_at.date() <= d:
            tx = txs[tx_idx]
            ticker = asset_map.get(tx.asset_id) if tx.asset_id else None

            if tx.tx_type == TxType.DEPOSIT:
                running_cash += tx.total_amount
            elif tx.tx_type == TxType.WITHDRAWAL:
                running_cash -= tx.total_amount
            elif tx.tx_type == TxType.FEE:
                running_cash -= tx.total_amount
            elif tx.tx_type == TxType.BUY:
                running_cash -= tx.total_amount
                if ticker:
                    running_shares[ticker] = running_shares.get(ticker, 0.0) + tx.quantity
            elif tx.tx_type == TxType.SELL:
                running_cash += tx.total_amount
                if ticker:
                    running_shares[ticker] = running_shares.get(ticker, 0.0) - tx.quantity

            tx_idx += 1

        daily_snapshots[d] = {
            "shares": {t: qty for t, qty in running_shares.items() if qty > 0.0},
            "cash": running_cash
        }

    # Find tickers that were active during the requested window [start_date, end_date]
    active_tickers = set()
    target_days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    for d in target_days:
        snapshot = daily_snapshots.get(d, {"shares": {}, "cash": 0.0})
        active_tickers.update(snapshot["shares"].keys())

    # Build price matrix for target period
    price_matrix = {}
    if active_tickers:
        price_matrix = price_service.build_price_matrix(session, list(active_tickers), start_date, end_date)

    data_points = []
    for d in target_days:
        snapshot = daily_snapshots.get(d, {"shares": {}, "cash": 0.0})
        cash = snapshot["cash"]
        portfolio_value = 0.0
        for ticker, qty in snapshot["shares"].items():
            price = price_matrix.get(ticker, {}).get(d, 0.0)
            portfolio_value += qty * price

        data_points.append(
            PortfolioHistoryPoint(
                date=d,
                portfolio_value=portfolio_value,
                cash_balance=cash,
                total_value=portfolio_value + cash
            )
        )

    return PortfolioHistory(
        period=period,
        data_points=data_points
    )


def get_portfolio_allocation(session: Session) -> list[AllocationSlice]:
    summary = get_portfolio_summary(session)
    total_val = summary.total_market_value

    slices = []
    for h in summary.holdings:
        pct = (h.market_value / total_val * 100.0) if total_val > 0.0 else 0.0
        slices.append(
            AllocationSlice(
                ticker=h.ticker,
                market_value=h.market_value,
                percentage=pct
            )
        )
    return slices
