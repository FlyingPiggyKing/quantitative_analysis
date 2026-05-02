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
        # Create user_watchlist table with market column
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                market TEXT DEFAULT 'A' NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, symbol)
            )
        """)

        # Migration: Add market column if it doesn't exist (for existing tables)
        cursor = conn.execute("PRAGMA table_info(user_watchlist)")
        columns = [row[1] for row in cursor.fetchall()]
        if "market" not in columns:
            conn.execute("ALTER TABLE user_watchlist ADD COLUMN market TEXT DEFAULT 'A' NOT NULL")

        # Create index for faster market-based queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_market ON user_watchlist(user_id, market)
        """)
        conn.commit()
    finally:
        conn.close()


class WatchlistService:
    """Service for watchlist database operations with user isolation."""

    @staticmethod
    def get_watchlist(user_id: int, page: int = 1, page_size: int = 10, market: Optional[str] = None) -> dict:
        """Get paginated watchlist items for a specific user.

        Args:
            user_id: The user's ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            market: Optional market filter ('A' for A-share, 'US' for US stocks)
                   If None, returns all markets
        """
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Build query based on market filter
            if market:
                # Get total count for specific market
                total = cursor.execute(
                    "SELECT COUNT(*) FROM user_watchlist WHERE user_id = ? AND market = ?",
                    (user_id, market)
                ).fetchone()[0]

                # Get items for specific market
                offset = (page - 1) * page_size
                total_pages = (total + page_size - 1) // page_size if total > 0 else 1

                rows = cursor.execute(
                    "SELECT symbol, name, market, added_at FROM user_watchlist WHERE user_id = ? AND market = ? ORDER BY added_at DESC LIMIT ? OFFSET ?",
                    (user_id, market, page_size, offset)
                ).fetchall()
            else:
                # Get total count for all markets
                total = cursor.execute(
                    "SELECT COUNT(*) FROM user_watchlist WHERE user_id = ?",
                    (user_id,)
                ).fetchone()[0]

                # Get items for all markets
                offset = (page - 1) * page_size
                total_pages = (total + page_size - 1) // page_size if total > 0 else 1

                rows = cursor.execute(
                    "SELECT symbol, name, market, added_at FROM user_watchlist WHERE user_id = ? ORDER BY added_at DESC LIMIT ? OFFSET ?",
                    (user_id, page_size, offset)
                ).fetchall()

            items = [
                {"symbol": row["symbol"], "name": row["name"], "market": row["market"], "added_at": row["added_at"]}
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
    def add_stock(user_id: int, symbol: str, name: str, market: str = "A") -> dict:
        """Add a stock to the user's watchlist.

        Args:
            user_id: The user's ID
            symbol: Stock symbol
            name: Stock name
            market: Market type - 'A' for A-share, 'US' for US stocks (default: 'A')
        """
        init_db()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            added_at = datetime.now().isoformat()

            # Use INSERT OR REPLACE to handle updates if stock already exists
            cursor.execute(
                "INSERT OR REPLACE INTO user_watchlist (user_id, symbol, name, market, added_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, symbol, name, market, added_at)
            )
            conn.commit()
            return {"symbol": symbol, "name": name, "market": market, "added_at": added_at}
        except Exception as e:
            return {"error": str(e), "symbol": symbol}
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
                "SELECT symbol, name, market, added_at FROM user_watchlist WHERE user_id = ? AND symbol = ?",
                (user_id, symbol)
            ).fetchone()
            if row:
                return {"symbol": row["symbol"], "name": row["name"], "market": row["market"], "added_at": row["added_at"]}
            return None
        finally:
            conn.close()
