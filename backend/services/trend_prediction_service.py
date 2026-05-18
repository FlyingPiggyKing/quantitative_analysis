"""Trend prediction database service using SQLite."""
import logging
import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "trend_predictions.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database, creating the predictions table if it doesn't exist."""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                trend_direction TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                summary TEXT NOT NULL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'trend'
            )
        """)
        # Add extended_analysis column if it doesn't exist (for backward compatibility)
        try:
            conn.execute("""
                ALTER TABLE predictions ADD COLUMN extended_analysis TEXT
            """)
        except Exception:
            pass  # Column already exists
        # Add source column if it doesn't exist (for backward compatibility)
        try:
            conn.execute("""
                ALTER TABLE predictions ADD COLUMN source TEXT DEFAULT 'trend'
            """)
        except Exception:
            pass  # Column already exists
        # Create index for faster lookups
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictions_symbol_analyzed
            ON predictions(symbol, source, analyzed_at DESC)
        """)

        # Create user_analysis_triggers table for rate limiting
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_analysis_triggers (
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, symbol)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_triggers_lookup
            ON user_analysis_triggers(user_id, symbol, triggered_at)
        """)
        conn.commit()
    finally:
        conn.close()


class TrendPredictionService:
    """Service for trend prediction database operations."""

    @staticmethod
    def save_prediction(
        symbol: str,
        name: str,
        trend_direction: str,
        confidence: int,
        summary: str,
        extended_analysis: dict = None,
        source: str = "trend",
    ) -> dict:
        """Save or update a prediction (upsert behavior - one per symbol per day)."""
        import json as json_lib
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            analyzed_at = datetime.now().isoformat()
            extended_json = json_lib.dumps(extended_analysis) if extended_analysis else None

            # Check if prediction exists for today
            today = datetime.now().strftime("%Y-%m-%d")
            existing = cursor.execute(
                "SELECT id FROM predictions WHERE symbol = ? AND date(analyzed_at) = ? AND source = ?",
                (symbol, today, source),
            ).fetchone()

            if existing:
                # Only update if new result is better (higher confidence or non-neutral when existing is neutral)
                # Don't overwrite successful results with failures
                existing_confidence = cursor.execute(
                    "SELECT confidence FROM predictions WHERE symbol = ? AND date(analyzed_at) = ? AND source = ?",
                    (symbol, today, source),
                ).fetchone()[0]

                should_update = True
                if confidence == 0 and existing_confidence > 0:
                    # Don't overwrite a valid result with a failure
                    should_update = False
                    logger.info(f"Skipping update for {symbol} - existing confidence {existing_confidence} is better than new {confidence}")

                if should_update:
                    cursor.execute(
                        """UPDATE predictions
                           SET trend_direction = ?, confidence = ?, summary = ?, analyzed_at = ?, extended_analysis = ?
                           WHERE symbol = ? AND date(analyzed_at) = ? AND source = ?""",
                        (trend_direction, confidence, summary, analyzed_at, extended_json, symbol, today, source),
                    )
            else:
                # Insert new
                cursor.execute(
                    """INSERT INTO predictions (symbol, name, trend_direction, confidence, summary, analyzed_at, extended_analysis, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (symbol, name, trend_direction, confidence, summary, analyzed_at, extended_json, source),
                )

            conn.commit()
            result = {
                "symbol": symbol,
                "name": name,
                "trend_direction": trend_direction,
                "confidence": confidence,
                "summary": summary,
                "analyzed_at": analyzed_at,
            }
            if extended_analysis:
                # Old format fields (for backward compatibility)
                result["情绪分析"] = extended_analysis.get("情绪分析")
                result["技术分析"] = extended_analysis.get("技术分析")
                result["趋势判断"] = extended_analysis.get("趋势判断")
                # Six-dimensional fields
                result["宏观产业周期"] = extended_analysis.get("宏观产业周期")
                result["板块行业景气"] = extended_analysis.get("板块行业景气")
                result["公司基本面质变"] = extended_analysis.get("公司基本面质变")
                result["资金筹码结构"] = extended_analysis.get("资金筹码结构")
                result["技术形态量价"] = extended_analysis.get("技术形态量价")
                result["波段操作执行"] = extended_analysis.get("波段操作执行")
                result["综合判断"] = extended_analysis.get("综合判断")
            return result
        finally:
            conn.close()

    @staticmethod
    def get_latest_prediction(symbol: str, source: str = "trend") -> Optional[dict]:
        """Get the latest prediction for a specific stock symbol and source."""
        import json as json_lib
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                """SELECT symbol, name, trend_direction, confidence, summary, analyzed_at, extended_analysis
                   FROM predictions
                   WHERE symbol = ? AND source = ?
                   ORDER BY analyzed_at DESC
                   LIMIT 1""",
                (symbol, source),
            ).fetchone()

            if row:
                result = {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "trend_direction": row["trend_direction"],
                    "confidence": row["confidence"],
                    "summary": row["summary"],
                    "analyzed_at": row["analyzed_at"],
                }
                if row["extended_analysis"]:
                    try:
                        extended = json_lib.loads(row["extended_analysis"])
                        # Old format fields (for regular stock analysis)
                        result["情绪分析"] = extended.get("情绪分析")
                        result["技术分析"] = extended.get("技术分析")
                        result["趋势判断"] = extended.get("趋势判断")
                        # Six-dimensional fields (for institutional analysis)
                        result["宏观产业周期"] = extended.get("宏观产业周期")
                        result["板块行业景气"] = extended.get("板块行业景气")
                        result["公司基本面质变"] = extended.get("公司基本面质变")
                        result["资金筹码结构"] = extended.get("资金筹码结构")
                        result["技术形态量价"] = extended.get("技术形态量价")
                        result["波段操作执行"] = extended.get("波段操作执行")
                        result["综合判断"] = extended.get("综合判断")
                    except (json_lib.JSONDecodeError, ValueError):
                        pass
                return result
            return None
        finally:
            conn.close()

    @staticmethod
    def get_all_latest_predictions() -> List[dict]:
        """Get the latest prediction for each stock that has been analyzed."""
        import json as json_lib
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Get latest prediction for each symbol
            rows = cursor.execute(
                """SELECT p.symbol, p.name, p.trend_direction, p.confidence, p.summary, p.analyzed_at, p.extended_analysis
                   FROM predictions p
                   INNER JOIN (
                       SELECT symbol, MAX(analyzed_at) as max_analyzed
                       FROM predictions
                       GROUP BY symbol
                   ) latest ON p.symbol = latest.symbol AND p.analyzed_at = latest.max_analyzed
                   ORDER BY p.analyzed_at DESC""",
            ).fetchall()

            results = []
            for row in rows:
                result = {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "trend_direction": row["trend_direction"],
                    "confidence": row["confidence"],
                    "summary": row["summary"],
                    "analyzed_at": row["analyzed_at"],
                }
                if row["extended_analysis"]:
                    try:
                        extended = json_lib.loads(row["extended_analysis"])
                        # Old format fields (for regular stock analysis)
                        result["情绪分析"] = extended.get("情绪分析")
                        result["技术分析"] = extended.get("技术分析")
                        result["趋势判断"] = extended.get("趋势判断")
                        # Six-dimensional fields (for institutional analysis)
                        result["宏观产业周期"] = extended.get("宏观产业周期")
                        result["板块行业景气"] = extended.get("板块行业景气")
                        result["公司基本面质变"] = extended.get("公司基本面质变")
                        result["资金筹码结构"] = extended.get("资金筹码结构")
                        result["技术形态量价"] = extended.get("技术形态量价")
                        result["波段操作执行"] = extended.get("波段操作执行")
                        result["综合判断"] = extended.get("综合判断")
                    except (json_lib.JSONDecodeError, ValueError):
                        pass
                results.append(result)
            return results
        finally:
            conn.close()

    @staticmethod
    def get_today_prediction(symbol: str, source: str = "trend") -> Optional[dict]:
        """Get today's cached prediction for a symbol and source if it exists and is valid (confidence > 0).

        Returns None if no prediction exists for today or if the existing prediction
        has confidence = 0 (failed analysis).
        """
        import json as json_lib
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            row = cursor.execute(
                """SELECT symbol, name, trend_direction, confidence, summary, analyzed_at, extended_analysis
                   FROM predictions
                   WHERE symbol = ? AND date(analyzed_at) = ? AND source = ? AND confidence > 0
                   ORDER BY analyzed_at DESC
                   LIMIT 1""",
                (symbol, today, source),
            ).fetchone()

            if row:
                result = {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "trend_direction": row["trend_direction"],
                    "confidence": row["confidence"],
                    "summary": row["summary"],
                    "analyzed_at": row["analyzed_at"],
                }
                if row["extended_analysis"]:
                    try:
                        extended = json_lib.loads(row["extended_analysis"])
                        result["宏观产业周期"] = extended.get("宏观产业周期")
                        result["板块行业景气"] = extended.get("板块行业景气")
                        result["公司基本面质变"] = extended.get("公司基本面质变")
                        result["资金筹码结构"] = extended.get("资金筹码结构")
                        result["技术形态量价"] = extended.get("技术形态量价")
                        result["波段操作执行"] = extended.get("波段操作执行")
                        result["综合判断"] = extended.get("综合判断")
                    except (json_lib.JSONDecodeError, ValueError):
                        pass
                return result
            return None
        finally:
            conn.close()

    @staticmethod
    def get_predictions_by_symbol(symbol: str, limit: int = 7) -> List[dict]:
        """Get recent predictions for a stock (for history/trends)."""
        import json as json_lib
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute(
                """SELECT symbol, name, trend_direction, confidence, summary, analyzed_at, extended_analysis
                   FROM predictions
                   WHERE symbol = ?
                   ORDER BY analyzed_at DESC
                   LIMIT ?""",
                (symbol, limit),
            ).fetchall()

            results = []
            for row in rows:
                result = {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "trend_direction": row["trend_direction"],
                    "confidence": row["confidence"],
                    "summary": row["summary"],
                    "analyzed_at": row["analyzed_at"],
                }
                if row["extended_analysis"]:
                    try:
                        extended = json_lib.loads(row["extended_analysis"])
                        # Old format fields (for regular stock analysis)
                        result["情绪分析"] = extended.get("情绪分析")
                        result["技术分析"] = extended.get("技术分析")
                        result["趋势判断"] = extended.get("趋势判断")
                        # Six-dimensional fields (for institutional analysis)
                        result["宏观产业周期"] = extended.get("宏观产业周期")
                        result["板块行业景气"] = extended.get("板块行业景气")
                        result["公司基本面质变"] = extended.get("公司基本面质变")
                        result["资金筹码结构"] = extended.get("资金筹码结构")
                        result["技术形态量价"] = extended.get("技术形态量价")
                        result["波段操作执行"] = extended.get("波段操作执行")
                        result["综合判断"] = extended.get("综合判断")
                    except (json_lib.JSONDecodeError, ValueError):
                        pass
                results.append(result)
            return results
        finally:
            conn.close()

    @staticmethod
    def check_rate_limit(user_id: str, symbol: str) -> bool:
        """Check if user is rate limited for force analysis on a symbol.

        Returns True if rate limited (within 1 hour of last trigger), False otherwise.
        """
        from datetime import timedelta
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
            row = cursor.execute(
                """SELECT triggered_at FROM user_analysis_triggers
                   WHERE user_id = ? AND symbol = ? AND triggered_at >= ?
                   ORDER BY triggered_at DESC LIMIT 1""",
                (user_id, symbol, cutoff),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    @staticmethod
    def record_trigger(user_id: str, symbol: str):
        """Record a force analysis trigger for rate limiting.

        Uses upsert behavior - updates triggered_at if record exists.
        """
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO user_analysis_triggers (user_id, symbol, triggered_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, symbol) DO UPDATE SET triggered_at = excluded.triggered_at""",
                (user_id, symbol, datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_rate_limit_remaining_seconds(user_id: str, symbol: str) -> int:
        """Get seconds until rate limit expires for user/symbol combo.

        Returns 0 if no active cooldown.
        """
        from datetime import timedelta
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(hours=1)).isoformat()
            row = cursor.execute(
                """SELECT triggered_at FROM user_analysis_triggers
                   WHERE user_id = ? AND symbol = ? AND triggered_at >= ?
                   ORDER BY triggered_at DESC LIMIT 1""",
                (user_id, symbol, cutoff),
            ).fetchone()
            if row is None:
                return 0
            last_trigger = datetime.fromisoformat(row["triggered_at"])
            expires_at = last_trigger + timedelta(hours=1)
            remaining = (expires_at - datetime.now()).total_seconds()
            return max(0, int(remaining))
        finally:
            conn.close()
