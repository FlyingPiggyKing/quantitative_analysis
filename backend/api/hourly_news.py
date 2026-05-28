"""API endpoint for hourly news summaries."""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter
from backend.services.trend_prediction_service import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hourly_news", tags=["hourly_news"])


def get_hourly_news_from_db(limit: int = 3) -> List[Dict[str, Any]]:
    """Retrieve the most recent hourly news summaries from the database.

    Args:
        limit: Maximum number of hourly summaries to return

    Returns:
        List of hourly news summaries, most recent first
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT hour_timestamp, summary_json, created_at
            FROM hourly_news
            ORDER BY hour_timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            hour_timestamp = row['hour_timestamp']
            summary_json = json.loads(row['summary_json'])
            created_at = row['created_at']

            # Format hour for display (e.g., "2024-05-28-09" -> "09:00")
            hour_display = hour_timestamp[-5:] if len(hour_timestamp) >= 5 else hour_timestamp
            if len(hour_display) == 5:
                hour_display = f"{hour_display[-2:]}:00"

            results.append({
                "hour": hour_display,
                "hour_timestamp": hour_timestamp,
                "top3_news": summary_json.get("top3_news", []),
                "market_impact": summary_json.get("market_impact", {"direction": "中性", "reason": ""}),
                "sector_impact": summary_json.get("sector_impact", []),
                "created_at": datetime.fromtimestamp(created_at).isoformat() if created_at else None,
            })
        return results
    finally:
        conn.close()


@router.get("")
async def get_hourly_news(limit: int = 3) -> List[Dict[str, Any]]:
    """Get the most recent hourly news summaries.

    Returns the last N hours of news summaries (default: 3), sorted by timestamp descending.

    Response format:
    [
        {
            "hour": "11:00",
            "hour_timestamp": "2024-05-28-11",
            "top3_news": [
                {"news_title": "...", "summary": "...", "impact_reason": "..."},
                ...
            ],
            "market_impact": {"direction": "流入偏多/流出偏多/中性", "reason": "..."},
            "sector_impact": [
                {"sector": "板块名称", "reason": "..."},
                ...
            ],
            "created_at": "2024-05-28T12:00:00"
        },
        ...
    ]
    """
    try:
        results = get_hourly_news_from_db(limit=limit)
        logger.info(f"[API] get_hourly_news returning {len(results)} hourly summaries")
        return results
    except Exception as e:
        logger.error(f"[API] Error fetching hourly news: {e}")
        return []


@router.get("/latest")
async def get_latest_hour() -> Dict[str, Any]:
    """Get the most recent hourly news summary."""
    results = get_hourly_news_from_db(limit=1)
    if results:
        return results[0]
    return {
        "hour": None,
        "hour_timestamp": None,
        "top3_news": [],
        "market_impact": {"direction": "中性", "reason": "暂无数据"},
        "sector_impact": [],
        "created_at": None,
    }
