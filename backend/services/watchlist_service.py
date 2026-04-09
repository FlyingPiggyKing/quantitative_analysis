"""Watchlist database service using SQLite with user isolation."""
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "watchlist.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database, creating the watchlist table if it doesn't exist."""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


class WatchlistService:
    """Service for watchlist database operations with user isolation."""

    @staticmethod
    def get_watchlist(user_id: int, page: int = 1, page_size: int = 10) -> dict:
        """Get paginated watchlist items for a specific user."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Get total count
            total = cursor.execute(
                "SELECT COUNT(*) FROM user_watchlist WHERE user_id = ?", (user_id,)
            ).fetchone()[0]

            # Calculate pagination
            offset = (page - 1) * page_size
            total_pages = (total + page_size - 1) // page_size if total > 0 else 1

            # Get items
            rows = cursor.execute(
                "SELECT symbol, name, added_at FROM user_watchlist WHERE user_id = ? ORDER BY added_at DESC LIMIT ? OFFSET ?",
                (user_id, page_size, offset)
            ).fetchall()

            items = [
                {"symbol": row["symbol"], "name": row["name"], "added_at": row["added_at"]}
                for row in rows
            ]

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        finally:
            conn.close()

    @staticmethod
    def add_stock(user_id: int, symbol: str, name: str) -> dict:
        """Add a stock to the user's watchlist."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            added_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO user_watchlist (user_id, symbol, name, added_at) VALUES (?, ?, ?, ?)",
                (user_id, symbol, name, added_at)
            )
            conn.commit()
            return {"symbol": symbol, "name": name, "added_at": added_at}
        except sqlite3.IntegrityError:
            # Stock already exists for this user
            return {"error": "Stock already in watchlist", "symbol": symbol}
        finally:
            conn.close()

    @staticmethod
    def remove_stock(user_id: int, symbol: str) -> bool:
        """Remove a stock from the user's watchlist. Returns True if removed, False if not found."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_watchlist WHERE user_id = ? AND symbol = ?", (user_id, symbol))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def check_stock(user_id: int, symbol: str) -> Optional[dict]:
        """Check if a stock is in the user's watchlist. Returns stock info if found, None otherwise."""
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT symbol, name, added_at FROM user_watchlist WHERE user_id = ? AND symbol = ?",
                (user_id, symbol)
            ).fetchone()
            if row:
                return {"symbol": row["symbol"], "name": row["name"], "added_at": row["added_at"]}
            return None
        finally:
            conn.close()
