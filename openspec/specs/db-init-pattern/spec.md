# db-init-pattern Specification

## Purpose
Define the database initialization design pattern used across the backend:
schema bootstrap is a single point per database, services do not lazily self-initialize,
legacy schemas are upgraded in place, and LLM-shaped data is hydrated defensively so
a single malformed row cannot 500 an entire list endpoint.

## Requirements

### Requirement: Single Source of Truth for Schema Bootstrap
The system SHALL have exactly one schema-bootstrap function per SQLite database, and SHALL invoke it once from `main.py` startup before any service runs. Service modules SHALL NOT call schema-creation code from inside their own methods.

#### Scenario: Two SQLite databases, two bootstrap entry points
- **WHEN** the backend starts
- **THEN** `db_migration.init_schema()` runs first and provisions all tables in `watchlist.db` (users, user_watchlist, captchas, user_sessions, roles, permissions, user_roles, role_permissions)
- **AND** `trend_prediction_service.init_predictions_db()` runs next and provisions the `predictions` and `user_analysis_triggers` tables in `trend_predictions.db`
- **AND** `trend_prediction_service.init_hourly_news_db()` provisions the `hourly_news` table
- **AND** `trend_prediction_service.init_trend_runs_db()` provisions the `trend_runs` table

#### Scenario: No lazy self-init in service methods
- **WHEN** a service method (e.g. `WatchlistService.get_watchlist`, `TrendPredictionService.save_prediction`) is invoked
- **THEN** the method SHALL NOT call any `init_db()` or `init_*_db()` function as its first action
- **AND** the method SHALL assume the schema already exists, since `main.py` startup has already run

#### Scenario: Redundant `init_db` functions are removed
- **WHEN** inspecting `backend/services/`
- **THEN** no module SHALL export a function named `init_db` (use the specific name like `init_predictions_db` to make the scope obvious)
- **AND** no module SHALL contain `CREATE TABLE` statements outside the designated bootstrap functions
- **AND** no module SHALL contain `ALTER TABLE ADD COLUMN` defensive blocks in service methods — column upgrades belong in the bootstrap

### Requirement: Idempotent Schema Bootstrap
The system SHALL guarantee that calling the bootstrap functions multiple times (e.g. on every restart) is safe and produces the same end state.

#### Scenario: CREATE TABLE IF NOT EXISTS is no-op on second call
- **WHEN** `init_schema()` runs against a DB where all tables already exist
- **THEN** no error is raised
- **AND** no data is modified

#### Scenario: Seed data uses INSERT OR IGNORE
- **WHEN** `init_schema()` seeds roles / permissions / role_permissions
- **THEN** the SQL SHALL use `INSERT OR IGNORE`
- **AND** re-running produces no duplicates

### Requirement: Legacy Column Upgrade
The system SHALL bring databases restored from older backups up to the current schema on first startup, so that historical DBs (which may pre-date a column) work without manual SQL.

#### Scenario: Missing column is detected and added
- **WHEN** a table exists but is missing a column that the current code expects
- **THEN** the bootstrap SHALL detect the gap via `PRAGMA table_info(<table>)`
- **AND** SHALL execute `ALTER TABLE <table> ADD COLUMN <definition>`
- **AND** the operation SHALL be idempotent (re-running against an already-current table is a no-op)

#### Scenario: Example — users.is_guest on legacy DB
- **WHEN** `init_schema()` runs against a DB whose `users` table was created before `is_guest` was added
- **THEN** the helper SHALL detect the missing column
- **AND** SHALL add `is_guest INTEGER DEFAULT 0` to the `users` table

#### Scenario: Example — predictions.extended_analysis on legacy DB
- **WHEN** `init_predictions_db()` runs against a DB whose `predictions` table was created before `extended_analysis` was added
- **THEN** the inlined PRAGMA check SHALL detect the missing column
- **AND** SHALL add `extended_analysis TEXT` to the `predictions` table

### Requirement: Defensive Hydration of LLM-Shaped Data
The system SHALL tolerate malformed values in LLM-generated JSON blobs that are surfaced through Pydantic response models, so a single bad row cannot 500 an entire list endpoint.

#### Scenario: dict-typed response field receives non-dict value
- **WHEN** `_hydrate_extended_fields` copies a key from the stored extended-analysis JSON into a result dict
- **AND** the value is anything other than a `dict` (e.g. `str`, `None`, `list`, `int`)
- **THEN** the field SHALL be dropped from the result (not assigned at all, so the Pydantic default `None` is used)
- **AND** other keys in the same row SHALL still be processed normally
- **AND** other rows in the list SHALL still be returned

#### Scenario: Top-level extended_analysis is not a dict
- **WHEN** the stored extended-analysis JSON parses to something other than a dict (e.g. a bare string from a corrupted row)
- **THEN** the hydration SHALL return early
- **AND** no field is assigned
- **AND** the row is still returned with the standard fields (symbol, trend_direction, confidence, summary, analyzed_at)

#### Scenario: String is not a valid JSON
- **WHEN** the stored value is a string that does not parse as JSON
- **THEN** the hydration SHALL catch the parse error
- **AND** SHALL return early without raising

### Requirement: Separate Concerns — Schema vs. Application Data
The system SHALL NOT seed application data (user accounts, user role assignments, watchlist entries) as part of schema bootstrap. Application data SHALL be created through the application's normal flows (registration, admin init, watchlist API).

#### Scenario: Schema bootstrap does not create users
- **WHEN** `init_schema()` runs on a fresh DB
- **THEN** the `users` table is created but stays empty
- **AND** no default admin / `jack.zhu` / etc. is created
- **AND** no password hash is hardcoded in any schema-bootstrap file
- **AND** the legacy `scripts/migrate_roles_permissions.py` does NOT exist in the codebase (its seed-data logic moved into `init_schema()`'s role/permission block, but its user-creation logic was removed entirely)

#### Scenario: System-defined roles are seed data, not application data
- **WHEN** `init_schema()` runs on a fresh DB
- **THEN** the 4 roles (admin / power_user / user / guest) and 3 permissions (assign_role / system_statistics / customized_agent) and their role→permission mappings are seeded
- **BECAUSE** these are part of the application's contract (business code references these names), not user data

### Requirement: No bcrypt / Hardcoded Credentials in Source
The system SHALL NOT contain hardcoded passwords, default admin credentials, or `bcrypt` calls in schema-bootstrap code. Admin user creation SHALL be handled by a future dedicated `init_admin` flow that reads credentials from environment / secrets manager.

#### Scenario: Grepping for hardcoded credentials returns nothing
- **WHEN** searching `backend/services/db_migration.py` for `bcrypt`, `gensalt`, `hashpw`, `password`, `jack.zhu`, `imabigboy`
- **THEN** no matches are returned
- **AND** the only references to "default user" or "admin user" are in TODOs / future-init spec docs
