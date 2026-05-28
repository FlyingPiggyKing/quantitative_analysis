"""Admin service for system statistics."""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).parent.parent / "watchlist.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class AdminService:
    """Service for admin operations."""

    @staticmethod
    def get_watchlist_stocks() -> List[Dict[str, Any]]:
        """Get all stocks from user_watchlist across all users (deduplicated by symbol)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                SELECT symbol, name, market, MAX(added_at) as added_at, COUNT(DISTINCT user_id) as user_count
                FROM user_watchlist
                GROUP BY symbol, name, market
                ORDER BY added_at DESC
                """
            ).fetchall()
            return [
                {
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "market": row["market"],
                    "added_at": row["added_at"],
                    "user_count": row["user_count"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def get_users() -> List[Dict[str, Any]]:
        """Get all registered users (non-guest)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT id, username, created_at FROM users WHERE is_guest = 0 ORDER BY created_at DESC"
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "username": row["username"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get all admin statistics."""
        stocks = AdminService.get_watchlist_stocks()
        users = AdminService.get_users()
        return {
            "watchlist_stocks": stocks,
            "watchlist_count": len(stocks),
            "users": users,
            "user_count": len(users),
        }
