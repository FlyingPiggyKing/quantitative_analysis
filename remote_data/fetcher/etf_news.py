"""ETF news fetcher."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from remote_data.config import load_config
from remote_data.fetcher.base import RetryPolicy, per_symbol, with_retry

logger = logging.getLogger(__name__)


def _fetch_one(symbol: str, since: Optional[str]) -> List[Dict[str, Any]]:
    cfg = load_config()
    from yahooquery import Ticker  # type: ignore

    t = Ticker(symbol)
    policy = RetryPolicy(
        max_retries=cfg.yahooquery_max_retries,
        backoff_seconds=cfg.yahooquery_backoff_seconds,
    )

    def _do():
        news = t.news or []
        if not news:
            return []
        return news

    raw_news = with_retry(_do, policy=policy)

    out: List[Dict[str, Any]] = []
    for item in raw_news:
        if not isinstance(item, dict):
            continue
        published = item.get("providerPublishTime")
        published_iso = None
        if published is not None:
            try:
                published_iso = datetime.fromtimestamp(
                    float(published), tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (TypeError, ValueError, OverflowError, OSError):
                published_iso = None
        if since and published_iso and published_iso < since:
            continue
        url = item.get("link")
        if not url:
            continue
        out.append({
            "url": url,
            "symbol": symbol,
            "title": item.get("title"),
            "publisher": item.get("publisher"),
            "published_at": published_iso,
            "summary": item.get("summary"),
        })
    return out


def fetch_news(symbols: List[str], since: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch news for each symbol, flattened. `since` filters by published_at."""
    out: List[Dict[str, Any]] = []
    for s in symbols:
        try:
            out.extend(_fetch_one(s, since))
        except Exception as exc:
            logger.warning("news fetch failed for %s: %s: %s", s, type(exc).__name__, exc)
    return out