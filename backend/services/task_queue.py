"""Background task queue for trend analysis using ThreadPoolExecutor."""
import threading
import uuid
import time
import logging
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from backend.services.stock_trend_agent import analyze_stock_trend
from backend.services.trend_prediction_service import TrendPredictionService
from backend.services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AnalysisTask:
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: str = "0/0"
    current: int = 0
    total: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class TaskQueue:
    """Thread-safe task queue for background analysis."""

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, AnalysisTask] = {}
        self._lock = threading.Lock()

    def submit_analysis_task(self, symbols: List[Dict[str, str]]) -> str:
        """Submit a batch analysis task.

        Args:
            symbols: List of dicts with 'symbol' and 'name' keys

        Returns:
            task_id: UUID for tracking the task
        """
        task_id = str(uuid.uuid4())

        with self._lock:
            self._tasks[task_id] = AnalysisTask(
                task_id=task_id,
                total=len(symbols),
                progress=f"0/{len(symbols)}",
            )

        self._executor.submit(self._run_analysis, task_id, symbols)

        return task_id

    def _run_analysis(self, task_id: str, symbols: List[Dict[str, str]]):
        """Run analysis in background thread."""
        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.RUNNING

        results = []
        failed = 0

        for i, stock in enumerate(symbols):
            symbol = stock["symbol"]
            name = stock["name"]

            try:
                logger.info(f"[Task {task_id}] Analyzing {name} ({symbol})")
                prediction = analyze_stock_trend(symbol, name)

                saved = TrendPredictionService.save_prediction(
                    symbol=symbol,
                    name=name,
                    trend_direction=prediction.get("trend_direction", "neutral"),
                    confidence=prediction.get("confidence", 0),
                    summary=prediction.get("summary", ""),
                )
                results.append(saved)

            except Exception as e:
                failed += 1
                logger.error(f"[Task {task_id}] Failed to analyze {symbol}: {e}")

            with self._lock:
                task = self._tasks[task_id]
                task.current = i + 1
                task.progress = f"{i + 1}/{len(symbols)}"

        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.results = results
            task.completed_at = time.time()
            if failed > 0:
                task.error = f"Failed to analyze {failed} stocks"

        logger.info(f"[Task {task_id}] Completed: {len(results)} analyzed, {failed} failed")

    def get_task_status(self, task_id: str) -> Optional[AnalysisTask]:
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
_task_queue: Optional[TaskQueue] = None
_init_lock = threading.Lock()


def get_task_queue() -> TaskQueue:
    """Get or create the global task queue instance."""
    global _task_queue
    if _task_queue is None:
        with _init_lock:
            if _task_queue is None:
                _task_queue = TaskQueue(max_workers=3)
    return _task_queue


def submit_analysis_task(symbols: List[Dict[str, str]]) -> str:
    """Submit a batch analysis task to the global queue."""
    return get_task_queue().submit_analysis_task(symbols)


def get_task_status(task_id: str) -> Optional[AnalysisTask]:
    """Get status of a task by ID."""
    return get_task_queue().get_task_status(task_id)
