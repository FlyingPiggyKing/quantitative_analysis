"""Service for trend-prediction run/batch state and persistence.

Run state lives in the `trend_runs` table of `trend_predictions.db`. One row per
run captures the durable facts (date, trigger type, status, batch progress). Batch
job scheduling and per-batch stock lists are kept in memory (see trend_run_queue).
"""
import logging
from datetime import datetime
from typing import Optional, List

from backend.services.trend_prediction_service import get_db_connection, init_trend_runs_db

logger = logging.getLogger(__name__)

BATCH_COUNT = 4

# Statuses considered "active" (a run is in progress).
ACTIVE_STATUSES = ("pending", "running")


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    return {
        "id": row["id"],
        "run_date": row["run_date"],
        "trigger_type": row["trigger_type"],
        "status": row["status"],
        "total_stocks": row["total_stocks"],
        "batch_count": row["batch_count"],
        "current_batch": row["current_batch"],
        "batch_total": row["batch_total"],
        "batch_completed": row["batch_completed"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_run(trigger_type: str, total_stocks: int) -> int:
    """Create a new run row dated for today and return its run_id."""
    init_trend_runs_db()
    conn = get_db_connection()
    try:
        now = datetime.now().isoformat()
        run_date = datetime.now().strftime("%Y-%m-%d")
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO trend_runs
               (run_date, trigger_type, status, total_stocks, batch_count,
                current_batch, batch_total, batch_completed, created_at, updated_at)
               VALUES (?, ?, 'pending', ?, ?, 0, 0, 0, ?, ?)""",
            (run_date, trigger_type, total_stocks, BATCH_COUNT, now, now),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_active_run() -> Optional[dict]:
    """Return the most recent run whose status is pending or running, if any."""
    init_trend_runs_db()
    conn = get_db_connection()
    try:
        placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
        row = conn.cursor().execute(
            f"""SELECT * FROM trend_runs
               WHERE status IN ({placeholders})
               ORDER BY id DESC LIMIT 1""",
            ACTIVE_STATUSES,
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_latest_run() -> Optional[dict]:
    """Return the most recently created run, regardless of status."""
    init_trend_runs_db()
    conn = get_db_connection()
    try:
        row = conn.cursor().execute(
            "SELECT * FROM trend_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_run_for_date(run_date: str) -> Optional[dict]:
    """Return the most recent run for the given run_date (YYYY-MM-DD), if any."""
    init_trend_runs_db()
    conn = get_db_connection()
    try:
        row = conn.cursor().execute(
            "SELECT * FROM trend_runs WHERE run_date = ? ORDER BY id DESC LIMIT 1",
            (run_date,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def update_batch_progress(run_id: int, current_batch: int, batch_total: int, batch_completed: int):
    """Update the current batch number and in-batch progress for a run."""
    init_trend_runs_db()
    conn = get_db_connection()
    try:
        conn.execute(
            """UPDATE trend_runs
               SET current_batch = ?, batch_total = ?, batch_completed = ?, updated_at = ?
               WHERE id = ?""",
            (current_batch, batch_total, batch_completed, datetime.now().isoformat(), run_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_status(run_id: int, status: str):
    """Set the status of a run."""
    init_trend_runs_db()
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE trend_runs SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), run_id),
        )
        conn.commit()
    finally:
        conn.close()


def manual_trigger_available() -> bool:
    """Return True iff the current moment is the normal scheduled-run window.

    "On-schedule" means: a weekday, local time >= 17:00, and no trend_runs row
    exists for today (i.e. the scheduled 17:00 run was missed and a manual run
    would be a like-for-like recovery). Outside this window a manual run is still
    permitted, but the UI asks for explicit confirmation (see get_trigger_info).
    """
    now = datetime.now()
    if now.weekday() >= 5:  # 5=Sat, 6=Sun
        return False
    if now.hour < 17:
        return False
    today = now.strftime("%Y-%m-%d")
    return get_run_for_date(today) is None


def get_trigger_info() -> dict:
    """Describe the manual-trigger state for the admin panel.

    Returns:
        run_active: a run is currently pending/running -> trigger must be blocked.
        on_schedule: now is the normal scheduled-run recovery window.
        off_schedule_reason: human-readable note when a trigger now would be
            outside the normal window (drives the confirmation prompt); None when
            on-schedule or when a run is active.
        disabled_reason: why the trigger is blocked (only when run_active).
    """
    active = get_active_run()
    run_active = active is not None
    on_schedule = manual_trigger_available()

    disabled_reason = None
    if run_active:
        disabled_reason = (
            f"趋势分析正在运行中（第 {active['current_batch']}/{active['batch_count']} 批，"
            f"{active['batch_completed']}/{active['batch_total']}），请等待当前任务完成后再触发。"
        )

    off_schedule_reason = None
    if not run_active and not on_schedule:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if now.weekday() >= 5:
            off_schedule_reason = "当前为周末，市场休市，系统通常不会运行趋势分析。"
        elif now.hour < 17:
            off_schedule_reason = "当前为工作日 17:00 之前，尚未到计划运行时间。"
        elif get_run_for_date(today) is not None:
            off_schedule_reason = "今天已经运行过趋势分析。"
        else:
            off_schedule_reason = "当前不在计划运行时间。"

    return {
        "run_active": run_active,
        "on_schedule": on_schedule,
        "off_schedule_reason": off_schedule_reason,
        "disabled_reason": disabled_reason,
    }


def mark_stale_runs_interrupted() -> int:
    """Mark any pending/running run as interrupted (startup reconciliation).

    Returns the number of rows updated.
    """
    init_trend_runs_db()
    conn = get_db_connection()
    try:
        placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
        cursor = conn.cursor()
        cursor.execute(
            f"""UPDATE trend_runs SET status = 'interrupted', updated_at = ?
               WHERE status IN ({placeholders})""",
            (datetime.now().isoformat(), *ACTIVE_STATUSES),
        )
        conn.commit()
        count = cursor.rowcount
        if count > 0:
            logger.info(f"[TrendRun] Marked {count} stale run(s) as interrupted on startup")
        return count
    finally:
        conn.close()
