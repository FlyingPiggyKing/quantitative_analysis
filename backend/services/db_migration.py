"""Database migration for user authentication."""
import sqlite3
from pathlib import Path
import bcrypt

DB_PATH = Path(__file__).parent.parent / "watchlist.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def migrate():
    """Run all migrations."""
    conn = get_db_connection()

    # Create users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create user_watchlist table (replaces global watchlist)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, symbol)
        )
    """)

    # Create captchas table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS captchas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create user_sessions table for token tracking
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_jti TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()

    # Migrate existing watchlist entries to user jack.zhu (user_id=1)
    cursor = conn.cursor()

    # Check if jack.zhu exists
    row = cursor.execute("SELECT id FROM users WHERE username = ?", ("jack.zhu",)).fetchone()

    if row is None:
        # Create default user jack.zhu
        password_hash = bcrypt.hashpw("imabigboy820518".encode(), bcrypt.gensalt()).decode()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("jack.zhu", password_hash)
        )
        conn.commit()
        user_id = cursor.execute("SELECT id FROM users WHERE username = ?", ("jack.zhu",)).fetchone()[0]
    else:
        user_id = row[0]

    # Migrate existing watchlist entries to jack.zhu
    cursor.execute("""
        INSERT OR IGNORE INTO user_watchlist (user_id, symbol, name, added_at)
        SELECT ?, symbol, name, added_at FROM watchlist
    """, (user_id,))

    conn.commit()
    conn.close()
    print(f"Migration complete. User jack.zhu has id={user_id}")


if __name__ == "__main__":
    migrate()
