# etf-remote-push-monitor Specification

## Purpose
Provide administrators with real-time visibility into the per-table push health of `etf_remote.db` so they can detect and triage ingest stalls on the overseas pusher.

## Requirements

### Requirement: Admin endpoint summarises per-table push health for etf_remote.db
The backend SHALL expose `GET /api/admin/etf-remote-push-status`, gated by the same `system_statistics` permission used by the existing `/api/admin/stats` endpoint. The endpoint SHALL return a JSON object with one entry per business table in `etf_remote.db` (`etf_quote`, `etf_fundamentals`, `etf_holdings`, `etf_sector_weights`, `etf_performance`, `etf_equity_holdings`, `etf_esg`, `etf_news`). For each `data_type` it MUST include:
- `data_type` (string)
- `last_received_at` (ISO8601 UTC string or `null`) — the latest `received_at` in `etf_ingest_log` whose `data_type` matches, irrespective of `accepted`/`rejected`
- `last_record_date` (ISO8601 date or timestamp string or `null`) — the most recent business date/timestamp stored in that table
- `row_count` (non-negative integer) — total rows in the table
- `lag_hours` (number, 2-decimal places, or `null`) — `now_utc - last_received_at` in hours
- `status` (string, one of `ok`, `warn`, `stale`, `unknown`) — derived from thresholds described below

