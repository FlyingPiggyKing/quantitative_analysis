## Context

Today the stock detail page at `/stock/[symbol]` renders header valuation chips (PE / PB / 换手 / 市值) from a single source: `/api/stock/{symbol}/valuation`. For US symbols (1–5 letters, matched by `_is_us_stock_symbol`) that endpoint delegates to `FutuQuoteService.get_daily_basic`, which composes a time-series from Futu's `request_history_kline` (pe_ratio per bar) and an `is_etf`-unaware snapshot (`pe_ttm_ratio`, `pb_ratio`, `total_market_val`, `turnover_rate`). This works for stocks. For US ETFs the data is sometimes thin and—more importantly—omits dividend fields that the rest of the ETF pipeline already collects.

Meanwhile the ETF ingest pipeline (`remote_data/`) writes a row per ingest into `etf_remote.db.etf_fundamentals` with `{symbol, as_of, pe, pb, dividend_yield, dividend_rate}` sourced from yahooquery (`trailingPE`, `dividendYield`, `dividendRate`). `GET /api/etf/fundamentals/{symbol}` already returns this payload. The frontend never calls it.

This change wires those two worlds together at the existing `/api/stock/{symbol}/valuation` endpoint, with the "is this an ETF?" decision made dynamically from the database. No new endpoint, no frontend list, no schema migration.

## Goals / Non-Goals

**Goals:**
- `/api/stock/{symbol}/valuation` returns an ETF-aware enriched response for US symbols that have rows in `etf_fundamentals`.
- The ETF set is determined dynamically by `SELECT DISTINCT symbol FROM etf_fundamentals`, cached in-memory; no hardcoded list anywhere in the codebase.
- Non-ETF US stocks, A-share, and HK responses are byte-identical to today.
- Frontend stays dumb: a single fetch, the same `valuation.pe_ttm` it already reads, plus two new optional chips when the response says `is_etf`.

