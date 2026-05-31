"""Dedicated single-worker queue for scheduled/manual trend-prediction runs.

A run analyzes the deduplicated system watchlist split into 4 sequential batches,
one batch every 5 hours. Batch 1 starts at run creation; batches 2-4 are scheduled
as one-off `date` jobs on the shared APScheduler. Execution happens on a dedicated
`ThreadPoolExecutor(max_workers=1)`, independent of the interactive force/batch queue
(`task_queue.py`), guaranteeing one analysis at a time without blocking user queries.

Run state is persisted via `trend_run_service` (the `trend_runs` table). Per-batch
stock lists and per-run cancel flags are kept in memory only (no backfill policy).
"""
import math
import logging
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from backend.services.stock_trend_agent import analyze_stock_trend
from backend.services.trend_prediction_service import TrendPredictionService
from backend.services.admin_service import AdminService
from backend.services import trend_run_service
from backend.services.trend_run_service import BATCH_COUNT

logger = logging.getLogger(__name__)

# Dedicated single-worker executor — separate from task_queue's max_workers=3 pool.
_executor = ThreadPoolExecutor(max_workers=1)

# Re-entrant lock guarding the in-memory registries below.
_lock = threading.RLock()

# run_id -> list of 4 batch lists (each a list of {"symbol","name"} dicts).
_run_batches: Dict[int, List[List[dict]]] = {}

# run_id -> cancel flag. Set cooperatively; checked before each stock/batch.
_cancel_flags: Dict[int, threading.Event] = {}

# Shared APScheduler instance, injected by main.py at startup.
_scheduler = None

# Hours between successive batches.
BATCH_INTERVAL_HOURS = 5


def set_scheduler(scheduler):
    """Inject the shared APScheduler used to schedule batches 2-4."""
    global _scheduler
    _scheduler = scheduler


def _batch_job_id(run_id: int, batch_index: int) -> str:
    """Stable scheduler job id for a run's batch, so it can be removed on cancel."""
    return f"trend_batch_{run_id}_{batch_index}"


def split_into_batches(stocks: List[dict]) -> List[List[dict]]:
    """Divide stocks into exactly BATCH_COUNT batches.

    Batch size is ceil(total / BATCH_COUNT); all stocks are covered exactly once.
    Tolerates fewer stocks than batches (trailing batches may be empty).
    """
    total = len(stocks)
    size = math.ceil(total / BATCH_COUNT) if total > 0 else 0
    batches: List[List[dict]] = []
    for i in range(BATCH_COUNT):
        start = i * size
        batches.append(stocks[start:start + size])
    return batches


def _is_cancelled(run_id: int) -> bool:
    flag = _cancel_flags.get(run_id)
    return flag is not None and flag.is_set()


def _cleanup_run(run_id: int):
    """Drop a run's in-memory batch lists and cancel flag."""
    with _lock:
        _run_batches.pop(run_id, None)
        _cancel_flags.pop(run_id, None)


def run_batch(run_id: int, batch_index: int, stocks: List[dict]):
    """Analyze a batch's stocks sequentially on the dedicated worker.

    Updates persisted progress after each stock. Checks the run's cancel flag
    before each stock and aborts if set. Marks the run completed after the last
    batch (unless cancelled).
    """
    if _is_cancelled(run_id):
        logger.info(f"[TrendRun {run_id}] Batch {batch_index} skipped - run cancelled")
        return

    trend_run_service.set_status(run_id, "running")
    total = len(stocks)
    trend_run_service.update_batch_progress(run_id, batch_index, total, 0)
    logger.info(f"[TrendRun {run_id}] Batch {batch_index}/{BATCH_COUNT} started ({total} stocks)")

    completed = 0
    for stock in stocks:
        if _is_cancelled(run_id):
            logger.info(f"[TrendRun {run_id}] Batch {batch_index} aborted mid-run - cancelled")
            return

        symbol = stock["symbol"]
        name = stock["name"]
        try:
            prediction = analyze_stock_trend(symbol, name)

            extended_analysis = None
            if prediction.get("情绪分析") or prediction.get("技术分析") or prediction.get("趋势判断"):
                extended_analysis = {
                    "情绪分析": prediction.get("情绪分析"),
                    "技术分析": prediction.get("技术分析"),
                    "趋势判断": prediction.get("趋势判断"),
                }

            TrendPredictionService.save_prediction(
                symbol=symbol,
                name=name,
                trend_direction=prediction.get("trend_direction", "neutral"),
                confidence=prediction.get("confidence", 0),
                summary=prediction.get("summary", ""),
                extended_analysis=extended_analysis,
            )
        except Exception as e:
            logger.error(f"[TrendRun {run_id}] Failed to analyze {symbol}: {e}")

        completed += 1
        trend_run_service.update_batch_progress(run_id, batch_index, total, completed)

    logger.info(f"[TrendRun {run_id}] Batch {batch_index}/{BATCH_COUNT} finished ({completed}/{total})")

    if batch_index >= BATCH_COUNT:
        if not _is_cancelled(run_id):
            trend_run_service.set_status(run_id, "completed")
            logger.info(f"[TrendRun {run_id}] Run completed")
        _cleanup_run(run_id)


