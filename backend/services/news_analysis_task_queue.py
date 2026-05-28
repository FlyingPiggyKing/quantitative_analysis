"""Background task queue for hourly news analysis using ThreadPoolExecutor."""
import threading
import uuid
import time
import logging
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

import tushare as ts
import pandas as pd

from backend.services.news_analysis_agent import analyze_hourly_news
from backend.services.trend_prediction_service import init_hourly_news_db, cleanup_old_hourly_news, get_db_connection

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class NewsAnalysisTask:
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: str = "0/3"
    current: int = 0
    total: int = 3
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class NewsAnalysisTaskQueue:
    """Thread-safe task queue for background hourly news analysis."""

    def __init__(self, max_workers: int = 1):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, NewsAnalysisTask] = {}
        self._lock = threading.Lock()

    def submit_news_analysis_task(self) -> str:
        """Submit a hourly news analysis task.

        Returns:
            task_id: UUID for tracking the task
        """
        task_id = str(uuid.uuid4())

        with self._lock:
            self._tasks[task_id] = NewsAnalysisTask(
                task_id=task_id,
                total=3,
                progress="0/3",
            )

        self._executor.submit(
            self._run_news_analysis,
            task_id,
        )

        return task_id

    def _fetch_tushare_news(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Fetch news from Tushare for the past N minutes.

        Args:
            minutes: Number of minutes to look back

        Returns:
            List of news items with datetime, title, content, source, relevance
        """
        try:
            pro = ts.pro_api()

            # Tushare news API returns news with datetime
            # The news API returns recent news from various sources
            df = pro.news(src='sina')

            if df is None or df.empty:
                logger.warning("[NewsTask] No news returned from Tushare")
                return []

            # Calculate cutoff time
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(minutes=minutes)

            results = []
            for _, row in df.iterrows():
                try:
                    # Parse datetime - Tushare news returns datetime as string
                    news_dt = row.get('datetime')
                    if news_dt is None:
                        continue

                    # Handle datetime parsing - Tushare returns as string like '2024-05-28 09:30:00'
                    if isinstance(news_dt, str):
                        dt = datetime.strptime(news_dt, '%Y-%m-%d %H:%M:%S')
                    else:
                        dt = news_dt

                    if dt < cutoff:
                        continue

                    # Get relevance score (default to 0.5 if not available)
                    relevance = float(row.get('rel', 0.5)) / 100.0 if row.get('rel') else 0.5

                    results.append({
                        "datetime": dt.strftime('%Y-%m-%d %H:%M:%S'),
                        "title": str(row.get('title', '')),
                        "content": str(row.get('content', ''))[:500],  # Truncate content
                        "source": str(row.get('src', 'unknown')),
                        "relevance": relevance,
                    })
                except Exception as e:
                    logger.warning(f"[NewsTask] Error parsing news row: {e}")
                    continue

            logger.info(f"[NewsTask] Fetched {len(results)} news items from Tushare")
            return results

        except Exception as e:
            logger.error(f"[NewsTask] Error fetching Tushare news: {e}")
            return []

    def _save_hourly_news(self, hour_timestamp: str, summary_json: Dict[str, Any]) -> bool:
        """Save hourly news summary to database.

        Args:
            hour_timestamp: Hour timestamp string (e.g., "2024-05-28-09")
            summary_json: Summary data as JSON-serializable dict

        Returns:
            True if saved successfully, False otherwise
        """
        import json
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO hourly_news (hour_timestamp, summary_json, created_at) VALUES (?, ?, ?)",
                (hour_timestamp, json.dumps(summary_json, ensure_ascii=False), time.time())
            )
            conn.commit()
            conn.close()
            logger.info(f"[NewsTask] Saved hourly news for {hour_timestamp}")
            return True
        except Exception as e:
            logger.error(f"[NewsTask] Error saving hourly news: {e}")
            return False

    def _run_news_analysis(self, task_id: str):
        """Run hourly news analysis in background thread."""
        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.RUNNING

        result = None
        error = None

        try:
            logger.info(f"[Task {task_id}] Starting hourly news analysis")

            # Step 1: Fetch news from Tushare
            with self._lock:
                task.current = 1
                task.progress = "1/3"

            news_list = self._fetch_tushare_news(minutes=60)
            logger.info(f"[Task {task_id}] Fetched {len(news_list)} news items")

            if not news_list:
                error = "No news available"
                logger.warning(f"[Task {task_id}] {error}")

            # Step 2: Analyze news with AI agent
            with self._lock:
                task.current = 2
                task.progress = "2/3"

            if news_list:
                analysis = analyze_hourly_news(news_list)
                result = analysis
                logger.info(f"[Task {task_id}] Analysis complete: {analysis.get('market_impact', {})}")

                # Step 3: Save to database
                with self._lock:
                    task.current = 3
                    task.progress = "3/3"

                hour_timestamp = time.strftime('%Y-%m-%d-%H')
                saved = self._save_hourly_news(hour_timestamp, analysis)
                if saved:
                    logger.info(f"[Task {task_id}] Saved to database")
                else:
                    logger.warning(f"[Task {task_id}] Failed to save to database")

        except Exception as e:
            error = str(e)
            logger.error(f"[Task {task_id}] Failed to analyze news: {e}")

        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.COMPLETED if result else TaskStatus.FAILED
            task.result = result
            task.error = error
            task.completed_at = time.time()

        logger.info(f"[Task {task_id}] Completed: {'success' if result else 'failed'}")

    def get_task_status(self, task_id: str) -> Optional[NewsAnalysisTask]:
        """Get current task status."""
        with self._lock:
            return self._tasks.get(task_id)

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        with self._lock:
            to_remove = [
                tid for tid, task in self._tasks.items()
                if task.completed_at and task.completed_at < cutoff
            ]
            for tid in to_remove:
                del self._tasks[tid]


# Global task queue instance
_news_task_queue: Optional[NewsAnalysisTaskQueue] = None
_init_lock = threading.Lock()


def get_news_task_queue() -> NewsAnalysisTaskQueue:
    """Get or create the global news analysis task queue instance."""
    global _news_task_queue
    if _news_task_queue is None:
        with _init_lock:
            if _news_task_queue is None:
                _news_task_queue = NewsAnalysisTaskQueue(max_workers=1)
    return _news_task_queue


def submit_news_analysis_task() -> str:
    """Submit a hourly news analysis task to the global queue."""
    return get_news_task_queue().submit_news_analysis_task()


def get_news_task_status(task_id: str) -> Optional[NewsAnalysisTask]:
    """Get status of a task by ID."""
    return get_news_task_queue().get_task_status(task_id)


def run_hourly_news_analysis() -> str:
    """Convenience function to run hourly news analysis and return task_id.

    This is the function that should be called by the scheduler.
    """
    return submit_news_analysis_task()
