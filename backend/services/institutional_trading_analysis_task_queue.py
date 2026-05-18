"""Background task queue for institutional trading analysis using ThreadPoolExecutor."""
import threading
import uuid
import time
import logging
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from backend.services.institutional_trading_analysis_agent import analyze_institutional_trading
from backend.services.trend_prediction_service import TrendPredictionService

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class InstitutionalAnalysisTask:
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: str = "0/0"
    current: int = 0
    total: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class InstitutionalTradingAnalysisTaskQueue:
    """Thread-safe task queue for background institutional trading analysis."""

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, InstitutionalAnalysisTask] = {}
        self._lock = threading.Lock()

    def submit_institutional_analysis_task(
        self,
        symbol: str,
        name: str,
        force: bool = False,
        user_id: str = None,
    ) -> str:
        """Submit a single institutional trading analysis task.

        Args:
            symbol: Stock symbol
            name: Stock name
            force: If False, skip if valid cached result exists today
            user_id: User ID for rate limiting

        Returns:
            task_id: UUID for tracking the task
        """
        task_id = str(uuid.uuid4())

        with self._lock:
            self._tasks[task_id] = InstitutionalAnalysisTask(
                task_id=task_id,
                total=1,
                progress="0/1",
            )

        self._executor.submit(
            self._run_institutional_analysis,
            task_id,
            symbol,
            name,
            force,
            user_id,
        )

        return task_id

    def _run_institutional_analysis(
        self,
        task_id: str,
        symbol: str,
        name: str,
        force: bool = False,
        user_id: str = None,
    ):
        """Run institutional trading analysis in background thread."""
        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.RUNNING

        result = None
        error = None

        # Check cache if not forcing
        if not force:
            # Try to get cached institutional analysis result with source="institutional"
            cached = TrendPredictionService.get_today_prediction(symbol, source="institutional")
            if cached:
                logger.info(f"[Task {task_id}] Using cached result for {name} ({symbol})")
                result = cached

        if result is None:
            try:
                logger.info(f"[Task {task_id}] Analyzing institutional trading for {name} ({symbol})")
                prediction = analyze_institutional_trading(symbol, name)

                # Build extended_analysis with six-dimensional fields
                extended_analysis = None
                if any([
                    prediction.get("宏观产业周期"),
                    prediction.get("板块行业景气"),
                    prediction.get("公司基本面质变"),
                    prediction.get("资金筹码结构"),
                    prediction.get("技术形态量价"),
                    prediction.get("波段操作执行"),
                    prediction.get("综合判断"),
                ]):
                    extended_analysis = {
                        "宏观产业周期": prediction.get("宏观产业周期"),
                        "板块行业景气": prediction.get("板块行业景气"),
                        "公司基本面质变": prediction.get("公司基本面质变"),
                        "资金筹码结构": prediction.get("资金筹码结构"),
                        "技术形态量价": prediction.get("技术形态量价"),
                        "波段操作执行": prediction.get("波段操作执行"),
                        "综合判断": prediction.get("综合判断"),
                    }

                saved = TrendPredictionService.save_prediction(
                    symbol=symbol,
                    name=name,
                    trend_direction=prediction.get("trend_direction", "neutral"),
                    confidence=prediction.get("confidence", 0),
                    summary=prediction.get("summary", ""),
                    extended_analysis=extended_analysis,
                    source="institutional",
                )
                result = saved

                if user_id and result:
                    TrendPredictionService.record_trigger(user_id, symbol)

            except Exception as e:
                error = str(e)
                logger.error(f"[Task {task_id}] Failed to analyze {symbol}: {e}")

        with self._lock:
            task = self._tasks[task_id]
            task.current = 1
            task.progress = "1/1"
            task.status = TaskStatus.COMPLETED if result else TaskStatus.FAILED
            task.results = [result] if result else []
            task.error = error
            task.completed_at = time.time()

        logger.info(f"[Task {task_id}] Completed: {'success' if result else 'failed'} {symbol}")

    def get_task_status(self, task_id: str) -> Optional[InstitutionalAnalysisTask]:
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
_institutional_task_queue: Optional[InstitutionalTradingAnalysisTaskQueue] = None
_init_lock = threading.Lock()


def get_institutional_task_queue() -> InstitutionalTradingAnalysisTaskQueue:
    """Get or create the global institutional analysis task queue instance."""
    global _institutional_task_queue
    if _institutional_task_queue is None:
        with _init_lock:
            if _institutional_task_queue is None:
                _institutional_task_queue = InstitutionalTradingAnalysisTaskQueue(max_workers=3)
    return _institutional_task_queue


def submit_institutional_analysis_task(
    symbol: str,
    name: str,
    force: bool = False,
    user_id: str = None,
) -> str:
    """Submit a single institutional trading analysis task to the global queue."""
    return get_institutional_task_queue().submit_institutional_analysis_task(
        symbol=symbol,
        name=name,
        force=force,
        user_id=user_id,
    )


def get_institutional_task_status(task_id: str) -> Optional[InstitutionalAnalysisTask]:
    """Get status of a task by ID."""
    return get_institutional_task_queue().get_task_status(task_id)
