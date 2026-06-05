from sqlmodel import Session, select
import yfinance as yf
from app.models import Asset, Holding, Account, Transaction, TxType, AssetMetadata
from app.schemas import (
    HoldingDetail,
    PortfolioSummary,
    PortfolioHistoryPoint,
    PortfolioHistory,
    AllocationSlice,
    HoldingInsightDetail,
    CashInsightDetail,
    PortfolioInsights,
)
from app.services import price_service
from datetime import date, datetime, timezone, timedelta


def get_portfolio_summary(session: Session) -> PortfolioSummary:
    assets = session.exec(select(Asset)).all()
    asset_map = {a.id: a for a in assets}

    # Get all holdings with shares > 0
    holdings_db = session.exec(
        select(Holding).where(Holding.total_shares > 0)
    ).all()

    # Group by asset_id (merge holdings across accounts)
    asset_holdings: dict[int, list[Holding]] = {}
    for h in holdings_db:
        asset_holdings.setdefault(h.asset_id, []).append(h)

    # Get active tickers for price fetch
    active_assets = [asset_map[aid] for aid in asset_holdings if aid in asset_map]
    active_tickers = [a.ticker for a in active_assets]

    current_prices = {}
    if active_tickers:
        current_prices = price_service.get_current_prices(session, active_tickers)

    holdings = []
    total_invested = 0.0
    total_market_value = 0.0

    for asset in active_assets:
        h_list = asset_holdings[asset.id]
        total_shares = sum(h.total_shares for h in h_list)
        total_cost = sum(h.total_cost for h in h_list)
        avg_cost_basis = total_cost / total_shares if total_shares > 0 else 0.0

        current_price = current_prices.get(asset.ticker, 0.0)
        market_value = total_shares * current_price
        unrealized_pnl = market_value - total_cost
        unrealized_pnl_pct = (unrealized_pnl / total_cost * 100.0) if total_cost > 0 else 0.0

        # Realized PNL for this asset (sum across accounts)
        realized_pnl = sum(h.realized_pnl for h in h_list)

        holdings.append(HoldingDetail(
            ticker=asset.ticker,
            asset_name=asset.name,
            total_shares=total_shares,
            avg_cost_basis=avg_cost_basis,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            realized_pnl=realized_pnl,
        ))

        total_invested += total_cost
        total_market_value += market_value

    # Total realized PNL
    all_holdings = session.exec(select(Holding)).all()
    total_realized_pnl = sum(h.realized_pnl for h in all_holdings)

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
        holdings=holdings,
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



def fetch_and_cache_metadata(session: Session, asset: Asset) -> AssetMetadata:
    metadata = session.exec(select(AssetMetadata).where(AssetMetadata.asset_id == asset.id)).first()
    now = datetime.now(timezone.utc)
    if metadata:
        fetched_at = metadata.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        if (now - fetched_at).days < 1:
            return metadata

    try:
        ticker_obj = yf.Ticker(asset.ticker)
        info = ticker_obj.info
        
        quote_type = info.get("quoteType", "EQUITY")
        asset_class = "Equity"
        if quote_type == "ETF":
            asset_class = "ETF"
        elif quote_type == "MUTUALFUND":
            asset_class = "Mutual Fund"
        elif quote_type == "CRYPTOCURRENCY":
            asset_class = "Crypto"

        currency = info.get("currency")
        if not currency:
            currency = "INR" if (asset.ticker.endswith(".NS") or asset.ticker.endswith(".BO")) else "USD"

        long_name = info.get("longName", asset.name or asset.ticker)
        if not asset.name and long_name:
            asset.name = long_name
            session.add(asset)

        data = {
            "currency": currency,
            "asset_class": asset_class,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country") or ("India" if currency == "INR" else "United States"),
            "exchange": info.get("exchange"),
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
            "long_name": long_name,
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "trailing_pe": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "price_to_book": info.get("priceToBook"),
            "fetched_at": now
        }

        if not metadata:
            metadata = AssetMetadata(asset_id=asset.id, **data)
        else:
            for k, v in data.items():
                setattr(metadata, k, v)
        
        session.add(metadata)
        session.commit()
        session.refresh(metadata)
    except Exception:
        session.rollback()
        # Create minimal fallback to avoid failure loops
        if not metadata:
            currency = "INR" if (asset.ticker.endswith(".NS") or asset.ticker.endswith(".BO")) else "USD"
            metadata = AssetMetadata(
                asset_id=asset.id,
                currency=currency,
                asset_class="Equity",
                sector="Other",
                country="India" if currency == "INR" else "United States",
                long_name=asset.name or asset.ticker,
                fetched_at=now
            )
            session.add(metadata)
            session.commit()
            session.refresh(metadata)
    return metadata


def get_portfolio_insights(session: Session) -> PortfolioInsights:
    summary = get_portfolio_summary(session)
    
    # Pre-fetch and cache metadata for all active assets
    assets = session.exec(select(Asset)).all()
    asset_map = {a.ticker: a for a in assets}
    asset_id_map = {a.id: a for a in assets}
    
    holdings_insights = []
    price_map = {}
    for h in summary.holdings:
        asset = asset_map.get(h.ticker)
        if asset:
            meta = fetch_and_cache_metadata(session, asset)
            holdings_insights.append(
                HoldingInsightDetail(
                    ticker=h.ticker,
                    asset_name=h.asset_name,
                    total_shares=h.total_shares,
                    market_value_native=h.market_value,  # holding.market_value is native in summary
                    currency=meta.currency,
                    asset_class=meta.asset_class,
                    sector=meta.sector,
                    industry=meta.industry,
                    country=meta.country,
                    exchange=meta.exchange,
                    beta=meta.beta,
                    market_cap=meta.market_cap,
                    fifty_two_week_high=meta.fifty_two_week_high,
                    fifty_two_week_low=meta.fifty_two_week_low,
                    trailing_pe=meta.trailing_pe,
                    dividend_yield=meta.dividend_yield,
                    price_to_book=meta.price_to_book,
                    unrealized_pnl_native=h.unrealized_pnl
                )
            )
            price_map[h.ticker] = h.current_price
            
    # Calculate stock value per account
    holdings_db = session.exec(select(Holding).where(Holding.total_shares > 0)).all()
    account_stock_val: dict[int, float] = {}
    for h in holdings_db:
        asset = asset_id_map.get(h.asset_id)
        if asset:
            price = price_map.get(asset.ticker, 0.0)
            val = h.total_shares * price
            account_stock_val[h.account_id] = account_stock_val.get(h.account_id, 0.0) + val

    # Fetch accounts & cash
    accounts = session.exec(select(Account)).all()
    cash_details = [
        CashInsightDetail(
            account_id=acc.id,
            account_name=acc.name,
            cash_balance_native=acc.cash_balance,
            currency=acc.currency,
            stock_value_native=account_stock_val.get(acc.id, 0.0)
        )
        for acc in accounts
    ]
    
    return PortfolioInsights(
        holdings=holdings_insights,
        cash_balances=cash_details
    )