def _fire_batch(run_id: int, batch_index: int):
    """Scheduler callback for batches 2-4: submit the batch to the worker."""
    with _lock:
        batches = _run_batches.get(run_id)
    if batches is None:
        logger.info(f"[TrendRun {run_id}] Batch {batch_index} job fired but run is gone - skipping")
        return
    if _is_cancelled(run_id):
        logger.info(f"[TrendRun {run_id}] Batch {batch_index} job fired but run cancelled - skipping")
        return
    _executor.submit(run_batch, run_id, batch_index, batches[batch_index - 1])


def _schedule_remaining_batches(run_id: int):
    """Schedule batches 2-4 as one-off date jobs at +5h / +10h / +15h."""
    if _scheduler is None:
        logger.warning(f"[TrendRun {run_id}] No scheduler set - batches 2-4 will not run")
        return
    now = datetime.now()
    for batch_index in range(2, BATCH_COUNT + 1):
        run_date = now + timedelta(hours=BATCH_INTERVAL_HOURS * (batch_index - 1))
        _scheduler.add_job(
            _fire_batch,
            "date",
            run_date=run_date,
            args=[run_id, batch_index],
            id=_batch_job_id(run_id, batch_index),
            name=f"Trend batch {batch_index} for run {run_id}",
            replace_existing=True,
        )
    logger.info(f"[TrendRun {run_id}] Scheduled batches 2-{BATCH_COUNT} at {BATCH_INTERVAL_HOURS}h intervals")


def cancel_run(run_id: int):
    """Cancel a run: set its cancel flag, remove pending batch jobs, mark cancelled."""
    with _lock:
        flag = _cancel_flags.get(run_id)
        if flag:
            flag.set()
    if _scheduler is not None:
        for batch_index in range(2, BATCH_COUNT + 1):
            try:
                _scheduler.remove_job(_batch_job_id(run_id, batch_index))
            except Exception:
                pass  # already ran or never scheduled
    trend_run_service.set_status(run_id, "cancelled")
    _cleanup_run(run_id)
    logger.info(f"[TrendRun {run_id}] Run cancelled")


def start_run(trigger_type: str) -> int:
    """Start a new run: snapshot stocks, cancel any active run, create the record,
    submit batch 1 immediately, and schedule batches 2-4.

    Returns the new run_id.
    """
    raw_stocks = AdminService.get_watchlist_stocks()
    stocks = [{"symbol": s["symbol"], "name": s["name"]} for s in raw_stocks]

    with _lock:
        active = trend_run_service.get_active_run()
        if active:
            logger.info(f"[TrendRun] New {trigger_type} run preempting active run {active['id']}")
            cancel_run(active["id"])

        run_id = trend_run_service.create_run(trigger_type, len(stocks))
        batches = split_into_batches(stocks)
        _run_batches[run_id] = batches
        _cancel_flags[run_id] = threading.Event()

    logger.info(f"[TrendRun {run_id}] Started ({trigger_type}, {len(stocks)} stocks)")
    _executor.submit(run_batch, run_id, 1, batches[0])
    _schedule_remaining_batches(run_id)
    return run_id


def run_scheduled_trend_analysis() -> int:
    """Auto-run entry point invoked by the weekday 17:00 cron job."""
    logger.info("[TrendRun] Scheduled (auto) trend analysis triggered")
    return start_run("auto")
