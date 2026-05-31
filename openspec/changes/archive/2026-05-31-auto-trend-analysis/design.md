## Context

Trend prediction currently runs only when triggered manually:
- Homepage batch button → `POST /api/trend-predictions/batch-async` → `task_queue.py` (`ThreadPoolExecutor(max_workers=3)`) iterating the caller's watchlist.
- Per-stock force button → `force-async` (kept, unchanged).

The backend already runs an `apscheduler` `BackgroundScheduler` in `backend/main.py` (hourly news job), so scheduling infrastructure exists. The deduplicated system-wide stock set is already produced by `AdminService.get_watchlist_stocks()` (used by the admin panel). Predictions are stored via `TrendPredictionService.save_prediction()` in `trend_predictions.db`, and `analyze_stock_trend(symbol, name)` auto-detects market from the symbol.

We need to move trend prediction to a system-owned, daily, weekday, batched schedule that does not interfere with interactive traffic, expose progress + a recovery trigger in the admin module, and remove the homepage batch button.

Key clarifications from the requester:
- The manual trigger is a **recovery tool**, normally unavailable; it is offered only when the day's scheduled run was missed (e.g., restart/crash before 17:00). It then runs the same batched cadence.
- Only **one run at a time**; a manual trigger during an active run is rejected.
- **No backfill** of missed runs.

## Goals / Non-Goals

**Goals:**
- Daily weekday (Mon–Fri) automatic run at 17:00 over the deduplicated system watchlist.
- Exactly 4 sequential batches, batch size = `ceil(total / 4)` so all stocks are covered; one batch starts every 5 hours.
- Within a batch, analyze stocks one at a time on a **dedicated single-worker queue** independent of interactive request handling and of the existing per-stock force-async queue.
- Persist run/batch progress so the admin panel can show date, batch N/4, and in-batch progress.
- Admin panel progress block + recovery-only manual trigger button (enabled only when the scheduled run was missed), guarded by `system_statistics`.
- No backfill; interrupted runs marked and not auto-resumed; a new auto run cancels any active run.
- Remove the homepage batch "趋势分析" button.

**Non-Goals:**
- Changing per-stock force-async analysis, rate limiting, or the prediction storage schema/format.
- Persisting *pending batch jobs* across restarts (in-memory scheduling is acceptable given the no-backfill policy).
- Configurable batch count / schedule time / per-user runs (fixed at 4 batches, 17:00, 5h spacing, system-wide set).
- Real-time push of progress to the frontend (panel polls, consistent with existing patterns).

## Decisions

### D1: Scheduling — one weekday cron trigger + dynamically scheduled per-batch one-off jobs
Add to the existing `BackgroundScheduler`:
- A cron job `day_of_week='mon-fri', hour=17, minute=0` that **starts a run** (batch 1) and schedules batches 2–4 as one-off `date` jobs at +5h / +10h / +15h via `scheduler.add_job(..., 'date', run_date=...)`.

Rationale: a single entry point keeps the weekday/once-a-day/no-weekend rules in one place. Per-batch one-off jobs keep the 5-hour spacing explicit and make cancellation simple (remove the future job ids). Using `apscheduler`'s own `run_date` avoids hand-rolled sleep timers in threads.

