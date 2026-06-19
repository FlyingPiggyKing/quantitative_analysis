"""Initialize the watchlist.db schema.

Pure schema bootstrap for new deployments. Idempotent: safe to call repeatedly.
Application data (users, roles, permissions, watchlist entries) is created
through the app's normal flows, not here.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "watchlist.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn, table: str, column: str, ddl: str):
    """ALTER TABLE ADD COLUMN if the column is missing.

    Fresh DBs get the column via CREATE TABLE; this only triggers for DBs
    that pre-date a schema change (e.g. backups from before is_guest existed).
    """
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _create_tables():
    """Create all tables required by the current codebase."""
    conn = get_db_connection()

    # users — auth + guest flag
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_guest INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Bring legacy users tables up to current schema (column may be missing
    # on DBs restored from backups taken before the role/guest refactor).
    _ensure_column(conn, "users", "is_guest", "is_guest INTEGER DEFAULT 0")

    # user_watchlist — per-user, market-aware
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            market TEXT DEFAULT 'A' NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, symbol)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_market ON user_watchlist(user_id, market)"
    )

    # captchas — login gate
    conn.execute("""
        CREATE TABLE IF NOT EXISTS captchas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # user_sessions — JWT jti tracking
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

    # roles / permissions / junctions
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles(id),
            FOREIGN KEY (permission_id) REFERENCES permissions(id)
        )
    """)

    conn.commit()
    conn.close()


# System-defined roles and permissions. These are part of the application
# contract (business code references these names), not user data — so they
# are seeded alongside the schema instead of via the future admin init.
SYSTEM_ROLES = [
    ("admin", "Administrator with full access"),
    ("power_user", "Power user with advanced features"),
    ("user", "Regular registered user"),
    ("guest", "Unauthenticated guest user"),
]

SYSTEM_PERMISSIONS = [
    ("assign_role", "Permission to assign roles to users"),
    ("system_statistics", "Permission to view system statistics"),
    ("customized_agent", "Permission to use customized AI agent"),
]

# role_name -> set of permission names it should hold
ROLE_PERMISSION_MAP = {
    "admin": {"assign_role", "system_statistics", "customized_agent"},
    "power_user": {"customized_agent"},
}


def _seed_system_data():
    """Seed roles, permissions, and role→permission mappings. Idempotent."""
    conn = get_db_connection()
    cur = conn.cursor()

    for name, desc in SYSTEM_ROLES:
        cur.execute(
            "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
            (name, desc),
        )
    for name, desc in SYSTEM_PERMISSIONS:
        cur.execute(
            "INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
            (name, desc),
        )

    for role_name, perm_names in ROLE_PERMISSION_MAP.items():
        role = cur.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
        if not role:
            continue
        for perm_name in perm_names:
            perm = cur.execute(
                "SELECT id FROM permissions WHERE name = ?", (perm_name,)
            ).fetchone()
            if not perm:
                continue
            cur.execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                (role["id"], perm["id"]),
            )

    conn.commit()
    conn.close()


def init_schema():
    """Create all tables required by the current codebase and seed system data."""
    _create_tables()
    _seed_system_data()


if __name__ == "__main__":
    init_schema()
    print("Schema + system data initialized.")