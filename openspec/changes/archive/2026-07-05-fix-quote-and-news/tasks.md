## 1. Extend `epoch_to_iso` to accept ISO date strings

- [x] 1.1 In `remote_data/fetcher/base.py`, extend `epoch_to_iso` to also accept ISO date strings: try `datetime.fromisoformat(value.replace("Z", "+00:00"))` first, then fall back to the existing `datetime.fromtimestamp(float(value), tz=timezone.utc)` path; both branches produce a string in the canonical `"%Y-%m-%dT%H:%M:%SZ"` form
- [x] 1.2 Verify: existing `test_epoch_to_iso_handles_bad_input` (and any other callers) still pass

## 2. Update `etf_quote` fetcher to use the dual-shape helper

- [x] 2.1 In `remote_data/fetcher/etf_quote.py`, confirm `ts_epoch = raw.get("regularMarketTime") or raw.get("preMarketTime") or raw.get("postMarketTime")` is unchanged and that `ts_iso = epoch_to_iso(ts_epoch) if ts_epoch is not None else None` continues to work; no edit needed beyond verifying the helper upgrade
- [x] 2.2 Verify: `test_fetch_quotes_shape` still passes

## 3. Update fake ticker fixture and add regression test

- [x] 3.1 In `remote_data/fetcher/tests/test_fetcher.py`, change `_FakeTicker.price` so `regularMarketTime` is the string `"2025-06-29 12:26:40"` (matching the live API shape) and `postMarketTime` is `"2025-06-29 19:59:58"`; keep `regularMarketPrice`, `regularMarketVolume`, etc. unchanged
- [x] 3.2 Add a regression test `test_epoch_to_iso_accepts_both_epoch_and_iso_string` in the same file that asserts: (a) `epoch_to_iso(1751200000)` returns `"2025-06-29T12:26:40Z"`; (b) `epoch_to_iso("2025-06-29 12:26:40")` returns `"2025-06-29T12:26:40Z"`; (c) `epoch_to_iso("2025-06-29T12:26:40Z")` returns `"2025-06-29T12:26:40Z"`; (d) `epoch_to_iso("not a date")` returns `None`; (e) `epoch_to_iso(None)` returns `None`
- [x] 3.3 Verify: `python3 -m pytest remote_data/ -v` shows all previous tests still passing plus the new regression test

## 4. Stub out the news fetch (path C)

- [x] 4.1 In `remote_data/scheduler/jobs.py`, remove the entry `"etf_news": (fetch_news, local_db.insert_etf_news),` from `_FETCH_TABLE`
- [x] 4.2 In `safe_run`, drop the special-case branch `if data_type != "etf_news" else fn(symbols, since=None)` — replace with a plain `records = fn(symbols)`
- [x] 4.3 In `build_scheduler`, remove the `fetch_news_job = make_fetch_job("etf_news", ...)` registration and its `scheduler.add_job(...)` block
- [x] 4.4 In `remote_data/config.py`, remove the `fetch_news_interval_minutes` field from `Config` (and from any `@dataclass` defaults / parsing)
- [x] 4.5 In `remote_data/.env.example`, remove or comment out `FETCH_NEWS_INTERVAL_MINUTES=60`
- [x] 4.6 At the top of `remote_data/fetcher/etf_news.py`, add a parking comment block referencing this OpenSpec change
- [x] 4.7 Verify: `python3 -m pytest remote_data/ -v` still passes (existing news tests should still pass since the module is intact; `test_build_scheduler_registers_all_jobs` must be updated to no longer expect `etf_news`)

## 5. Update scheduler test that enumerated all jobs

- [x] 5.1 In `remote_data/scheduler/tests/test_scheduler.py`, find `test_build_scheduler_registers_all_jobs` and remove `etf_news` from the expected job list (verify the test passes with the news entry gone)
- [x] 5.2 Verify: `python3 -m pytest remote_data/scheduler/ -v` passes

## 6. End-to-end verification on the live host

- [x] 6.1 From `remote_data/`, run `python3 scripts/init_local_db.py` to ensure schema is unchanged (idempotent — should print "schema applied" and exit 0)
- [x] 6.2 Run `python3 -m pytest remote_data/ -v`; expect 50 (existing) + 1 (new regression) passed, no failures
- [x] 6.3 Stop the running daemon (`./stop-fetcher.sh` from repo root — see [[deploy-no-systemd]]) and restart (`./start-fetcher.sh`)
- [x] 6.4 Within ~90 seconds, confirm:
  - `fetch_log` shows a new `etf_quote` row with `status='ok'` and `row_count=20` (instead of the previous `status='error'`) → id=940 @ 03:15:56, status=ok, rows=20 ✓
  - `etf_quote` table contains rows (`SELECT COUNT(*) FROM etf_quote` returns > 0) → 20 rows ✓
  - `push_log` shows a new `etf_quote` row with `http_status=200` and `row_count=20` → id=8 @ 03:16:08, http=200, rows=20 ✓
  - `fetch_log` shows no new `etf_news` activity (the job is no longer scheduled) → 0 post-restart news entries ✓
- [x] 6.5 Roll back if any check fails: NOT NEEDED — all checks passed; sample etf_quote rows show correctly-normalized `ts` (e.g. QQQ: `2026-07-02T20:00:01Z` from yahooquery's `"2026-07-02 20:00:01"` string)