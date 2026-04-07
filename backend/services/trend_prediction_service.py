"""Trend prediction database service using SQLite."""
import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

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
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create index for faster lookups
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictions_symbol_analyzed
            ON predictions(symbol, analyzed_at DESC)
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
    ) -> dict:
        """Save or update a prediction (upsert behavior - one per symbol per day)."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            analyzed_at = datetime.now().isoformat()

            # Check if prediction exists for today
            today = datetime.now().strftime("%Y-%m-%d")
            existing = cursor.execute(
                "SELECT id FROM predictions WHERE symbol = ? AND date(analyzed_at) = ?",
                (symbol, today),
            ).fetchone()

            if existing:
                # Update existing
                cursor.execute(
                    """UPDATE predictions
                       SET trend_direction = ?, confidence = ?, summary = ?, analyzed_at = ?
                       WHERE symbol = ? AND date(analyzed_at) = ?""",
                    (trend_direction, confidence, summary, analyzed_at, symbol, today),
                )
            else:
                # Insert new
                cursor.execute(
                    """INSERT INTO predictions (symbol, name, trend_direction, confidence, summary, analyzed_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (symbol, name, trend_direction, confidence, summary, analyzed_at),
                )

            conn.commit()
            return {
                "symbol": symbol,
                "name": name,
                "trend_direction": trend_direction,
                "confidence": confidence,
                "summary": summary,
                "analyzed_at": analyzed_at,
            }
        finally:
            conn.close()

    @staticmethod
    def get_latest_prediction(symbol: str) -> Optional[dict]:
        """Get the latest prediction for a specific stock symbol."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                """SELECT symbol, name, trend_direction, confidence, summary, analyzed_at
                   FROM predictions
                   WHERE symbol = ?
                   ORDER BY analyzed_at DESC
                   LIMIT 1""",
                (symbol,),
            ).fetchone()

            if row:
                return {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "trend_direction": row["trend_direction"],
                    "confidence": row["confidence"],
                    "summary": row["summary"],
                    "analyzed_at": row["analyzed_at"],
                }
            return None
        finally:
            conn.close()

    @staticmethod
    def get_all_latest_predictions() -> List[dict]:
        """Get the latest prediction for each stock that has been analyzed."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Get latest prediction for each symbol
            rows = cursor.execute(
                """SELECT p.symbol, p.name, p.trend_direction, p.confidence, p.summary, p.analyzed_at
                   FROM predictions p
                   INNER JOIN (
                       SELECT symbol, MAX(analyzed_at) as max_analyzed
                       FROM predictions
                       GROUP BY symbol
                   ) latest ON p.symbol = latest.symbol AND p.analyzed_at = latest.max_analyzed
                   ORDER BY p.analyzed_at DESC""",
            ).fetchall()

            return [
                {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "trend_direction": row["trend_direction"],
                    "confidence": row["confidence"],
                    "summary": row["summary"],
                    "analyzed_at": row["analyzed_at"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def get_predictions_by_symbol(symbol: str, limit: int = 7) -> List[dict]:
        """Get recent predictions for a stock (for history/trends)."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute(
                """SELECT symbol, name, trend_direction, confidence, summary, analyzed_at
                   FROM predictions
                   WHERE symbol = ?
                   ORDER BY analyzed_at DESC
                   LIMIT ?""",
                (symbol, limit),
            ).fetchall()

            return [
                {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "trend_direction": row["trend_direction"],
                    "confidence": row["confidence"],
                    "summary": row["summary"],
                    "analyzed_at": row["analyzed_at"],
                }
                for row in rows
            ]
        finally:
            conn.close()
