"""Watchlist API routes."""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from backend.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddStockRequest(BaseModel):
    symbol: str
    name: str


@router.get("")
async def get_watchlist(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=30)
):
    """Get paginated watchlist."""
    return WatchlistService.get_watchlist(page=page, page_size=page_size)


@router.post("")
async def add_to_watchlist(request: AddStockRequest):
    """Add a stock to the watchlist."""
    result = WatchlistService.add_stock(request.symbol, request.name)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.delete("/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove a stock from the watchlist."""
    removed = WatchlistService.remove_stock(symbol)
    if not removed:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    return {"success": True}


@router.get("/{symbol}")
async def check_watchlist(symbol: str):
    """Check if a stock is in the watchlist."""
    result = WatchlistService.check_stock(symbol)
    if result is None:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    return result