*Alternative considered*: four independent cron jobs at 17:00/22:00/03:00/08:00. Rejected — batches 3/4 land on the next calendar day, making "weekday-only" and "belongs to which run" logic awkward (Friday's run legitimately spills into Saturday morning; we must allow that while still not *starting* a run on Saturday). A start-trigger + relative offsets models "a run that spans ~20h" cleanly.

### D2: Dedicated single-worker run queue, separate from `task_queue.py`
Introduce a dedicated `ThreadPoolExecutor(max_workers=1)` for runs (new module, e.g. `services/trend_run_queue.py`), distinct from the existing `max_workers=3` force/batch queue.

Rationale: req 2 demands sequential, one-at-a-time execution that does not compete with user queries. A separate single-worker pool guarantees at most one analysis from the run executes at any time and isolates it from interactive force-async work. Reusing the existing pool would interleave run work with user-triggered analyses and break the "one at a time" guarantee.

### D3: Run state persisted in `trend_predictions.db`; batch scheduling in-memory
Add a `trend_runs` table (one row per run) capturing the durable facts; keep the list of stocks-per-batch and the future job handles in memory.

Proposed `trend_runs` columns:
- `id` INTEGER PK
- `run_date` TEXT (`YYYY-MM-DD`, local) — used to enforce "one run per day" and "missed run" detection
- `trigger_type` TEXT (`auto` | `manual`)
- `status` TEXT (`pending` | `running` | `completed` | `cancelled` | `interrupted`)
- `total_stocks` INTEGER
- `batch_count` INTEGER (always 4)
- `current_batch` INTEGER (1–4, 0 before start)
- `batch_total` INTEGER (stocks in the current batch)
- `batch_completed` INTEGER (stocks finished in the current batch)
- `created_at`, `updated_at` TEXT (ISO)

Rationale: the panel needs progress to survive across HTTP requests and process reads → DB. Per the no-backfill policy, we deliberately do **not** persist pending batch jobs; if the process dies mid-run, batches simply stop (and the row is marked `interrupted`). This keeps the model simple and matches the requirement that missed/interrupted work is not resumed.

*Alternative considered*: pure in-memory run object (like `task_queue`'s `AnalysisTask`). Rejected for the run record itself because "missed run" detection and panel history want a durable `run_date`. We still keep the heavy per-batch stock lists in memory.

### D4: "Missed run" detection drives manual-trigger availability
Manual trigger is **available** iff: it is currently a weekday, local time ≥ 17:00, and there is **no `trend_runs` row for today**. Otherwise unavailable (day already ran, before 17:00, weekend, or a run is active).

Rationale: directly encodes "recovery only when the scheduled run was missed." Because the auto cron always inserts a row at 17:00 when up, the only way to have no row after 17:00 on a weekday is that the backend missed the trigger — exactly the recovery case. Re-triggering after a normal run is thus naturally blocked (a row exists).

### D5: Cancellation via a per-run cancel flag checked between stocks
Each run carries a `threading.Event` (in-memory, keyed by run id). The single worker checks it before each stock and at each batch boundary; future one-off batch jobs are removed from the scheduler. Starting a new auto run first cancels any active run (sets its event, removes its pending jobs, marks `cancelled`).

Rationale: cooperative cancellation is safe (no killing mid-analysis), and because execution is sequential the flag is checked frequently enough. Removing future `apscheduler` jobs stops not-yet-started batches.

### D6: Startup reconciliation
On app startup, mark any `trend_runs` row left in `pending`/`running` as `interrupted` (the process that owned its in-memory jobs is gone). Do not reschedule.

Rationale: satisfies "interrupted run is not auto-resumed" and keeps the panel honest after a restart.

### D7: API surface (admin, `system_statistics`-guarded)
Add to `backend/api/admin.py`:
- `GET /api/admin/trend-run` → current/last run status + `manual_trigger_available` boolean.
- `POST /api/admin/trend-run/trigger` → start a manual run; 409 if a run is active, 403 if unauthorized, 400/409 if not currently available.

Rationale: reuses the existing admin router and `RoleService.user_has_permission(..., "system_statistics")` guard pattern already used by `/api/admin/stats`.

### D8: Frontend
- `SystemAdminPanel.tsx`: add a progress block (polls `GET /api/admin/trend-run`, e.g. every 3–5s) showing `run_date`, `current_batch`/4, `batch_completed`/`batch_total`, plus a "趋势分析" button (enabled per `manual_trigger_available`) calling the trigger endpoint.
- `page.tsx`: remove the homepage batch button, `handleTrendAnalysis`, and the now-unused `runBatchAnalysisAsync` import; remove `isAnalyzing` if it becomes unused. The homepage force-async/per-stock flows and progress bar tied to user force actions remain as-is except for the batch button removal.

Rationale: keeps changes surgical and confined to the two components the requirements name.

## Risks / Trade-offs

- **In-memory batch jobs lost on restart** → By design (no backfill). Mitigation: mark `interrupted` on startup so the panel is accurate; admin can recover via manual trigger if it was today's run.
- **Friday run legitimately spills into Saturday (batches 3/4 at 03:00/08:00 Sat)** → Acceptable: we forbid *starting* a run on weekends, not finishing one. The cron only triggers Mon–Fri; offset jobs are allowed to land on Saturday.
- **Long-running single worker vs. a fast next-day auto run** → Cancellation (D5) ensures the next auto run preempts an unfinished prior/manual run; sequential design + frequent flag checks bound the cancellation latency to one in-flight stock analysis.
- **Clock/timezone**: schedule and `run_date` both use server local time; ensure the scheduler timezone matches the intended market timezone. Mitigation: rely on server local time consistently (same basis the hourly news job uses).
- **DB contention**: `trend_predictions.db` is SQLite shared with predictions/news. Run writes are low-frequency (per-stock + progress updates) on a single worker; risk of lock contention is low. Mitigation: short transactions, reuse existing connection helper.
- **Stock set changes mid-run**: snapshot at run start (D3) so batch composition is stable even if users edit watchlists during the ~20h window.

## Migration Plan

1. Add `trend_runs` table via an idempotent `init` (CREATE TABLE IF NOT EXISTS), called on startup alongside existing inits — no data migration needed.
2. Deploy backend with the new scheduler job, run queue, service, and admin endpoints. On startup, reconciliation marks any stale rows `interrupted` (none on first deploy).
3. Deploy frontend with the admin panel additions and homepage button removal.
4. Rollback: revert frontend (homepage button returns) and backend (remove scheduler job + endpoints). The `trend_runs` table can remain harmlessly; predictions table/format are untouched, so existing prediction reads continue working throughout.

## Open Questions

- Confirm the server's local timezone equals the intended 17:00 market-close reference; if the deployment runs UTC, the cron may need an explicit timezone. (Assumed: server local time, matching existing jobs.)
- Retention of `trend_runs` history (e.g., prune > N days) — not required by the spec; can be added later if the table grows.
