## ADDED Requirements

### Requirement: Local SQLite database stores raw fetcher output and push cursor
The system SHALL create a SQLite database at `LOCAL_DB_PATH` (default `data/etf_local.db`). It MUST contain one table per `data_type`, each table's schema matching the normalized record shape, plus a `pushed_at` column and a `fetch_log` and `push_log` audit table.

#### Scenario: Database is created on first run
- **WHEN** `python -m remote_data` starts and `LOCAL_DB_PATH` does not exist
- **THEN** the system creates the database file and all required tables per `remote_data/store/schema.sql`

#### Scenario: All required tables exist
- **WHEN** the database is initialized
- **THEN** the following tables MUST exist: `etf_quote`, `etf_fundamentals`, `etf_holdings`, `etf_sector_weights`, `etf_performance`, `etf_equity_holdings`, `etf_esg`, `etf_news`, `etf_dead_letter`, `fetch_log`, `push_log`

#### Scenario: Each business table has a `pushed_at` column
- **WHEN** any business table is created
- **THEN** it MUST include a `pushed_at` column (nullable, default NULL) used as the push retry cursor

### Requirement: Store exposes insert / fetch-pending / mark-pushed operations
The store module MUST expose at minimum: `insert_<data_type>(records)`, `fetch_pending(data_type, limit)`, `mark_pushed(ids)`, `mark_failed(id, error)`, `record_push_attempt(...)`.

#### Scenario: Insert records
- **WHEN** the fetcher calls `insert_etf_quote([{...}])`
- **THEN** the records are written to `etf_quote` with `pushed_at = NULL`; duplicate `(symbol, ts)` MUST be deduplicated by UPSERT-style INSERT (latest record wins on `pushed_at`)

#### Scenario: Fetch pending pushes
- **WHEN** `fetch_pending("etf_quote", limit=100)` is called
- **THEN** the system returns up to 100 rows from `etf_quote` where `pushed_at IS NULL`, ordered by `ts` ascending

#### Scenario: Mark pushed
- **WHEN** `mark_pushed("etf_quote", [1, 2, 3])` is called
- **THEN** those rows have `pushed_at` set to the current UTC timestamp

#### Scenario: Record push attempt outcome
- **WHEN** the pusher completes an HTTP call
- **THEN** it calls `record_push_attempt(...)` with `data_type`, `batch_id`, `http_status`, `retry_count`, `error` (nullable), writing a row to `push_log`

### Requirement: Retention policy bounds disk usage
The store MUST expose a `prune()` operation that deletes rows older than configurable thresholds per data type.

#### Scenario: Prune old quotes
- **WHEN** `prune()` is called and `etf_quote` has rows older than 90 days
- **THEN** those rows are deleted; pushed and unpushed rows are pruned by `ts` (not `pushed_at`)

#### Scenario: Prune old news
- **WHEN** `prune()` is called and `etf_news` has rows older than 30 days
- **THEN** those rows are deleted

#### Scenario: Prune old push log
- **WHEN** `prune()` is called and `push_log` has rows older than 30 days
- **THEN** those rows are deleted

### Requirement: Dead letter table captures 4xx-class push failures
The system MUST write records that fail with non-retriable errors (4xx from the remote ingest) to `etf_dead_letter` with the original payload and the response body, and MUST mark the source row as `failed_at = now`.

#### Scenario: 4xx from remote
- **WHEN** the pusher receives HTTP 4xx from the ingest endpoint
- **THEN** the affected records are written to `etf_dead_letter` and the source rows have `failed_at` set; they are NOT retried on subsequent push loops
