## Context

The quantitative-analysis stack has two halves. The overseas half (`remote_data/`) runs a fetcher that pulls normalized ETF data from yahooquery and a pusher that ships it over HTTPS, HMAC-signed, to a domestic ingest endpoint. The domestic half persists those payloads into a single SQLite database at `data/etf_remote.db` (8 business tables + `etf_ingest_log`) and exposes read APIs.

The existing `etf_ingest_log` table already records every push that arrives:
```
id, batch_id, data_type, source_ip, accepted, rejected, received_at
```
…so the data needed for "how recently did each table get pushed" is already on disk. What's missing is a way to read it without going to the SQLite CLI.

`SystemAdminPanel.tsx` already gates an admin-only stats panel by the `system_statistics` permission. We extend that panel with a sibling block. The change is read-only on the monitoring side and does not touch the pusher/persistence pipeline.

Stakeholders: `jack.zhu` (admin), operations staff who need to know "is the pipeline healthy?" without reading logs.

## Goals / Non-Goals

**Goals**
- One-call answer to "is `etf_remote.db` receiving pushes, and are the rows fresh?"
- Visual signal at a glance: green / amber / red / grey per `data_type`
- Read-only access; no writes, no locks, no schema changes
- Single backend endpoint, single frontend block, minimal surface area
- Configurable thresholds via env (`ETF_PUSH_WARN_HOURS`, `ETF_PUSH_STALE_HOURS`) with sensible defaults

