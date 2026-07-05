## Why

The overseas ETF fetcher has been failing silently on two data types and we are losing freshness on the pipeline. `etf_quote` has produced zero rows in the last six hours of daemon runtime because `yahooquery.Ticker.price` now returns `regularMarketTime` as an **ISO date string** (e.g. `"2026-07-02 20:00:01"`) instead of an integer epoch, and `epoch_to_iso` returns `None`, causing the inserter to reject the entire 20-symbol batch. `etf_news` has never produced rows because `Ticker.news` is a method (not a property) and the underlying Yahoo Finance news endpoint is currently rate-limited / erroring for our session — both must be fixed before news can flow again. The pipeline today only ships `etf_fundamentals` and `etf_performance` (both daily) to the domestic node; fixing `etf_quote` restores intra-day freshness.

## What Changes

- **`remote_data/fetcher/base.py`** — make `epoch_to_iso` accept ISO date strings in addition to integer/float epochs, by attempting `datetime.fromisoformat` (with `Z` → `+00:00` normalization) before falling back to `datetime.fromtimestamp`.
- **`remote_data/fetcher/etf_quote.py`** — keep the existing `regularMarketTime`/`preMarketTime`/`postMarketTime` preference chain (still the right fields) but ensure the value is normalized before `epoch_to_iso` is called, so both shapes work.
- **`remote_data/fetcher/tests/test_fetcher.py`** — update `_FakeTicker.price` to return `regularMarketTime` as a string (matching the real API), and add a regression test asserting `epoch_to_iso` accepts both epoch numbers and ISO date strings.
- **`remote_data/scheduler/jobs.py`** — remove `etf_news` from `_FETCH_TABLE` and from `build_scheduler` (no fetch job, no log noise). The `etf_news` table remains in the schema so a future change can wire a different news source without a migration.
- **`remote_data/config.py`** — drop the `fetch_news_interval_minutes` knob from Config (or keep it as unused-but-documented, depending on existing tests).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- **`etf-fetcher`** — requirement changes: quote timestamp normalization must accept both integer epochs and ISO date strings returned by `yahooquery.Ticker.price`; news fetcher is no longer part of the fetcher capability surface (parked until a new source is chosen).
- **`etf-scheduler`** — requirement changes: the scheduler no longer schedules a periodic news fetch job.
- **`etf-local-store`** — no requirement change (the store already rejects rows with NULL `ts`/`published_at`; behavior stays the same).

## Impact

- **Code**:
  - `remote_data/fetcher/base.py` (helper change, low risk)
  - `remote_data/fetcher/etf_quote.py` (uses helper, low risk)
  - `remote_data/fetcher/etf_news.py` (becomes dead code — see tasks.md)
  - `remote_data/scheduler/jobs.py` (one entry removed, one scheduled job removed)
  - `remote_data/config.py` (one knob removed)
  - `remote_data/fetcher/tests/test_fetcher.py` (fixture update + new test)
- **Schema**: unchanged. `etf_news` table remains; existing rows unaffected.
- **APIs / wire contract**: unchanged. The pusher is data-type-agnostic over `local_db.all_business_tables()`; removing the news fetch simply means no news rows land to be pushed.
- **Daemon runtime**: a single daily job (news) stops firing; the rest of the schedule is untouched.
- **Operations**: `etf_news` in `fetch_log` will stop showing activity. `etf_quote` fetch_log entries should transition from `status=error` (ValueError) to `status=ok` with `row_count=20`, and `etf_quote` table should accumulate one row per symbol per 5-minute fetch interval, with corresponding successful pushes to the domestic node.