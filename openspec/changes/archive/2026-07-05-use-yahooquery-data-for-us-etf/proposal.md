## Why

The `etf_remote.db` ETL pipeline already pulls US ETF fundamentals (PE, PB, dividend_yield, dividend_rate) from yahooquery into `etf_fundamentals`, and the read endpoint `GET /api/etf/fundamentals/{symbol}` already exposes them — but the stock detail page never reads from it. When a user opens `/stock/QQQ`, the page renders PE/PB sourced exclusively from Futu's snapshot (`pe_ttm_ratio`, `pb_ratio`), and dividend fields are not displayed at all. This change wires the existing yahooquery-sourced ETF fundamentals into the stock detail page, so US ETF pages show the same metrics the rest of the ETF pipeline already collects.

## What Changes

- **Backend (Python, dynamic)**: Introduce a new `etf_valuation` service module that wraps `FutuQuoteService.get_daily_basic` and merges `etf_fundamentals` fields into the response when the requested symbol is recognised as an ETF. The "is this an ETF?" decision is **dynamic** — the symbol set is loaded from `SELECT DISTINCT symbol FROM etf_fundamentals` and cached in-memory at startup; no hardcoded list. The ETF branch is owned by `USStockService.get_daily_basic`; A-share and HK paths are untouched.
- **Backend response shape**: `/api/stock/{symbol}/valuation` gains three new optional fields when the symbol is an ETF:
  - top-level `is_etf: bool`
  - `latest.dividend_yield: float | null` (decimal, e.g. `0.0024` = `0.24%`)
  - `latest.dividend_rate: float | null` (annual dividend per share in USD)
  - `latest.as_of: string | null` (yahooquery fetch timestamp)
  - For ETFs, `latest.pe_ttm` is sourced from `etf_fundamentals.pe` instead of Futu. `pb`, `total_mv`, `turnover_rate`, and the historical `data` series continue to come from Futu.
- **Frontend (minimal)**: Extend `ValuationRecord` / `ValuationResponse` in `frontend/src/services/stock.ts` with the new optional fields. In `frontend/src/app/stock/[symbol]/page.tsx`, render two new header chips ("股息率", "年股息") conditional on `valuation.is_etf`. PE chip is unchanged (still reads `valuation.pe_ttm`, which is now yahooquery-sourced for ETFs).
- **Out of scope** (explicitly deferred):
  - Changes to `remote_data/` (the pusher, the fetcher, or the `etf_remote.db` schema).
  - Verifying that the `pe` column currently holds strict TTM and not forward PE (the existing fetcher prefers `trailingPE` but falls back to `forwardPE`; a separate change would address this).
  - HK ETFs (the `etf_fundamentals` table is US-only today).
  - Broader ETF-aware UI redesign on the stock detail page (company-info panel, main-business panel, shareholders panel behaviour for ETFs).
  - Changes to `GET /api/etf/fundamentals/{symbol}` (already exists and works).

## Capabilities

### New Capabilities

- `etf-aware-stock-valuation`: US ETF symbols are detected dynamically from `etf_remote.db`, and their valuation response merges `etf_fundamentals` data (PE, dividend fields) with Futu-sourced market data (PB, total_mv, turnover_rate, historical PE series). Non-ETFs are unchanged.

### Modified Capabilities

- `stock-valuation-metrics`: The valuation response gains optional `is_etf`, `dividend_yield`, `dividend_rate`, and `as_of` fields. For ETFs, `pe_ttm` is sourced from `etf_fundamentals` instead of Futu. Existing fields and the response shape for non-ETFs are unchanged.
- `us-stock-data`: `USStockService.get_daily_basic` now delegates to an ETF-aware wrapper instead of calling Futu directly. Non-ETF US stocks behave identically.

## Impact

- **Backend code**:
  - New: `backend/services/etf_valuation.py` (~70 lines: dynamic symbol-set cache, `is_etf()`, `get_etf_aware_daily_basic()`, `refresh_etf_symbols()`).
  - Edit: `backend/services/akshare_service.py` — `USStockService.get_daily_basic` delegates to the new wrapper. `USStockService.get_daily_basic_batch` is unchanged in this change.
  - Optional: warm cache at backend startup (`backend/main.py` startup hook).
- **Frontend code**:
  - Edit: `frontend/src/services/stock.ts` — extend `ValuationRecord` / `ValuationResponse` interfaces.
  - Edit: `frontend/src/app/stock/[symbol]/page.tsx` — add two conditional chips next to the existing header valuation row.
- **No new endpoints**, no schema migration, no changes to `remote_data/`, no changes to the existing `/api/etf/*` routes.
- **Backward compatibility**: clients that ignore unknown fields keep working. Existing `pe_ttm`, `pb`, `total_mv`, `turnover_rate` semantics for non-ETFs are byte-identical to today.
- **Performance**: one extra SQLite query per US-stock valuation request (single-row lookup by symbol on the primary key `(symbol, as_of)` with `ORDER BY as_of DESC LIMIT 1`). The ETF-symbol-set is cached in-memory after first load.