**Non-Goals:**
- Changes to `remote_data/` (pusher, fetcher, schema, ETL).
- Verifying that the current `pe` column holds strict TTM (vs. the latent risk of the fetcher's `forwardPE` fallback). Tracked elsewhere.
- HK ETFs (no HK data in `etf_fundamentals` today).
- Broader ETF-aware UI redesign on the stock detail page (company-info, main-business, shareholders panels).
- Changing `GET /api/etf/fundamentals/{symbol}` or other existing `/api/etf/*` endpoints.
- Changing the `batch/valuation` endpoint (would re-apply the merge for batch callers; deferred).

## Decisions

### 1. Branch in `USStockService.get_daily_basic`, not at the API route

The existing route `GET /api/stock/{symbol}/valuation` already dispatches by market in `backend/api/stock.py:476-484` (HK / US / A-share). Putting the ETF merge inside `USStockService.get_daily_basic` keeps the cross-cutting concern co-located with the other US-specific logic and means the existing batch endpoint can opt in later by mirroring the same wrapper, without changing the route.

**Alternative considered**: branch inside `FutuQuoteService.get_daily_basic` (one level deeper). Rejected — couples Futu to ETF semantics; would require Futu to know about `etf_remote.db`. The current split (Futu = quote protocol, akshare_service = market-specific orchestration) is the right boundary.

**Alternative considered**: branch in the API route. Rejected — leaks market-specific knowledge into the route handler and would duplicate for the batch endpoint.

### 2. Dynamic ETF symbol set, cached in a module-level `Set[str]`

`is_etf(symbol)` reads from a module-level cache populated by `_load_etf_symbols()`, which executes `SELECT DISTINCT symbol FROM etf_fundamentals` once and stores uppercased symbols in a `set[str]` for O(1) membership tests. The set is ~17 symbols today and grows slowly (one entry per ingested ETF), so re-reading on first request is negligible.

**Alternative considered**: query `etf_fundamentals` per request. Rejected — adds a SQLite hit to every US-stock valuation (every page load for non-ETF US stocks). The cache turns the hot path back into a single in-memory `in` check.

**Alternative considered**: hardcoded `US_ETF_SYMBOLS` list (the first sketch). Rejected — drifts from the database and creates two sources of truth for "what is an ETF". The whole point of putting the logic in the backend is to make the database the single source.

**Alternative considered**: scheduled refresh (cron-like). Deferred — for ~17 symbols with ingests happening minutes apart, lazy-load + `refresh_etf_symbols()` callable from the pusher is enough. If pusher-coordinated invalidation proves brittle, add a TTL or admin-endpoint-driven refresh.

### 3. Response shape: add fields, don't replace

The merged response keeps every existing key. For ETFs we additionally:
- add top-level `is_etf: true`
- override `latest.pe_ttm` with `etf_fundamentals.pe`
- override `latest.pb` with `etf_fundamentals.pb` when present
- add `latest.dividend_yield`, `latest.dividend_rate`, `latest.as_of`

For non-ETFs we still emit `is_etf: false` and `dividend_yield: null` / `dividend_rate: null` so the TypeScript shape is uniform across both branches. Historical `data[]` rows stay untouched — they remain Futu's time series for both branches.

**Alternative considered**: only emit the new keys for ETFs (omit `is_etf` when false). Rejected — forces the frontend to branch on key presence rather than value, which TypeScript interfaces don't model cleanly.

**Alternative considered**: a separate `/api/stock/{symbol}/valuation-etf` endpoint. Rejected — splits the truth across two routes and forces the frontend to choose which to call (back to the hardcoded-list problem).

### 4. ETF merge happens for symbols with or without a current row

`etf_service.get_fundamentals(symbol)` returns the most recent row (`ORDER BY as_of DESC LIMIT 1`). If a symbol is in the cached ETF set but the latest row is missing or has all-null fields, we still emit `is_etf: true` and leave the dividend / PE override fields null. This keeps the UI stable (still shows the chips) rather than toggling between branches on data freshness.

### 5. Frontend: extend interfaces, conditional render, no new fetch

The page's existing `Promise.all` already includes `fetchStockValuation(symbol, 100)`. We extend `ValuationRecord` / `ValuationResponse` in `frontend/src/services/stock.ts` with optional fields (`is_etf`, `dividend_yield`, `dividend_rate`, `as_of`). The page renders two new chips (`股息率`, `年股息`) immediately after the existing `市值` chip, gated on `valuation?.is_etf`. The PE chip itself is unchanged — it already reads `valuation.pe_ttm`, which is now sourced from yahooquery for ETFs without any frontend code change.

**Alternative considered**: a separate `useEffect` to call `/api/etf/fundamentals/{symbol}` directly. Rejected — duplicates work the backend now does, and reintroduces the question of "how does the frontend know it's an ETF".

### 6. `USStockService.get_daily_basic_batch` left unchanged

`/api/stock/batch/valuation` (used for watchlist / index-metrics / sector-top-stocks callers) still calls `FutuQuoteService.get_daily_basic_batch` directly. For now, batch callers will see Futu-sourced PE for ETFs. Mirroring the merge there is a follow-up if any batch caller starts mixing ETFs in.

## Risks / Trade-offs

- **Cache staleness after pusher ingest** → Lazy-load on first request. Provide `etf_valuation.refresh_etf_symbols()` for the pusher (or an admin endpoint) to call after each successful ingest. Worst case if not wired: a newly ingested ETF symbol takes effect after the next backend restart.
- **Latent `forwardPE` leakage in `pe` column** → Out of scope. Documented in proposal as a known limitation; the fetcher prefers `trailingPE` but will fall back to `forwardPE`. A separate change would either make the fetcher strict (`_f(["trailingPE"])` only) or split `pe_ttm` / `pe_forward` columns. Until then, an exotic ETF whose `trailingPE` is null could have a forward-PE value labeled as TTM by our backend.
- **404 in `etf_service.get_fundamentals` for an ETF-symbol-in-cache** → Treated as missing data: `is_etf: true` is still emitted but the dividend fields and PE override are null. UI degrades to Futu-sourced PE with empty chips. Document this fallback in the spec.
- **`batch/valuation` inconsistency** → Mitigated by an explicit non-goal statement. Document in the spec so future batch callers know ETFs there are Futu-sourced.
- **Schema change in `etf_fundamentals` later would break the cache loader** → The cache loader reads `symbol` only. If new columns are added, no change needed; if `symbol` is renamed, the loader fails fast on the next `is_etf()` call (acceptable; clear error).
- **Two calls (`etf_remote.db` for ETF row, Futu for snapshot) per ETF valuation request** → One extra SQLite read per ETF page load. Single-row lookup on the primary key — negligible. Non-ETF path is unchanged (no `etf_remote.db` hit once cache is warm).
- **Stock detail page still renders 主营业务 / shareholders / company-info for ETFs** → Out of scope; these panels are wrong for ETFs but already exist today. The narrow step does not make them worse.

## Migration Plan

No schema migration, no data backfill, no feature flag. Deploy is a normal backend + frontend rollout:

1. Merge backend change (`etf_valuation.py` new + `akshare_service.py` edit). Restart backend; cache warms on first request.
2. Merge frontend change (`stock.ts` interface + `page.tsx` chip rendering). Rebuild + redeploy frontend.
3. Verify on `/stock/QQQ`: PE shows yahooquery value (33.30 from sample), `股息率` and `年股息` chips appear with values from `etf_fundamentals`. Verify on `/stock/AAPL`: header unchanged (no ETF chips, PE still Futu-sourced).
4. Verify `batch/valuation` callers (watchlist, index metrics) still return Futu-sourced numbers — no behaviour change for them in this release.

**Rollback**: revert the two backend commits + two frontend commits. No data persisted; the in-memory cache goes away on backend restart. No cleanup needed.

## Open Questions

- Should `is_etf: true` be emitted for ETFs whose `etf_service.get_fundamentals` returns `None`? Current decision: yes, with null dividend/override fields. UI stable, but the chips render empty. Alternative: only emit `is_etf: true` when the row exists — but this toggles the UI based on data freshness rather than symbol identity.
- Should the frontend surface `latest.as_of` (yahooquery fetch timestamp) as a freshness indicator? Cheap to add (tooltip on the PE chip); not in scope unless requested.
- Should `refresh_etf_symbols()` be invoked from the pusher on every successful ingest, from an admin endpoint, or from a TTL-based cache? Defer until cache staleness is observed in practice.
- Should `batch/valuation` mirror the merge? Currently deferred. The deciding factor is whether any batch caller actually mixes ETFs in.