"""Watchlist API routes with authentication."""
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.services.watchlist_service import WatchlistService
from backend.api.auth import get_current_user

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddStockRequest(BaseModel):
    symbol: str
    name: str
    market: str = "A"  # Default to A-share


@router.get("")
async def get_watchlist(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=30),
    market: Optional[str] = Query(default=None, description="Filter by market: 'A' for A-share, 'US' for US stocks"),
    current_user: dict = Depends(get_current_user)
):
    """Get paginated watchlist for authenticated user."""
    return WatchlistService.get_watchlist(
        user_id=current_user["user_id"],
        page=page,
        page_size=page_size,
        market=market
    )


@router.post("")
async def add_to_watchlist(
    request: AddStockRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a stock to the authenticated user's watchlist."""
    result = WatchlistService.add_stock(
        current_user["user_id"],
        request.symbol,
        request.name,
        request.market
    )
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.delete("/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a stock from the authenticated user's watchlist."""
    removed = WatchlistService.remove_stock(current_user["user_id"], symbol)
    if not removed:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    return {"success": True}


@router.get("/{symbol}")
async def check_watchlist(
    symbol: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if a stock is in the authenticated user's watchlist."""
    result = WatchlistService.check_stock(current_user["user_id"], symbol)
    if result is None:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    return result
