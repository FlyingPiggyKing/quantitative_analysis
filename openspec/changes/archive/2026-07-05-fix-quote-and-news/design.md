## Context

The `remote_data` package implements the overseas half of the ETF pipeline (`etf-fetcher-pusher`). A live daemon has been running on this host since 2026-07-02; `fetch_log` and `push_log` show the system is healthy for daily data types (`etf_fundamentals`, `etf_performance` — both pushed at 200 OK) but two data types are silently broken:

1. **`etf_quote`** — `yahooquery.Ticker(symbol).price` returns `regularMarketTime`, `preMarketTime`, and `postMarketTime` as **ISO date strings** (e.g. `"2026-07-02 20:00:01"`) rather than integer epochs as the fetcher assumes. The string flows into `epoch_to_iso` which calls `float(...)` → `ValueError` → returns `None`. `ts=None` then trips the `ts TEXT NOT NULL` constraint in `etf_quote` (`local_db._row_to_values`), and the entire 20-symbol batch fails with `ValueError: etf_quote record missing required field ts`. Net effect: 843 failed fetches, 0 rows, 0 pushes for `etf_quote` since the daemon started.

2. **`etf_news`** — `yahooquery.Ticker(symbol).news` is a bound method, but the fetcher treats it as a property (`t.news or []`), which yields the method object and raises `TypeError: 'method' object is not iterable`. The exception is swallowed per-symbol inside `fetch_news`, leaving `etf_news` with zero rows. Even after fixing the call shape (`t.news()`), the Yahoo Finance news endpoint currently returns `["error"]` from `yahooquery` (driven by an upstream 429 / hard error from `query2.finance.yahoo.com/v2/finance/news`) for every symbol, every call, from this IP — confirmed by direct HTTP probes also returning `HTTP 429 Too Many Requests` against `/v7/finance/quote`, `/v1/finance/search`, and `/v2/finance/news`. yahooquery is at the latest version (2.4.1).

The `etf-fetcher` and `etf-scheduler` specs currently require news to flow; we are relaxing that requirement (path C — stub news out) while leaving the table in place for a future change.

The unit test fixture (`_FakeTicker` in `remote_data/fetcher/tests/test_fetcher.py`) returns `regularMarketTime: 1751200000` — an integer epoch — which is why the bug never surfaced in CI. The fixture is stale relative to the live API.

## Goals / Non-Goals

**Goals:**
- Restore `etf_quote` rows landing in the local store and being pushed to the domestic node within one 5-minute fetch window after deployment.
- Make `epoch_to_iso` (and any other field that may receive either shape) tolerant of both integer-epoch and ISO-date-string variants from `yahooquery`, so future similar drift doesn't break the whole batch.
- Stop scheduling `etf_news` fetches so the daemon log no longer shows `TypeError: 'method' object is not iterable` warnings and `fetch_log` stops recording `status=ok row_count=0` mis-leading entries.
- Keep the `etf_news` table, the `insert_etf_news` helper, and the wire-format contract intact so a future change can re-introduce news ingestion without a schema migration.
- Preserve all existing test coverage; update stale fixtures to match real API shape; add a regression test for the dual-shape `epoch_to_iso` behavior.

**Non-Goals:**
- Choosing a new news source (Google News RSS, Finnhub, Alpha Vantage, NewsAPI, etc.) — this is a separate change once a decision is made.
- Re-introducing `etf_news` end-to-end — out of scope.
- Fixing the "one bad record nukes the whole batch" pattern in `_insert_records` — that's a separate, broader hardening task; we just want `etf_quote` working again.
- Touching the push loop, signing, retry, or wire-format — out of scope.

## Decisions

### D1. Normalize time inputs in `epoch_to_iso` rather than at each call-site

`epoch_to_iso` is the single helper that converts a yahooquery time field into the ISO string the store expects. It currently only handles `int | float | None`. We extend it to also handle ISO date strings (with or without trailing `Z`), trying `datetime.fromisoformat` first after `Z`→`+00:00` normalization, then falling back to `datetime.fromtimestamp`. The fetcher at `etf_quote.py:50-51` keeps its existing preference order (`regularMarketTime` then `preMarketTime` then `postMarketTime`); it just passes whichever wins to `epoch_to_iso`.

**Why centralized:** every fetcher that touches a time field funnels through this helper; tolerating both shapes here means future fetchers can't reintroduce this drift. Alternative considered — parsing the ISO string explicitly inside `etf_quote.py` — would work but duplicates the helper for one caller.

### D2. Keep the preference chain for `etf_quote` time source

`ts_epoch = raw.get("regularMarketTime") or raw.get("preMarketTime") or raw.get("postMarketTime")` is still the right set of fields to try. `regularMarketTime` is what carries the regular-session close timestamp (the row was stamped at `"2026-07-02 20:00:01"` even though the live fetch happened at 01:37 UTC). The fact that the field is now a string instead of an epoch is a `yahooquery` library change, not a contract change — the *meaning* of the field is the same.

**Alternative considered:** use `datetime.now(UTC)` as the `ts` instead. Rejected — the upstream field is meaningful and authoritative; falling back to "now" would mean different symbols could land in the same batch with slightly different timestamps, and re-pushes would create dedup misses on `(symbol, ts)`.

