# Implementation Tasks

## 1. Data Model & Run State

- [x] 1.1 Add `init_trend_runs_db()` to `backend/services/trend_prediction_service.py` (or new module) creating `trend_runs` table (`id, run_date, trigger_type, status, total_stocks, batch_count, current_batch, batch_total, batch_completed, created_at, updated_at`) with `CREATE TABLE IF NOT EXISTS`.
- [x] 1.2 Create `backend/services/trend_run_service.py` with functions: `create_run(trigger_type, total_stocks) -> run_id`, `get_active_run()`, `get_latest_run()`, `update_batch_progress(run_id, current_batch, batch_total, batch_completed)`, `set_status(run_id, status)`, `get_run_for_date(run_date)`.
- [x] 1.3 Add `manual_trigger_available()` helper: returns True iff weekday AND local time ≥ 17:00 AND no `trend_runs` row exists for today.
- [x] 1.4 Add startup reconciliation `mark_stale_runs_interrupted()` that sets any `pending`/`running` row to `interrupted`.

## 2. Dedicated Run Queue

- [x] 2.1 Create `backend/services/trend_run_queue.py` with a module-global `ThreadPoolExecutor(max_workers=1)` (separate from `task_queue.py`) and a registry of per-run `threading.Event` cancel flags.
- [x] 2.2 Implement batch division helper `split_into_batches(stocks) -> list[list]` producing exactly 4 batches with `ceil(total/4)` sizing, covering all stocks, tolerating <4 stocks (empty batches allowed).
- [x] 2.3 Implement `run_batch(run_id, batch_index, stocks)`: sequentially call `analyze_stock_trend(symbol, name)` + `TrendPredictionService.save_prediction(...)` per stock, updating `update_batch_progress` after each; check the run's cancel flag before each stock and abort if set.
- [x] 2.4 Implement `start_run(trigger_type) -> run_id`: snapshot deduped stocks via `AdminService.get_watchlist_stocks()`, cancel any active run (set flag, remove its pending scheduler jobs, mark `cancelled`), create run record, submit batch 1 to the queue, and schedule batches 2–4.
- [x] 2.5 Implement `cancel_run(run_id)`: set cancel flag, remove pending batch jobs from the scheduler, mark status `cancelled`.

## 3. Scheduler Wiring (`backend/main.py`)

- [x] 3.1 In `start_scheduler()`, call `init_trend_runs_db()` and `mark_stale_runs_interrupted()` on startup.
- [x] 3.2 Add cron job `day_of_week='mon-fri', hour=17, minute=0` (id `daily_trend_analysis`) that invokes the auto-run entry point.
- [x] 3.3 Implement the auto-run entry point that calls `start_run("auto")`; ensure batches 2–4 are scheduled as one-off `date` jobs at +5h/+10h/+15h relative to batch 1, with stable job ids per run so they can be removed on cancel.
- [x] 3.4 Verify the existing hourly news job and scheduler shutdown still work unchanged.

## 4. Admin API (`backend/api/admin.py`)

- [x] 4.1 Add `GET /api/admin/trend-run` guarded by `system_statistics`: returns current/last run (`run_date`, `trigger_type`, `status`, `current_batch`, `batch_count`, `batch_total`, `batch_completed`) plus `manual_trigger_available`.
- [x] 4.2 Add `POST /api/admin/trend-run/trigger` guarded by `system_statistics`: 403 if unauthorized; 409 if a run is active; 400/409 if not currently available; otherwise `start_run("manual")` and return run identity + status.
- [x] 4.3 Manually verify both endpoints return 403 for a user without `system_statistics`.

## 5. Frontend — Admin Panel (`frontend/src/components/SystemAdminPanel.tsx`)

- [x] 5.1 Add a service module function (e.g. in `frontend/src/services/`) for `GET /api/admin/trend-run` and `POST /api/admin/trend-run/trigger` using `getAuthHeaders()`.
- [x] 5.2 Add a "趋势分析进度" block showing run date, `第 {current_batch}/{batch_count} 批`, and `{batch_completed}/{batch_total}`; poll every 3–5s while a run is active.
- [x] 5.3 Add a "趋势分析" trigger button below the panel, enabled only when `manual_trigger_available` is true; on click call the trigger endpoint and refresh status; show rejection feedback on 409.
- [x] 5.4 Show a sensible empty/last-run state when no run is active.

## 6. Frontend — Remove Homepage Batch Button (`frontend/src/app/page.tsx`)

- [x] 6.1 Remove the batch "趋 势 分 析" button JSX and revert the "查 询" button to full width for authenticated users.
- [x] 6.2 Remove `handleTrendAnalysis`, the `runBatchAnalysisAsync` import, and `isAnalyzing` (and any now-unused imports/state) that were only used by the removed button; keep per-stock force-async and progress-bar logic that is not tied to the batch button.
- [x] 6.3 Confirm `force-async` per-stock analysis on stock detail pages is unchanged.

## 7. Verification

- [x] 7.1 Backend smoke test: import the new modules and call `split_into_batches` with 48, 50, and 3 stocks; assert 4 batches each and full coverage.
- [x] 7.2 Run backend (`uv` venv from `backend/`) and confirm startup logs show the `daily_trend_analysis` job registered and no scheduler errors.
- [x] 7.3 Manually exercise: with no run today after 17:00 (simulate), `GET /api/admin/trend-run` reports `manual_trigger_available: true`; trigger a manual run; verify progress advances and a second trigger during the run returns 409.
- [x] 7.4 Frontend build (`npm run build` / lint) passes with no unused-variable errors after the homepage button removal.
- [x] 7.5 `openspec validate auto-trend-analysis` passes.
