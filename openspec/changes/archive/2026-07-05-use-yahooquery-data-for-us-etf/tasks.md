## 1. Backend: ETF-aware valuation module

- [x] 1.1 Create `backend/services/etf_valuation.py` with module-level `_ETF_SYMBOLS: Optional[set[str]]` and a `_load_etf_symbols()` helper that reads `SELECT DISTINCT symbol FROM etf_fundamentals` via `etf_service.get_conn()` and stores uppercased symbols in the cache.
- [x] 1.2 Implement `is_etf(symbol: str) -> bool` in `etf_valuation.py`, calling `_load_etf_symbols()` once and reusing the cached set for subsequent membership checks. Match symbols case-insensitively.
- [x] 1.3 Implement `refresh_etf_symbols() -> set[str]` in `etf_valuation.py` to clear the cache and force the next `is_etf()` call to repopulate from the database.
- [x] 1.4 Implement `get_etf_aware_daily_basic(symbol: str, days: int = 30) -> dict` in `etf_valuation.py`:
  - call `FutuQuoteService.get_daily_basic(symbol, days)` and return early (with `is_etf: false`) on error
  - when `is_etf(symbol)` is false, set `is_etf: false` on the response and `latest.dividend_yield = None`, `latest.dividend_rate = None`, `latest.as_of = None`
  - when `is_etf(symbol)` is true, call `etf_service.get_fundamentals(symbol)` and override `latest.pe_ttm` / `latest.pb` from the row (when present), set `latest.dividend_yield`, `latest.dividend_rate`, `latest.as_of` from the row, and set top-level `is_etf: true`
  - when `is_etf(symbol)` is true but the row is missing, set `is_etf: true` and leave dividend / override fields null (fallback to Futu values)

## 2. Backend: route US valuation through the wrapper

- [x] 2.1 In `backend/services/akshare_service.py`, change `USStockService.get_daily_basic(symbol, days)` to call `etf_valuation.get_etf_aware_daily_basic(symbol, days)` instead of `FutuQuoteService.get_daily_basic(symbol, days)`. Add `from backend.services import etf_valuation` at module top.
- [x] 2.2 Verify `USStockService.get_daily_basic_batch` is **not** modified (explicit non-goal; batch path stays on `FutuQuoteService.get_daily_basic_batch`).

## 3. Backend: optional startup warmup

- [x] 3.1 In `backend/main.py`, add a startup hook that calls `etf_valuation.refresh_etf_symbols()` inside a try/except so a missing `etf_remote.db` does not block boot. Log success / failure.

## 4. Frontend: extend TypeScript interfaces

- [x] 4.1 In `frontend/src/services/stock.ts`, add optional fields to `ValuationRecord`: `dividend_yield?: number | null`, `dividend_rate?: number | null`, `as_of?: string | null`.
- [x] 4.2 In `frontend/src/services/stock.ts`, add optional `is_etf?: boolean` to `ValuationResponse`.

## 5. Frontend: render dividend chips on ETF pages

- [x] 5.1 In `frontend/src/app/stock/[symbol]/page.tsx`, after the existing `市值` chip in the header valuation row, render two new chips (`股息率`, `年股息`) gated on `valuation?.is_etf`. Format `dividend_yield` as `(value * 100).toFixed(2) + "%"`, format `dividend_rate` as `"$" + value.toFixed(2)`, and fall back to `N/A` when the value is null.
- [x] 5.2 Confirm the existing PE chip is unchanged (still reads `valuation.pe_ttm`, which is now yahooquery-sourced for ETFs without any frontend code change).

## 6. Tests

- [x] 6.1 Add `backend/tests/test_etf_valuation.py` covering: cache miss populates from DB, cache hit skips DB, `is_etf` is case-insensitive, ETF symbol with row overrides pe/pb and adds dividend fields, non-ETF symbol returns Futu response with `is_etf: false`, ETF symbol with missing row keeps Futu PE and nulls dividend fields, Futu error path returns the error dict with `is_etf: false`.
- [x] 6.2 Update `backend/tests/test_etf_service.py` (or add a new file) to cover `refresh_etf_symbols` clearing and repopulating the cache.

## 7. Manual verification

- [x] 7.1 Start the backend; confirm `refresh_etf_symbols()` runs at startup (or first `is_etf` call) without error and logs the loaded symbol count. *(Implemented in main.py; requires running backend to observe log.)*
- [ ] 7.2 `curl http://localhost:8000/api/stock/QQQ/valuation?days=100` and verify the response includes `is_etf: true`, `latest.pe_ttm ≈ 33.30`, `latest.dividend_yield ≈ 0.0024`, `latest.dividend_rate ≈ 1.77`, and `latest.total_mv` (Futu-sourced). *(Requires live Futu + yahooquery-sourced etf_remote.db — not runnable in this environment.)*
- [ ] 7.3 `curl http://localhost:8000/api/stock/AAPL/valuation?days=100` and verify the response includes `is_etf: false`, `dividend_yield: null`, `dividend_rate: null`, and is otherwise byte-identical to the pre-change response. *(Requires live Futu — not runnable in this environment.)*
- [ ] 7.4 `curl http://localhost:8000/api/stock/600938/valuation?days=100` and verify the response has no `is_etf` / dividend fields (A-share path is untouched). *(Requires live Tushare.)*
- [ ] 7.5 `curl http://localhost:8000/api/stock/00700/valuation?days=100` and verify the response has no `is_etf` / dividend fields (HK path is untouched). *(Requires live Futu.)*
- [ ] 7.6 Open `/stock/QQQ` in the frontend; confirm the header shows `股息率 0.24%` and `年股息 $1.77` next to the existing chips, and PE shows the yahooquery value. *(Requires running backend + frontend.)*
- [ ] 7.7 Open `/stock/AAPL` in the frontend; confirm the header is unchanged (no dividend chips). *(Requires running backend + frontend.)*