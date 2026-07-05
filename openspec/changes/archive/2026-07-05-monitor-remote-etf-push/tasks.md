## 1. Backend — read-only health query

- [x] 1.1 Add `backend/api/admin/etf_remote_push_status.py` with a `compute_push_status(db_path)` function that opens `etf_remote.db` via `sqlite3.connect("file:<path>?mode=ro", uri=True)` and returns the per-`data_type` summary (data_type, last_received_at, last_record_date, row_count, lag_hours, status). Use a `TABLE_SPECS` list of `(data_type, table, date_column, label_zh)` tuples for the 8 business tables.
- [x] 1.2 Compute `last_received_at` from `SELECT MAX(received_at) FROM etf_ingest_log WHERE data_type = ?` per table.
- [x] 1.3 Compute `last_record_date` from `SELECT MAX(<date_column>) FROM <table>` and `row_count` from `SELECT COUNT(*) FROM <table>` per table.
- [x] 1.4 Compute `lag_hours = (now_utc - last_received_at).total_seconds() / 3600` and round to 2 decimals; `lag_hours = None` when `last_received_at IS NULL`.
- [x] 1.5 Derive `status` from `ETF_PUSH_WARN_HOURS` (default 6) and `ETF_PUSH_STALE_HOURS` (default 24) per the spec table.
- [x] 1.6 Return `{"tables": [...], "server_time": <iso>, "db_path": <path>, "thresholds": {"warn_hours": ..., "stale_hours": ...}}`; on `FileNotFoundError` return `{"tables": [], "server_time": ..., "db_path": ..., "thresholds": {...}, "error": "etf_remote.db not found"}`.

## 2. Backend — endpoint wiring

- [x] 2.1 Add `GET /api/admin/etf-remote-push-status` route to the existing admin router. Reuse the same `system_statistics` permission gate that `GET /api/admin/stats` uses (same dependency injection helper).
- [x] 2.2 Resolve `REMOTE_DB_PATH` env var (default `data/etf_remote.db`) to an absolute path before opening; log the resolved path at startup.
- [x] 2.3 Add backend tests: (a) authorised user gets 200 with correct schema; (b) unauthorised gets 403; (c) missing db returns 200 with empty tables; (d) lag/status thresholds produce expected status for synthetic timestamps.
- [x] 2.4 Verify: `cd backend && uv run pytest tests/test_admin_etf_remote_push_status.py -v` passes; manual `curl -H "Authorization: Bearer ..." http://localhost:8000/api/admin/etf-remote-push-status` returns the documented JSON shape.

## 3. Frontend — admin panel block

- [x] 3.1 In `frontend/src/components/SystemAdminPanel.tsx`, add the `EtfPushStatus` type and a `useEtfPushStatus()` hook (or inline state) that fetches `/api/admin/etf-remote-push-status` and exposes `data`, `loading`, `error`, `lastCheckedAt`, `refresh()`.
- [x] 3.2 Render a new "ETF 数据推送监控" `vt-panel` block as a sibling of the existing "股票统计" / "用户统计" blocks. Show one row per `data_type` with: Chinese label, relative time ("3 小时前"), last business date, row count, status pill, and a "刷新" button.
- [x] 3.3 Add status pill rendering: `ok` → green, `warn` → amber, `stale` → red, `unknown` → grey. Use the project's existing `vt-*` token classes (add 4 small token classes if missing).
- [x] 3.4 Auto-refresh every 60 seconds via `setInterval`; clear on unmount. Manual "刷新" button triggers an immediate re-fetch.
- [x] 3.5 On endpoint error, keep the previous snapshot visible and show an inline small "刷新失败" pill; on `tables: []` + `error` field, show "etf_remote.db 未找到" message.
- [x] 3.6 Show "last checked at: <server_time>" timestamp at the bottom of the block using the response's `server_time`.
- [ ] 3.7 Verify: `cd frontend && pnpm dev` (or `npm run dev`), open `/`, log in as admin, open "系统管理" tab; confirm the new block renders, refresh button works, status pills colour correctly, auto-refresh fires after 60s.

## 4. Configuration & docs

- [x] 4.1 Add `ETF_PUSH_WARN_HOURS=6` and `ETF_PUSH_STALE_HOURS=24` to `backend/.env.example` with a short comment.
- [x] 4.2 Update `README.md` (or the system-admin section) with a 2–3 line note that operators can now see push health under "系统管理 → ETF 数据推送监控".
- [x] 4.3 Verify: no `pkill` of running backend needed; env vars are read at request time so a backend restart picks them up.

## 5. End-to-end smoke (operator — requires live dev backend + browser)

- [ ] 5.1 With the dev backend up and `data/etf_remote.db` populated, open the admin panel in a browser; confirm every `data_type` row shows a non-null `last_received_at` (or `unknown` if the table has never been pushed).
- [ ] 5.2 Temporarily set `ETF_PUSH_STALE_HOURS=0` via env and restart; confirm all rows flip to `stale` (red). Revert.
- [ ] 5.3 Stop the overseas pusher for ~5 minutes; confirm the row for `etf_quote` increments `lag_hours` visibly and eventually flips to `warn`.
- [x] 5.4 `openspec validate monitor-remote-etf-push --strict` passes.
- [ ] 5.5 Archive the change via `openspec archive monitor-remote-etf-push` once verified.