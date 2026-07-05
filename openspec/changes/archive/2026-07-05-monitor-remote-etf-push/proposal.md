## Why

The overseas `remote_data` service pushes normalized ETF data into the domestic `etf_remote.db` via an authenticated ingest endpoint. When a push silently stops (network issue, auth drift, scheduler death, schema drift) the domestic side has no quick way to detect it — data freshness can only be inferred by noticing missing charts in the UI, which is far too late. Operators (e.g. `jack.zhu` with `system_statistics` permission) need a single panel that shows, at a glance, whether the overseas → domestic pipeline is healthy: how long ago each table was last pushed, and how fresh the latest record in each table actually is.

## What Changes

- Add a backend endpoint `GET /api/admin/etf-remote-push-status` (gated by `system_statistics`) that returns per-table push health for `etf_remote.db`:
  - `last_received_at` from `etf_ingest_log` (the last push that hit this table)
  - `last_record_date` from the business table itself (the latest business-date/row stored)
  - `row_count` for that table
  - `lag_hours` and a derived `status` of `ok` / `warn` / `stale` based on configurable thresholds per `data_type`
- Add a new "ETF 数据推送监控" (ETF Data Push Monitor) block to the existing `SystemAdminPanel`, reading from that endpoint. The block lists each `data_type` table with its three timestamps and a colour-coded status pill, plus a "Refresh" button. The block polls every ~60s; manually refreshing more than once a second is not needed (operations only need one look a day, but seeing fresh data right after a check is useful).
- No new tables, no new permissions, no frontend framework changes. Backend reads from existing `etf_remote.db` (path from `REMOTE_DB_PATH`/`data/etf_remote.db`) and the existing `etf_ingest_log` table. Frontend reuses `vt-panel` / `vt-btn-oxblood` styling in `SystemAdminPanel.tsx`.

## Capabilities

### New Capabilities

- `etf-remote-push-monitor`: capability covering (a) the backend endpoint that summarises `etf_remote.db` push health per table, (b) the freshness / status thresholds used to derive `ok`/`warn`/`stale`, and (c) the System Admin Panel block that displays this to admins.

### Modified Capabilities

- `system-admin-module`: the existing System Administration module spec is extended to include the new ETF push monitor block (an additional block alongside the existing "股票统计" and "用户统计" blocks, and a new API endpoint `/api/admin/etf-remote-push-status` under the same `system_statistics` gate).

## Impact

- Backend: new router file under `backend/api/admin/etf_remote_push_status.py` (or addition to an existing admin router), with a small helper that opens `etf_remote.db` read-only via `sqlite3` and queries `etf_ingest_log` + each business table. Requires the process to have read access to `data/etf_remote.db` (it already does — it's the persistence target).
- Frontend: `frontend/src/components/SystemAdminPanel.tsx` — add a new panel block; minor type/interface additions; no new dependencies.
- Configuration: thresholds (hours-since-last-received → warn / stale) live in env vars with sensible defaults (e.g. `ETF_PUSH_STALE_HOURS=24`, `ETF_PUSH_WARN_HOURS=6`); defaults can be tuned without code changes.
- No impact on the pusher, fetcher, or store code; no schema migration; no breaking changes.