## Why

Trend prediction today is triggered manually by users (the homepage "趋势分析" batch button), which means watchlist analysis only runs when someone remembers to click it, competes with live user queries for resources, and re-analyzes everything in one heavy burst. We want the system to own this work: analyze every watchlisted stock automatically once per trading day, spread the load across the day in small sequential batches so it never disrupts interactive use, and give admins visibility into progress plus a recovery trigger for the rare day the schedule is missed.

## What Changes

- Add a daily automatic trend-prediction run for all stocks in the system watchlist (the deduplicated union of every user's `user_watchlist`), executed Monday–Friday only (markets closed on weekends).
- Split each run into **4 sequential batches**. Batch size is derived from the live stock count divided into 4 (e.g., 48 stocks → 12 per batch); the last batch absorbs any remainder.
- Run **one batch every 5 hours** starting at **17:00**, so the 4 batches complete within ~20 hours. Within a batch, stocks are analyzed one at a time, sequentially, on a dedicated single-worker queue so the run never blocks interactive API requests or other users' queries.
- Persist run/batch progress (date, current batch number, per-batch progress, status) so it survives reads across requests.
- Add a **progress panel** in the System Administration module showing the current run's date, which batch is active (e.g., "第 2/4 批"), and progress (e.g., "7/12").
- Add a **manual "趋势分析" trigger button** below that panel, visible only to users with `system_statistics` permission. An admin may trigger a run **at any time**; the button is disabled only while a run is already active. When triggering **off-schedule** (weekend, weekday before 17:00, or a day that already ran), the admin must **confirm twice** before the run starts; within the normal weekday-17:00 window a single confirmation suffices. Manual runs use the same batched, every-5-hours cadence.
- **No catch-up / backfill**: if a scheduled run does not start (system down at 17:00), the system SHALL NOT auto-run it later. Recovery is only via the manual admin trigger.
- **Auto run takes priority over manual**: when the next day's scheduled run starts, it cancels any still-active manual (or prior) run — unfinished stocks are abandoned because a fresh round has begun.
- **One run at a time**: if a run is already active, a manual trigger is rejected.
- **BREAKING**: Remove the homepage batch "趋势分析" button (req 7). Trend prediction is now system-managed. The per-stock "立刻分析 / 强制分析" (force-async) button on stock detail pages is unchanged.

## Capabilities

### New Capabilities
- `scheduled-trend-analysis`: Daily weekday, batched, sequential automatic trend prediction over all watchlisted stocks, with a dedicated non-blocking queue, persisted run/batch progress, no-backfill policy, and auto-cancels-manual priority rules.
- `trend-analysis-manual-trigger`: Admin-only (`system_statistics`) manual trigger that runs the same batched flow, available any time (disabled only while a run is active), requiring double confirmation when triggered off-schedule.

### Modified Capabilities
- `system-admin-module`: Adds a trend-analysis progress panel and the manual trigger button (with its enable/disable rules) to the System Administration module and a supporting admin API endpoint.
- `stock-query`: Removes the homepage "趋势分析" button from the search/button layout requirement; the "查询" button reverts to full width for authenticated users.

## Impact

- **Backend**
  - `backend/main.py`: add a weekday 17:00 cron job and per-batch scheduling to the existing `BackgroundScheduler`; mark stale "running" runs as interrupted on startup.
  - New `backend/services/trend_run_service.py` (run/batch state + persistence) and a dedicated single-worker run queue (new module or extension of `task_queue.py`).
  - New `trend_runs` (and batch progress) storage in `trend_predictions.db`.
  - `backend/api/admin.py`: add run-status and manual-trigger endpoints guarded by `system_statistics`.
  - Reuses `analyze_stock_trend`, `TrendPredictionService.save_prediction`, and `AdminService.get_watchlist_stocks` (deduplicated stock source).
- **Frontend**
  - `frontend/src/components/SystemAdminPanel.tsx`: add progress panel + trigger button.
  - `frontend/src/app/page.tsx`: remove the homepage batch "趋势分析" button and its handler/import; the related homepage progress-bar wiring driven solely by that button becomes unused.
  - `frontend/src/services/` : add admin trend-run status/trigger calls.
- **Dependencies**: none new (`apscheduler` already present).
- **No change** to per-stock force-async analysis or rate limiting.