### D3. Path C — stub news out by removing the scheduler entry, not the table or module

We:
- Remove the `make_fetch_job("etf_news", ...)` registration from `build_scheduler`.
- Remove `etf_news` from `_FETCH_TABLE` so `safe_run` can no longer route to `fetch_news`.
- Keep `fetch_news` module, `insert_etf_news` helper, and `etf_news` table — so a future change can plug a new source back in with minimal churn.
- Update `safe_run` to remove the `since=None` special case for `etf_news`.

**Why not delete `fetch_news.py` outright:** it's referenced by the existing test module (`test_fetch_news_shape`) and removing it requires also updating those tests. Keeping the module behind a thin `__all__`/comment that says "parked" preserves the test contract and makes future revival a low-friction revert of a few lines.

**Why not delete the `etf_news` table:** schema migrations are a separate concern; the table is harmless if empty, and the push loop iterates `local_db.all_business_tables()` so an empty table incurs zero cost.

### D4. Drop `fetch_news_interval_minutes` from Config (and from the env example)

If the news fetch is no longer scheduled, the config knob is dead weight. Remove it from `Config` and from `remote_data/.env.example` so future ops don't see a knob that doesn't do anything.

**Alternative considered:** leave it as "unused but documented for revival." Rejected — leaving dead knobs in config drifts toward "what does this do?" later.

### D5. Update `_FakeTicker` fixture to match real API shape, add a regression test

The existing `_FakeTicker.price` returns `regularMarketTime: 1751200000` (integer epoch). Real yahooquery returns it as `"2026-07-02 20:00:01"`. Update the fixture to the string shape so the live-shape contract is exercised in CI. Add a regression test that calls `epoch_to_iso` directly with both shapes and asserts the result.

**Why update the fixture rather than add a second fixture:** one canonical shape per test file is simpler; if yahooquery ever flips back, the test breaks loudly and we revisit.

## Risks / Trade-offs

- **[Risk] yahooquery could flip `regularMarketTime` back to an integer epoch.** → `epoch_to_iso`'s fallback path still handles ints/floats; the helper is dual-shape on purpose. No regression possible.
- **[Risk] some yahooquery symbols might return `regularMarketTime` as `None` (no trading data).** → unchanged behavior: `ts_iso = None`, the record fails `ts NOT NULL`, batch is lost (pre-existing fragility). Out of scope for this change; flag for a follow-up hardening task.
- **[Risk] removing `etf_news` fetch job could surprise ops dashboards.** → `fetch_log` already shows the misleading `status=ok row_count=0` entries; the change makes them go away. Document in CHANGELOG / runbook that `etf_news` is parked.
- **[Risk] a future change that wants news will need to remember how to re-enable it.** → leave a `# PARKING:` comment block at the top of `fetch_news.py` and at the now-removed `etf_news` lines in `jobs.py` referencing this OpenSpec change, so a search lands on the rationale.
- **[Risk] `_FakeTicker` change could break the existing `test_fetch_quotes_shape` if the assertion is tight on type.** → read the assertion before changing the fixture; adjust if needed (likely the assertion only checks the parsed `ts_iso` output, which is identical regardless of input shape).
- **[Trade-off] dual-shape `epoch_to_iso` slightly increases the helper's surface area.** → acceptable; the alternative (forcing every caller to normalize) duplicates logic and regresses under future drift.

## Migration Plan

1. Land the code changes in a single PR (`fix-quote-and-news`).
2. CI: `python3 -m pytest remote_data/ -v` must show 50 (existing) + N (new regression) passed.
3. Deploy: `cd remote_data && ./stop-fetcher.sh && ./start-fetcher.sh` (no systemd — see [[deploy-no-systemd]]). Within 90 seconds the daemon should:
   - fire `fetch_quotes` successfully → `etf_quote` rows begin landing,
   - fire `push_loop` → first `etf_quote` batch hits the domestic node and returns 200.
4. Verify with the same SQL probes from this exploration:
   ```sql
   SELECT data_type, COUNT(*) FROM push_log
     WHERE sent_at > datetime('now', '-1 day')
     GROUP BY data_type;
   SELECT COUNT(*), COUNT(pushed_at) FROM etf_quote;
   ```
   Expect `etf_quote` to appear in both, with `pushed` close to `total`.
5. Confirm no `etf_news` activity in `fetch_log` after deployment.
6. Rollback: revert the single PR; `etf_quote` reverts to the previous broken behavior, no data corruption.

## Open Questions

- (Resolved in D4) Should the `fetch_news_interval_minutes` env knob be kept for revival? — **No, drop it.**
- (Resolved in D3) Should the `etf_news` table be dropped? — **No, keep it.**
- (Deferred) Should `_insert_records` be hardened to skip-and-warn on bad rows instead of failing the whole batch? — **Yes, but separately.** Tracked under `etf-local-store` capability, future change.
- (Deferred) Should we pick a new news source? — **Yes, but separately.** Tracked as a future change. Candidates: Google News RSS (no key), Finnhub (free tier), Alpha Vantage (free tier), NewsAPI (free tier).