## ADDED Requirements

### Requirement: Database Backup Script
The system SHALL provide a backup script that copies the SQLite database before any migration.

#### Scenario: Backup creates timestamped copy
- **WHEN** `scripts/backup_database.py` is executed
- **THEN** it copies `backend/watchlist.db` to `backend/watchlist.db.backup.<timestamp>`
- **WHERE** `<timestamp>` is in format `YYYYMMDD_HHMMSS`
- **AND** backup file is created in the same directory as the original

#### Scenario: Backup succeeds silently
- **WHEN** `scripts/backup_database.py` is executed
- **THEN** it prints "Backup created: watchlist.db.backup.<timestamp>"
- **AND** exits with code 0

#### Scenario: Backup handles missing database gracefully
- **WHEN** `scripts/backup_database.py` is executed but database file is missing
- **THEN** it prints error message and exits with code 1
