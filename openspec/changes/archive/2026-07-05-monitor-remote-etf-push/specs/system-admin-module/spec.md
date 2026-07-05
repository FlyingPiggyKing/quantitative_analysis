# system-admin-module Specification (delta)

## MODIFIED Requirements

### Requirement: System Admin Module Content
The system SHALL display statistics blocks within the System Administration module for system-wide observability: stock statistics, user statistics, and an ETF Data Push Monitor block. The ETF block visibility follows the same `system_statistics` permission gate as the rest of the module.

#### Scenario: System Administration module displays stock statistics block
- **WHEN** admin user views the System Administration module
- **THEN** a "股票统计" (Stock Statistics) block is displayed
- **AND** it lists all unique stocks from `user_watchlist` across all users (deduplicated by symbol)
- **AND** each stock shows: symbol, name, market, added_at, user_count (number of users following this stock)
- **AND** it shows the total count of unique stocks (e.g., "共 X 只股票")

#### Scenario: System Administration module displays user statistics block
- **WHEN** admin user views the System Administration module
- **THEN** a "用户统计" (User Statistics) block is displayed
- **AND** it lists all registered users (username and registration date)
- **AND** it shows the total count of users (e.g., "共 X 位用户")

#### Scenario: System Administration module displays ETF data push monitor block
- **WHEN** admin user views the System Administration module
- **THEN** an "ETF 数据推送监控" (ETF Data Push Monitor) block is displayed
- **AND** it lists one row per `data_type` table in `etf_remote.db` (实时报价 / 基本面 / 持仓 / 行业权重 / 业绩 / 成分股权重 / ESG / 新闻)
- **AND** each row shows: data_type label, last push time (relative + absolute), latest business date, row count, and a colour-coded status pill (`ok` / `warn` / `stale` / `unknown`)
- **AND** the block includes a "刷新" (Refresh) button and auto-refreshes every 60 seconds
- **AND** the block shows a "last checked at" timestamp derived from the endpoint response

## ADDED Requirements

### Requirement: Admin API endpoints for System Administration
The system SHALL provide admin-only API endpoints under `/api/admin`, accessible only to users with `system_statistics` permission:
- `GET /api/admin/stats` — returns watchlist stocks and user statistics (existing)
- `GET /api/admin/etf-remote-push-status` — returns per-table push health for `etf_remote.db`

#### Scenario: Authorized user can access admin stats endpoint
- **WHEN** a user with `system_statistics` permission calls `GET /api/admin/stats` with valid authentication
- **THEN** the response contains `watchlist_stocks` array with symbol, name, market, added_at, user_count for each unique stock
- **AND** the response contains `users` array with id, username, created_at for each user
- **AND** the response contains `watchlist_count` and `user_count` integers

#### Scenario: Authorized user can access ETF push status endpoint
- **WHEN** a user with `system_statistics` permission calls `GET /api/admin/etf-remote-push-status` with valid authentication
- **THEN** the response contains a `tables` array with one entry per business data_type in `etf_remote.db`
- **AND** each entry contains `data_type`, `last_received_at`, `last_record_date`, `row_count`, `lag_hours`, `status`
- **AND** the response contains `server_time`, `db_path`, and `thresholds`

#### Scenario: Unauthorized user cannot access admin endpoints
- **WHEN** a user without `system_statistics` permission calls any `/api/admin/*` endpoint
- **THEN** the system returns HTTP 403 Forbidden
- **AND** error message indicates insufficient permissions