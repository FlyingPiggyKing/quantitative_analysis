"""Trend prediction API routes."""
import time
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from backend.services.trend_prediction_service import TrendPredictionService
from backend.services.watchlist_service import WatchlistService
from backend.services.stock_trend_agent import analyze_stock_trend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trend-predictions", tags=["trend-predictions"])


class PredictionResponse(BaseModel):
    symbol: str
    name: str
    trend_direction: str
    confidence: int
    summary: str
    analyzed_at: str


class BatchAnalysisResponse(BaseModel):
    analyzed: int
    failed: int
    results: List[PredictionResponse]


@router.get("", response_model=List[PredictionResponse])
async def get_all_predictions():
    """Get all latest predictions for analyzed stocks."""
    predictions = TrendPredictionService.get_all_latest_predictions()
    return predictions


@router.get("/{symbol}", response_model=PredictionResponse)
async def get_prediction(symbol: str):
    """Get the latest prediction for a specific stock."""
    prediction = TrendPredictionService.get_latest_prediction(symbol)
    if prediction is None:
        raise HTTPException(status_code=404, detail="No prediction found for this stock")
    return prediction


@router.post("/batch", response_model=BatchAnalysisResponse)
async def batch_analyze():
    """Run trend analysis for all stocks in the watchlist."""
    logger.info("Starting batch analysis for watchlist")
    # Get all stocks from watchlist
    watchlist_result = WatchlistService.get_watchlist(page=1, page_size=100)
    stocks = watchlist_result.get("items", [])
    logger.info(f"Found {len(stocks)} stocks in watchlist")

    if not stocks:
        return BatchAnalysisResponse(analyzed=0, failed=0, results=[])

    results = []
    failed = 0

    for stock in stocks:
        symbol = stock["symbol"]
        name = stock["name"]
        logger.info(f"Analyzing stock: {name} ({symbol})")

        try:
            # Run analysis
            logger.info(f"Calling analyze_stock_trend for {symbol}...")
            prediction = analyze_stock_trend(symbol, name)
            logger.info(f"Analysis complete for {symbol}: {prediction.get('trend_direction')}")

            # Save prediction
            saved = TrendPredictionService.save_prediction(
                symbol=symbol,
                name=name,
                trend_direction=prediction.get("trend_direction", "neutral"),
                confidence=prediction.get("confidence", 0),
                summary=prediction.get("summary", ""),
            )
            results.append(saved)
            logger.info(f"Saved prediction for {symbol}")

            # Small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            failed += 1
            logger.error(f"Failed to analyze {symbol}: {e}")

    return BatchAnalysisResponse(
        analyzed=len(results),
        failed=failed,
        results=results,
    )
