"""Backup database script for watchlist.db"""
import shutil
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "backend" / "watchlist.db"
BACKUP_DIR = DB_PATH.parent


def backup_database():
    """Create a timestamped backup of watchlist.db"""
    if not DB_PATH.exists():
        print(f"Error: Database file not found: {DB_PATH}")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"watchlist.db.backup.{timestamp}"

    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path.name}")
    return True


if __name__ == "__main__":
    success = backup_database()
    exit(0 if success else 1)
