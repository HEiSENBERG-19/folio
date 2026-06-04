import logging
import yfinance as yf
import pandas as pd
from datetime import date, datetime, timezone, timedelta
from sqlmodel import Session, select
from typing import Optional

from app.models import Asset, PriceCache

logger = logging.getLogger("uvicorn")


def extract_close_series(df: pd.DataFrame, ticker: str) -> Optional[pd.Series]:
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        # Level 0 is Metric (Close, Open, etc.), Level 1 is Ticker
        if 'Close' in df.columns.levels[0]:
            close_df = df['Close']
            if isinstance(close_df, pd.Series):
                return close_df
            if ticker in close_df.columns:
                return close_df[ticker]
            elif ticker.upper() in close_df.columns:
                return close_df[ticker.upper()]
            else:
                return close_df.iloc[:, 0]
    else:
        if 'Close' in df.columns:
            return df['Close']
        elif 'close' in df.columns:
            return df['close']
    return None


def fetch_and_cache_prices(session: Session, ticker: str, start_date: date, end_date: date) -> None:
    asset = session.exec(select(Asset).where(Asset.ticker == ticker)).first()
    if not asset:
        return

    # Check PriceCache for cached dates in this range
    cached = session.exec(
        select(PriceCache)
        .where(PriceCache.asset_id == asset.id)
        .where(PriceCache.price_date >= start_date)
        .where(PriceCache.price_date <= end_date)
    ).all()

    cached_dates = {item.price_date for item in cached}

    # Identify gaps
    all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    missing_dates = [d for d in all_dates if d not in cached_dates]

    if not missing_dates:
        return

    # Download missing range from yfinance (bounding box)
    missing_start = min(missing_dates)
    missing_end = max(missing_dates)

    # end date in yfinance is exclusive
    start_str = missing_start.strftime("%Y-%m-%d")
    end_str = (missing_end + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        df = yf.download(ticker, start=start_str, end=end_str)
        if not df.empty:
            close_series = extract_close_series(df, ticker)
            if close_series is not None and not close_series.empty:
                for ts, val in close_series.items():
                    d = ts.date()
                    try:
                        price = float(val)
                    except (ValueError, TypeError):
                        continue

                    # Only cache if not already in our set of cached dates
                    if d not in cached_dates:
                        # Extra double check against DB to prevent UniqueConstraint violations
                        existing = session.exec(
                            select(PriceCache)
                            .where(PriceCache.asset_id == asset.id)
                            .where(PriceCache.price_date == d)
                        ).first()
                        if not existing:
                            cache_item = PriceCache(
                                asset_id=asset.id,
                                price_date=d,
                                close_price=price
                            )
                            session.add(cache_item)
                            cached_dates.add(d)
                session.commit()
    except Exception as e:
        logger.warning(f"Error fetching from yfinance for {ticker}: {e}")


def get_current_prices(session: Session, tickers: list[str]) -> dict[str, float]:
    prices = {}
    for ticker in tickers:
        price = None
        try:
            ticker_obj = yf.Ticker(ticker)
            price = ticker_obj.fast_info.get("lastPrice", None)
            if price is None:
                hist = ticker_obj.history(period="1d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.warning(f"Error fetching current price from yfinance for {ticker}: {e}")

        if price is None:
            # Fallback: latest price in PriceCache
            asset = session.exec(select(Asset).where(Asset.ticker == ticker)).first()
            if asset:
                latest = session.exec(
                    select(PriceCache)
                    .where(PriceCache.asset_id == asset.id)
                    .order_by(PriceCache.price_date.desc())
                    .limit(1)
                ).first()
                if latest:
                    price = latest.close_price

        # Fallback default if completely missing
        prices[ticker] = price if price is not None else 0.0
    return prices


def build_price_matrix(session: Session, tickers: list[str], start_date: date, end_date: date) -> dict[str, dict[date, float]]:
    matrix = {}
    # Build complete calendar date range index
    all_dates = pd.date_range(start=start_date, end=end_date, freq="D")

    for ticker in tickers:
        asset = session.exec(select(Asset).where(Asset.ticker == ticker)).first()
        if not asset:
            matrix[ticker] = {d.date(): 0.0 for d in all_dates}
            continue

        # 1. Fetch and cache prices first to ensure we have data
        try:
            fetch_and_cache_prices(session, ticker, start_date, end_date)
        except Exception as e:
            logger.warning(f"Error during fetch_and_cache_prices inside build_price_matrix for {ticker}: {e}")

        # 2. Retrieve all cache entries for this asset in the range
        cached = session.exec(
            select(PriceCache)
            .where(PriceCache.asset_id == asset.id)
            .where(PriceCache.price_date >= start_date)
            .where(PriceCache.price_date <= end_date)
        ).all()

        # If cache is completely empty, fallback to latest overall price
        if not cached:
            latest = session.exec(
                select(PriceCache)
                .where(PriceCache.asset_id == asset.id)
                .order_by(PriceCache.price_date.desc())
                .limit(1)
            ).first()
            fallback_price = latest.close_price if latest else 0.0
            matrix[ticker] = {d.date(): fallback_price for d in all_dates}
            continue

        # 3. Reindex and fill using Pandas
        series_data = {pd.to_datetime(item.price_date): item.close_price for item in cached}
        series = pd.Series(series_data)
        series = series.reindex(all_dates)
        series = series.ffill().bfill()
        series = series.fillna(0.0)

        matrix[ticker] = {d.date(): float(val) for d, val in series.items()}

    return matrix
