from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.database import get_session
from app.schemas import PortfolioSummary, PortfolioHistory, AllocationSlice
from app.services.portfolio import get_portfolio_summary, get_portfolio_history, get_portfolio_allocation

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
def read_portfolio_summary(session: Session = Depends(get_session)):
    return get_portfolio_summary(session)


@router.get("/history", response_model=PortfolioHistory)
def read_portfolio_history(
    period: str = Query(default="1Y"),
    session: Session = Depends(get_session)
):
    if period not in ("1M", "3M", "6M", "1Y", "ALL"):
        raise HTTPException(status_code=400, detail="Invalid period. Must be one of: 1M, 3M, 6M, 1Y, ALL")
    return get_portfolio_history(session, period)


@router.get("/allocation", response_model=list[AllocationSlice])
def read_portfolio_allocation(session: Session = Depends(get_session)):
    return get_portfolio_allocation(session)