The endpoint MUST also return `server_time` (ISO8601 UTC string of the backend's clock used to compute `lag_hours`) and `db_path` (string, the resolved `etf_remote.db` path).

#### Scenario: Authorized admin fetches status
- **WHEN** a user with `system_statistics` permission calls `GET /api/admin/etf-remote-push-status` with valid authentication
- **THEN** the response is HTTP 200 with JSON containing `tables` (array of `data_type` summaries), `server_time`, `db_path`, and `thresholds` (the resolved warn/stale hour values)

#### Scenario: Unauthorized user is rejected
- **WHEN** a user without `system_statistics` permission calls `GET /api/admin/etf-remote-push-status`
- **THEN** the response is HTTP 403 Forbidden

#### Scenario: Guest user is rejected
- **WHEN** an unauthenticated user calls `GET /api/admin/etf-remote-push-status`
- **THEN** the response is HTTP 401 Unauthorized

#### Scenario: Database file missing
- **WHEN** `data/etf_remote.db` does not exist or is not readable
- **THEN** the response is HTTP 200 with `tables: []`, `server_time` set, `db_path` set to the resolved path, and an `error: "etf_remote.db not found"` field

### Requirement: Push freshness status derives from configurable thresholds
The system SHALL classify each table's push health based on `lag_hours` and configured thresholds `ETF_PUSH_WARN_HOURS` (default 6) and `ETF_PUSH_STALE_HOURS` (default 24):
- `lag_hours <= WARN_HOURS` → `ok`
- `WARN_HOURS < lag_hours <= STALE_HOURS` → `warn`
- `lag_hours > STALE_HOURS` → `stale`
- `last_received_at IS NULL` → `unknown` (table has never received a push)

#### Scenario: Recent push
- **WHEN** `etf_quote` last received a push 2 hours ago and `WARN_HOURS=6`
- **THEN** its `status` is `ok` and `lag_hours` is `2.00`

#### Scenario: Push slipping behind
- **WHEN** `etf_fundamentals` last received a push 10 hours ago and `WARN_HOURS=6`, `STALE_HOURS=24`
- **THEN** its `status` is `warn`

#### Scenario: Stale push
- **WHEN** `etf_news` last received a push 36 hours ago and `STALE_HOURS=24`
- **THEN** its `status` is `stale`

#### Scenario: Never received
- **WHEN** `etf_holdings` has no rows in `etf_ingest_log` with that `data_type`
- **THEN** its `status` is `unknown`, `last_received_at` is `null`, `lag_hours` is `null`

### Requirement: `last_record_date` reflects the latest business date stored in each table
The system SHALL compute `last_record_date` as the maximum value of the business date/timestamp column for each table:
- `etf_quote.last_record_date` = `MAX(ts)`
- `etf_fundamentals.last_record_date` = `MAX(as_of)`
- `etf_holdings.last_record_date` = `MAX(as_of_date)`
- `etf_sector_weights.last_record_date` = `MAX(as_of_date)`
- `etf_performance.last_record_date` = `MAX(as_of_date)`
- `etf_equity_holdings.last_record_date` = `MAX(as_of_date)`
- `etf_esg.last_record_date` = `MAX(as_of_date)`
- `etf_news.last_record_date` = `MAX(published_at)`

The endpoint MUST return `null` for `last_record_date` when the table is empty.

#### Scenario: Empty table
- **WHEN** `etf_esg` has 0 rows
- **THEN** its `last_record_date` is `null`, `row_count` is `0`

#### Scenario: Populated table
- **WHEN** `etf_quote` has rows including one with `ts = '2026-07-04T20:00:00Z'`
- **THEN** its `last_record_date` is `2026-07-04T20:00:00Z` and `row_count` matches the actual row count

### Requirement: Endpoint reads etf_remote.db read-only and never mutates it
The endpoint SHALL open `etf_remote.db` using SQLite's `open(... uri=True, mode='ro')` (or equivalent read-only connection) so that monitoring traffic cannot corrupt or block the live ingest writer.

#### Scenario: Read-only connection used
- **WHEN** the endpoint opens the database
- **THEN** the SQLite connection mode is `ro` (read-only); any attempt to write through the monitor connection MUST fail at the SQLite layer

### Requirement: Endpoint responds quickly for repeated calls
The endpoint MUST return within 2 seconds under normal conditions (database file < 100 MB, 8 tables queried, no external network calls). It MUST NOT take an exclusive lock on the database.

#### Scenario: Cold call latency
- **WHEN** the endpoint is called for the first time after backend startup
- **THEN** the response returns within 2 seconds with all 8 table entries populated

#### Scenario: Concurrent calls
- **WHEN** two admin clients call the endpoint within 100 ms of each other
- **THEN** both succeed and return identical (or near-identical) results; no SQLite `database is locked` errors are returned to the client

### Requirement: System Admin Panel renders an ETF Data Push Monitor block
The `SystemAdminPanel` component SHALL render an "ETF 数据推送监控" block as a sibling of the existing "股票统计" and "用户统计" blocks. The block MUST display, for each `data_type`:
- The Chinese-friendly label (e.g. `实时报价`, `基本面`, `持仓`, `行业权重`, `业绩`, `成分股权重`, `ESG`, `新闻`)
- `last_received_at` formatted as a relative time ("3 小时前") and an absolute timestamp on hover
- `last_record_date` as a date string
- `row_count` as an integer
- A status pill coloured by `status`:
  - `ok` → green
  - `warn` → amber
  - `stale` → red
  - `unknown` → grey
- A "刷新" (Refresh) button that triggers an immediate re-fetch
- The panel's "last checked at" timestamp (server_time from the response) so operators know how fresh the snapshot is

The block MUST auto-refresh every 60 seconds by default.

#### Scenario: Admin opens the panel
- **WHEN** an admin user opens the System Administration module
- **THEN** the "ETF 数据推送监控" block is rendered below the existing statistics blocks and initially shows a loading state, then populated rows

#### Scenario: Manual refresh
- **WHEN** the admin clicks the "刷新" button
- **THEN** the block re-fetches `/api/admin/etf-remote-push-status` and updates rows and "last checked at"

#### Scenario: Auto-refresh
- **WHEN** 60 seconds elapse without any user interaction
- **THEN** the block silently re-fetches and updates the displayed rows

#### Scenario: Endpoint unreachable
- **WHEN** the endpoint returns HTTP 5xx or the network call fails
- **THEN** the block shows an inline error message ("加载失败") and keeps the previous snapshot visible (no full-block error)

#### Scenario: No data
- **WHEN** `tables` is empty (e.g. `etf_remote.db` missing)
- **THEN** the block shows "etf_remote.db 未找到，请检查 data/etf_remote.db 是否存在" and the error field from the response

#### Scenario: Status colours
- **WHEN** a table's `status` is `warn`
- **THEN** its status pill renders with the amber colour class defined in the project's styling tokens
