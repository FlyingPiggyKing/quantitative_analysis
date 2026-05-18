"""Institutional Trading Analysis API routes."""
import logging
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel

from backend.services.institutional_trading_analysis_agent import analyze_institutional_trading
from backend.services.trend_prediction_service import TrendPredictionService
from backend.services.watchlist_service import WatchlistService
from backend.services.institutional_trading_analysis_task_queue import (
    submit_institutional_analysis_task,
    get_institutional_task_status,
    TaskStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/institutional-analysis", tags=["institutional-analysis"])


class PredictionResponse(BaseModel):
    symbol: str
    name: str
    trend_direction: str
    confidence: int
    summary: str
    analyzed_at: str
    is_fallback: bool = False
    # Old format fields (for regular stock analysis)
    情绪分析: Optional[dict] = None
    技术分析: Optional[dict] = None
    趋势判断: Optional[dict] = None
    机构分析: Optional[dict] = None
    # Six-dimensional fields (for institutional analysis)
    宏观产业周期: Optional[dict] = None
    板块行业景气: Optional[dict] = None
    公司基本面质变: Optional[dict] = None
    资金筹码结构: Optional[dict] = None
    技术形态量价: Optional[dict] = None
    波段操作执行: Optional[dict] = None
    综合判断: Optional[dict] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: str
    current: int
    total: int
    results: Optional[list] = None
    error: Optional[str] = None


class ForceAnalysisResponse(BaseModel):
    task_id: str
    status: str


def _get_stock_name(symbol: str) -> str:
    """Look up stock name from watchlist or stock info API."""
    name = symbol
    try:
        watchlist_result = WatchlistService.get_watchlist(page=1, page_size=100)
        for stock in watchlist_result.get("items", []):
            if stock["symbol"] == symbol:
                name = stock["name"]
                break
    except Exception:
        pass

    if name == symbol:
        try:
            from backend.services.akshare_service import AShareService
            stock_info = AShareService.get_stock_info(symbol)
            if stock_info and "name" in stock_info and stock_info["name"]:
                name = stock_info["name"]
        except Exception:
            pass

    return name


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_endpoint(task_id: str):
    """Get the status of an institutional analysis task."""
    task = get_institutional_task_status(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        progress=task.progress,
        current=task.current,
        total=task.total,
        results=task.results if task.status == TaskStatus.COMPLETED else None,
        error=task.error,
    )


@router.post("/{symbol}/force-async", response_model=ForceAnalysisResponse)
async def force_analysis_async(
    symbol: str,
    authorization: Optional[str] = Header(None),
):
    """Submit institutional analysis for a single stock to background task queue.

    Returns immediately with a task_id. Poll /api/institutional-analysis/task/{task_id}
    for status and results.
    Rate limit: only one analysis per user per stock per hour.
    Requires authentication.
    """
    from backend.api.auth import get_current_user

    current_user = get_current_user(authorization)
    user_id = current_user.get("user_id")

    # Check rate limit
    if TrendPredictionService.check_rate_limit(user_id, symbol):
        remaining = TrendPredictionService.get_rate_limit_remaining_seconds(user_id, symbol)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": remaining,
            },
            headers={"retry_after": str(remaining)},
        )

    name = _get_stock_name(symbol)

    # Submit to background queue
    task_id = submit_institutional_analysis_task(
        symbol,
        name,
        force=True,
        user_id=user_id,
    )

    return ForceAnalysisResponse(
        task_id=task_id,
        status="pending",
    )


@router.get("/{symbol}", response_model=PredictionResponse)
async def get_prediction(symbol: str):
    """Get the latest institutional analysis prediction for a stock.

    Returns cached result if available, otherwise returns 404.
    """
    cached = TrendPredictionService.get_today_prediction(symbol, source="institutional")
    if cached:
        cached["is_fallback"] = False
        return cached

    latest = TrendPredictionService.get_latest_prediction(symbol, source="institutional")
    if latest:
        latest["is_fallback"] = True
        return latest

    raise HTTPException(
        status_code=404,
        detail="No prediction available. Please use force-async to trigger analysis.",
    )
