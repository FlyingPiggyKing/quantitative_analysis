## 1. Backend — sector resolution & money-flow ranking

- [x] 1.1 In `backend/services/akshare_service.py`, add module-level caches mirroring `_sector_mf_cache`: `_sw_classify_cache` (daily), `_index_member_cache` (daily, keyed by index_code), `_stock_basic_name_cache` (daily), `_moneyflow_day_cache` (keyed by trade_date, long TTL for closed days).
- [x] 1.2 Add `_get_sw_classify()` that fetches and caches the full `index_classify(src='SW2021')` table (L1+L2+L3) once per day. Uses `industry_name` column (not `name`).
- [x] 1.3 Add `_resolve_sector_to_sw(name)` that normalizes the DC sector name (trim whitespace + strip trailing roman-numeral variants using the existing regex pattern) and matches it to an SW2021 `index_code`: exact normalized match → L2 normalized match → substring containment; prefer deepest unambiguous level. Return `(index_code, matched_name)` or `(None, None)`.
- [x] 1.4 Add `_get_index_members(index_code)` that fetches and caches member `ts_code` list via `index_member`.
- [x] 1.5 Add `_get_moneyflow_day(trade_date)` that fetches `moneyflow(trade_date=YYYYMMDD, fields='ts_code,buy_elg_amount,sell_elg_amount,buy_lg_amount,sell_lg_amount,net_mf_amount')`, builds `{ts_code: net_inflow_in_yi}` where `net_inflow = ((buy_elg-sell_elg)+(buy_lg-sell_lg))/10000`, and caches it per date. Detect Tushare permission/rate-limit errors (reuse existing "权限"/"每分钟"/"Connection" detection) and propagate a clear error.
- [x] 1.6 Add `_get_stock_names(ts_codes)` that resolves codes to company names via cached `stock_basic(fields='ts_code,name')`.
- [x] 1.7 Add `_get_stock_basics(trade_date)` that fetches `daily_basic(trade_date=YYYYMMDD, fields='ts_code,pe_ttm,total_mv')`, returns `{ts_code: {pe_ttm, total_mv_yi}}` where `total_mv_yi = total_mv / 1e4` (元 → 万亿). Caches per date with long TTL for closed days.
- [x] 1.8 Add `AShareService.get_sector_top_stocks(sector, dates, top_n=5)` orchestrating: resolve sector → members → for each date build ranked top_n member companies with names, `net_inflow`, `pe_ttm`, and `total_mv_yi` (亿元, sorted desc by net_inflow). Return `{sector, index_code, matched_name, by_date, error}`. Empty `by_date` + `error` when no SW match or money-flow unavailable.

## 2. Backend — API endpoint

- [x] 2.1 In `backend/api/stock.py`, add `GET /api/stock/sector-top-stocks` BEFORE the `/{symbol}` route, with query params `sector: str`, `dates: str` (comma-separated YYYY-MM-DD), `top_n: int = Query(default=5, ge=1, le=20)`; parse dates and call `AShareService.get_sector_top_stocks`.
- [ ] 2.2 Manually verify the endpoint with `curl` for a known sector (e.g. `白酒`) and recent dates: confirm `by_date` returns ranked companies with names, 亿元 net inflow, PE, and 市值, and that an unmatchable sector returns `error` with empty `by_date`.

## 3. Frontend — service & panel

- [x] 3.1 Create `frontend/src/services/sectorTopStocks.ts` with a `StockTopInfo` type (`ts_code`, `name`, `net_inflow`, `pe_ttm`, `total_mv_yi`) and `SectorTopStocksResponse` (`sector`, `index_code`, `matched_name`, `by_date: Record<string, StockTopInfo[]>`, `error?`). `fetchSectorTopStocks(sector, dates, top_n=5)` calls the new endpoint.
- [x] 3.2 Create `frontend/src/components/SectorTopStocksPanel.tsx` that takes `sector` and `dates: string[]`, fetches on change, and renders per-date groups (newest first) of ranked companies with columns: #, 名称/代码 (mobile: stacked), PE(TTM), 市值 (≥10000亿 displayed as 万亿), 主力净流入 (signed, brass/oxblood coloring). Loading, empty/no-match (无法匹配到申万行业成分股), and error states included.

## 4. Frontend — wire into chart

- [x] 4.1 In `frontend/src/components/SectorMoneyFlowSankey.tsx`, after the "已选中" block (after line 432), render `SectorTopStocksPanel` when `highlightedSector` is set, passing `highlightedSector` and the dates that sector appears in (derived from `data.daily_top`).
- [ ] 4.2 Confirm the panel updates correctly on select / re-select / deselect, and that selecting via both flow-line click and legend click trigger it.

## 5. Verify

- [ ] 5.1 Run the backend (`uv` venv from `backend/`) and frontend; click a sector with multiple inflow dates (e.g. 白酒) and confirm the panel shows each date's top 5 companies with name, code, PE, 市值 (万亿), and net inflow (亿元) matching the chart's dates.
- [ ] 5.2 Verify units: net inflow displays in 亿元 (万元 → /10000), 市值 ≥10000亿 displays as 万亿 (e.g. 1.29万亿), signs render with `+`/`-`, and a sector that cannot map to SW2021 shows the no-match message without errors.
