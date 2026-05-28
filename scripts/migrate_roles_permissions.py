"""Migration script for role and permission system."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "backend" / "watchlist.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def migrate():
    """Run all migrations for roles and permissions."""
    conn = get_db_connection()

    # 2.2 Add roles table with 4 default roles
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2.3 Add permissions table with 3 default permissions
    conn.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2.4 Add user_roles junction table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)

    # 2.5 Add role_permissions junction table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles(id),
            FOREIGN KEY (permission_id) REFERENCES permissions(id)
        )
    """)

    # 2.6 Add is_guest column to users table
    conn.execute("""
        ALTER TABLE users ADD COLUMN is_guest INTEGER DEFAULT 0
    """)

    conn.commit()

    cursor = conn.cursor()

    # 2.7 Seed role-permission mappings
    # Insert roles
    roles = [
        ('admin', 'Administrator with full access'),
        ('power_user', 'Power user with advanced features'),
        ('user', 'Regular registered user'),
        ('guest', 'Unauthenticated guest user'),
    ]
    for name, description in roles:
        cursor.execute(
            "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
            (name, description)
        )

    # Insert permissions
    permissions = [
        ('assign_role', 'Permission to assign roles to users'),
        ('system_statistics', 'Permission to view system statistics'),
        ('customized_agent', 'Permission to use customized AI agent'),
    ]
    for name, description in permissions:
        cursor.execute(
            "INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
            (name, description)
        )

    conn.commit()

    # Map permissions to roles
    # admin gets all 3 permissions
    admin_role = cursor.execute("SELECT id FROM roles WHERE name = 'admin'").fetchone()
    power_user_role = cursor.execute("SELECT id FROM roles WHERE name = 'power_user'").fetchone()
    assign_perm = cursor.execute("SELECT id FROM permissions WHERE name = 'assign_role'").fetchone()
    system_perm = cursor.execute("SELECT id FROM permissions WHERE name = 'system_statistics'").fetchone()
    agent_perm = cursor.execute("SELECT id FROM permissions WHERE name = 'customized_agent'").fetchone()

    if admin_role and assign_perm and system_perm and agent_perm:
        cursor.execute(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            (admin_role[0], assign_perm[0])
        )
        cursor.execute(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            (admin_role[0], system_perm[0])
        )
        cursor.execute(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            (admin_role[0], agent_perm[0])
        )

    # power_user gets customized_agent permission
    if power_user_role and agent_perm:
        cursor.execute(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            (power_user_role[0], agent_perm[0])
        )

    conn.commit()

    # 2.8 Assign jack.zhu to admin and power_user roles
    jack_user = cursor.execute("SELECT id FROM users WHERE username = ?", ("jack.zhu",)).fetchone()
    if jack_user:
        user_id = jack_user[0]
        admin = cursor.execute("SELECT id FROM roles WHERE name = 'admin'").fetchone()
        power_user = cursor.execute("SELECT id FROM roles WHERE name = 'power_user'").fetchone()
        if admin and power_user:
            cursor.execute(
                "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, admin[0])
            )
            cursor.execute(
                "INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, power_user[0])
            )
        conn.commit()

    # 2.9 Assign default 'user' role to existing registered users
    user_role = cursor.execute("SELECT id FROM roles WHERE name = 'user'").fetchone()
    if user_role:
        # Get all users that don't have any role yet
        cursor.execute("""
            INSERT OR IGNORE INTO user_roles (user_id, role_id)
            SELECT u.id, ?
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.user_id IS NULL
        """, (user_role[0],))
        conn.commit()

    conn.close()
    print("Migration complete.")


def verify():
    """Verify migration results."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n=== Verification ===")

    # Check roles
    print("\nRoles:")
    rows = cursor.execute("SELECT * FROM roles").fetchall()
    for row in rows:
        print(f"  {row['id']}: {row['name']} - {row['description']}")

    # Check permissions
    print("\nPermissions:")
    rows = cursor.execute("SELECT * FROM permissions").fetchall()
    for row in rows:
        print(f"  {row['id']}: {row['name']} - {row['description']}")

    # Check role_permissions
    print("\nRole-Permission Mappings:")
    rows = cursor.execute("""
        SELECT r.name as role, p.name as permission
        FROM role_permissions rp
        JOIN roles r ON rp.role_id = r.id
        JOIN permissions p ON rp.permission_id = p.id
    """).fetchall()
    for row in rows:
        print(f"  {row['role']} -> {row['permission']}")

    # Check jack.zhu roles
    print("\njack.zhu roles:")
    rows = cursor.execute("""
        SELECT r.name
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        JOIN users u ON ur.user_id = u.id
        WHERE u.username = 'jack.zhu'
    """).fetchall()
    for row in rows:
        print(f"  {row['name']}")

    # Check users with default 'user' role
    print("\nUsers with 'user' role:")
    rows = cursor.execute("""
        SELECT u.username
        FROM user_roles ur
        JOIN users u ON ur.user_id = u.id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name = 'user'
    """).fetchall()
    for row in rows:
        print(f"  {row['username']}")

    conn.close()


if __name__ == "__main__":
    migrate()
    verify()
