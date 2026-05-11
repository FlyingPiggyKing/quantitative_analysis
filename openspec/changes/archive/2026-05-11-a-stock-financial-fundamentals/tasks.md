## 1. Backend: Service & API

- [x] 1.1 Add `get_financial_fundamentals(symbol)` method to `AShareService` in `backend/services/akshare_service.py` calling Tushare `fina_indicator` and `income` tables
- [x] 1.2 Add `GET /api/stock/{symbol}/fundamentals` endpoint to `backend/api/stock.py` with A-share check (6-digit symbol validation) and "暂不适用" error for HK/US symbols
- [x] 1.3 Test endpoint with A-share symbol `000001.SZ` to verify data returns

## 2. Frontend: Component

- [x] 2.1 Create `FinancialIndicatorsPanel.tsx` component mirroring `IndicatorPanel` style: collapsible block, 4-column grid, `GroupTitle` and `Cell` sub-components
- [x] 2.2 Display these 13 fields: `end_date`, `eps`, `bps`, `roe`, `roe_yearly`, `gross_margin`, `netprofit_margin`, `basic_eps_yoy`, `netprofit_yoy`, `tr_yoy`, `debt_to_assets`, `current_ratio`, `total_revenue`, `n_income`
- [x] 2.3 Handle loading state (skeleton loader), error state ("暂不适用"), and null field values (show `--`)

## 3. Frontend: Integration

- [x] 3.1 Add `fundamentals` state to `StockDetailPage` component
- [x] 3.2 Fetch data from `GET /api/stock/{symbol}/fundamentals` (non-blocking, parallel with other data fetches)
- [x] 3.3 Import and render `FinancialIndicatorsPanel` as standalone block below "AI趋势分析", wrapped in A-share check (`/^\d{6}$/.test(symbol)`)
- [x] 3.4 Test with A-share symbol `000001.SZ` and US symbol `US.AAPL` (latter should show "暂不适用")

## 4. Post-Implementation Fixes

- [x] 4.1 Fix `gross_margin` data error: Tushare returns gross profit in 元 (not %) for quarterly reports. Added heuristic: if value > 1000, compute as `(gross_margin / revenue) × 100`
- [x] 4.2 Add `report_label` derived from `end_date` period (0331→一季报, 0630→半年报, 0930→三季报, 1231→年报) displayed in panel header
- [x] 4.3 Add `ann_date` displayed as "YYYY-MM-DD发布" in panel header
- [x] 4.4 Wrap `income` API call in `try/except` so rate limit errors don't break the entire endpoint; `fina_indicator` data still returns on `income` failure
- [x] 4.5 Test with `300274` (阳光电源 Q1 2026) to verify `gross_margin = 33.26%` (was 5,175,926,820.42% before fix)
