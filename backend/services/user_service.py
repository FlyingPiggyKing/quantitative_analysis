"""User service for user CRUD operations."""
import sqlite3
from pathlib import Path
from typing import Optional
import bcrypt

DB_PATH = Path(__file__).parent.parent / "watchlist.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class UserService:
    """Service for user operations."""

    @staticmethod
    def get_user_by_username(username: str) -> Optional[dict]:
        """Get user by username. Returns user dict or None."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "created_at": row["created_at"],
                }
            return None
        finally:
            conn.close()

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[dict]:
        """Get user by ID. Returns user dict or None."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT id, username, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "created_at": row["created_at"],
                }
            return None
        finally:
            conn.close()

    @staticmethod
    def create_user(username: str, password: str) -> dict:
        """Create a new user. Returns user dict or error dict."""
        if len(password) < 8:
            return {"error": "Password must be at least 8 characters"}

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return {
                "id": user_id,
                "username": username,
                "created_at": datetime.now().isoformat(),
            }
        except sqlite3.IntegrityError:
            return {"error": "Username already taken"}
        finally:
            conn.close()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


from datetime import datetime
