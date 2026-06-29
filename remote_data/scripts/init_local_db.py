#!/usr/bin/env python3
"""Standalone initialization script for the local SQLite store.

Loads `.env`, resolves `LOCAL_DB_PATH`, creates parent dir if needed, applies
schema via `local_db.init()`, prints the resulting table list to stdout.

Exit codes:
    0 — success
    non-zero — failure (already-existing schema is NOT a failure: idempotent)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable when invoked as a script.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from remote_data.store import local_db  # noqa: E402


def main() -> int:
    try:
        path = local_db.init()
    except Exception as exc:
        print(f"init_local_db: FAILED — {exc}", file=sys.stderr)
        return 1

    conn = local_db.connect(path)
    try:
        tables = local_db.list_tables(conn)
    finally:
        conn.close()

    print(f"init_local_db: OK — db={path}")
    print(f"tables ({len(tables)}): {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())