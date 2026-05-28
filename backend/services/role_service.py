"""Role and permission service for RBAC."""
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "watchlist.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class RoleService:
    """Service for role and permission operations."""

    @staticmethod
    def user_has_permission(user_id: int, permission_name: str) -> bool:
        """Check if a user has a specific permission via any of their roles."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT 1
                FROM user_roles ur
                JOIN role_permissions rp ON ur.role_id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE ur.user_id = ? AND p.name = ?
                LIMIT 1
            """, (user_id, permission_name)).fetchone()
            return row is not None
        finally:
            conn.close()

    @staticmethod
    def get_user_roles(user_id: int) -> list[str]:
        """Get all role names for a user."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT r.name
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = ?
            """, (user_id,)).fetchall()
            return [row["name"] for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_role_permissions(role_id: int) -> list[str]:
        """Get all permission names for a role."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT p.name
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = ?
            """, (role_id,)).fetchall()
            return [row["name"] for row in rows]
        finally:
            conn.close()

    @staticmethod
    def get_role_permissions_by_name(role_name: str) -> list[str]:
        """Get all permission names for a role by role name."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT p.name
                FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE r.name = ?
            """, (role_name,)).fetchall()
            return [row["name"] for row in rows]
        finally:
            conn.close()

    @staticmethod
    def is_guest_user(user_id: int) -> bool:
        """Check if a user is a guest (unauthenticated)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT is_guest FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            if row:
                return row["is_guest"] == 1
            return True  # User not found, assume guest
        finally:
            conn.close()

    @staticmethod
    def assign_role_to_user(user_id: int, role_name: str) -> bool:
        """Assign a role to a user. Returns True if successful."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            role = cursor.execute(
                "SELECT id FROM roles WHERE name = ?",
                (role_name,)
            ).fetchone()
            if not role:
                return False
            cursor.execute(
                "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, role[0])
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def remove_role_from_user(user_id: int, role_name: str) -> bool:
        """Remove a role from a user. Returns True if successful."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            role = cursor.execute(
                "SELECT id FROM roles WHERE name = ?",
                (role_name,)
            ).fetchone()
            if not role:
                return False
            cursor.execute(
                "DELETE FROM user_roles WHERE user_id = ? AND role_id = ?",
                (user_id, role[0])
            )
            conn.commit()
            return True
        finally:
            conn.close()