**Non-Goals**
- Alerting / email / webhook on `stale` (operators open the panel; that's the alert)
- Trend history / time-series charts (operators only need one look a day)
- Writing back into `etf_remote.db` (read-only is the contract)
- Modifying the pusher, fetcher, persistence, or ingest endpoint
- Showing per-symbol freshness (per-table is enough at this scale)

## Decisions

### D1. New backend endpoint at `GET /api/admin/etf-remote-push-status`
**Why:** Mirrors the existing `GET /api/admin/stats` shape and reuses the same `system_statistics` gate. Single-purpose endpoint keeps the SQL surface small.

**Alternatives considered:**
- Extend `GET /api/admin/stats` with a `etf_remote` key → rejected: mixes concerns; the existing endpoint is "user/watchlist" oriented and is cached in the frontend with no refresh button; pushing 60s polling onto it would force polling the watchlist too.
- Add `?include=etf_remote` query flag → rejected: still couples refresh cycles; explicit endpoint is cleaner.

### D2. Open `etf_remote.db` with SQLite URI `file:...?mode=ro`
**Why:** The persistence path is also the read path for ingest and the read API. Using `mode=ro` guarantees the monitor cannot accidentally corrupt the live writer's data, even if a bug in the monitor tries to write. SQLite supports this via `sqlite3.connect("file:data/etf_remote.db?mode=ro", uri=True)`.

**Alternatives considered:**
- Reuse the persistence module's connection pool → rejected: it's wired for writes and would require either a second pool or careful connection scoping; the read-only DB is small (<100 MB), so a fresh connection per request is fine.
- Plain `sqlite3.connect(path)` → rejected: opens in `rw` mode by default, which is unnecessary privilege.

### D3. Per-table summary computed in Python, not a single big SQL
**Why:** The data we need per table is small (one MAX + one COUNT + one join to `etf_ingest_log`). A hand-written Python loop over a `TABLE_SPECS` list of `(data_type, table, date_column)` tuples is easier to test and matches the schema-per-table shape already established in `etf-persistence`. Each iteration opens a single SELECT against the read-only connection.

**Alternatives considered:**
- One SQL query with UNION ALL of MAX(date_col) per table → rejected: harder to keep in sync if a table is added; no measurable perf win for 8 tables.
- Persist a denormalised "last push status" row updated by the ingest endpoint → rejected: that's a schema change and adds a write path; out of scope for a monitoring feature.

### D4. Lag is measured against `etf_ingest_log.received_at`, not the business date
**Why:** "How recently did the overseas side push?" is a pipeline-health question, not a data-freshness question. `etf_ingest_log.received_at` answers that directly. `last_record_date` is also exposed separately so operators can distinguish "the pusher is silent" from "the pusher is up but yahooquery returned no new rows".

**Alternatives considered:**
- Compute lag from `last_record_date` only → rejected: hides pipeline stalls that didn't yet surface in the data (e.g. market holiday where no new rows land for a day).
- Compute lag from `push_log` on the overseas side → rejected: requires querying the overseas DB; monitoring must work from the domestic side alone.

### D5. Status thresholds via env vars with defaults
**Why:** Different `data_type`s have different natural cadences (quotes are minutes, fundamentals are days). Defaulting to 6h warn / 24h stale is a reasonable global default; if a finer-grained per-data_type table is needed later, it can be layered on top without breaking the contract. Operators can tune `ETF_PUSH_WARN_HOURS` and `ETF_PUSH_STALE_HOURS` without a redeploy if the backend is configured to read env at request time (default behaviour of `os.getenv`).

**Alternatives considered:**
- Per-`data_type` thresholds in a config file → rejected: too much knob for a feature operators use once a day.
- Hardcoded constants → rejected: makes environment-specific tuning impossible.

### D6. Frontend block polls every 60s, manual refresh button
**Why:** Operators said "at most once a day", but they also want to see fresh data right after they check. 60s polling is the lowest cadence that feels "live" without spamming the endpoint. A manual refresh button handles the "I just kicked the pipeline, show me now" case.

**Alternatives considered:**
- No auto-refresh, manual only → rejected: stale on-screen data defeats the purpose.
- 10s polling → rejected: too aggressive for a "check a couple of times a day" use case.

### D7. Status pill colours reuse existing CSS tokens
**Why:** `vt-panel`, `vt-brass-400`, `vt-parchment-dim` are already used in `SystemAdminPanel.tsx`. We add 4 small token classes (`vt-pill-ok`, `vt-pill-warn`, `vt-pill-stale`, `vt-pill-unknown`) using the same green/amber/red/grey pattern that's idiomatic in the codebase. No new colour system.

**Alternatives considered:**
- Tailwind utility colours directly → rejected: the file uses `vt-*` tokens throughout; mixing in raw `text-green-500` would be inconsistent.

### D8. Frontend keeps last good snapshot on transient errors
**Why:** Operators care about "is the pipeline healthy", not "did my dashboard work". If the endpoint hiccups, showing the previous snapshot with a small inline "刷新失败" pill is more useful than blowing away the whole block.

## Risks / Trade-offs

- [Monitor holds a long-lived read-only connection] → Mitigation: open per-request and close; SQLite WAL mode means readers don't block writers, but holding a connection is unnecessary for sub-2s queries.
- [Backend can't reach `data/etf_remote.db` (path differs in containers)] → Mitigation: respect the existing `REMOTE_DB_PATH` env var the persistence layer already uses; surface `db_path` in the response so operators can see what's being read; on `FileNotFoundError`, return 200 with `tables: []` and an `error` field rather than 5xx.
- [Thresholds too tight cause false alarms] → Mitigation: defaults are generous (6h warn / 24h stale); ops can bump via env without code change. Document the envs in `backend/.env.example`.
- [Frontend polling at 60s adds backend load if many admins] → Mitigation: query is read-only and sub-2s; load is trivial. If it ever becomes a problem, add a `Cache-Control: max-age=30` header on the endpoint.
- [Lag hours uses the backend clock, not the ingest clock] → Mitigation: include `server_time` in the response so operators see the reference clock; log a warning at startup if the backend's UTC clock differs from `time.time()` by more than 5s.
- [One symbol with thousands of rows slows `MAX(date_col)`] → Mitigation: each business table has a primary key on `(symbol, ts|date)`; SQLite uses the index for `MAX` on a leading column trivially. If a future table has a different key shape, the `TABLE_SPECS` tuple can carry an `index_hint`.

## Migration Plan

1. Land backend endpoint + tests; deploy to dev environment.
2. Confirm endpoint returns sensible data against a known-good `etf_remote.db`.
3. Land frontend block; verify in admin's local browser.
4. Watch for a week; tune `ETF_PUSH_WARN_HOURS` / `ETF_PUSH_STALE_HOURS` based on observed push cadence.

**Rollback:** Remove the new endpoint and revert the frontend file. No data migrations, no destructive operations. The endpoint is purely additive.

## Open Questions

- Do we want a server-side cache (e.g. 30s `Cache-Control`) to absorb bursty polling from multiple admins? Default: no, defer until observed.
- Should `last_record_date` for `etf_news` reflect the published date or the received-at? Default: published date (matches the natural meaning of "freshness" for news); revisit if operators ask.
- Should we expose per-symbol lag (e.g. "QQQ is 2h behind, SPY is 5h behind")? Default: no — out of scope for the "one look a day" use case.