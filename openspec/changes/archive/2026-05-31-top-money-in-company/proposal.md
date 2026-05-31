## Why

In the 资金流向 (money flow) sub-module, users can click an inflow line in the sector Sankey chart to highlight an industry (the "已选中: 白酒" block). Today that selection only highlights the chart — it gives no insight into *which companies* drove that industry's inflow. Users want to drill from "this industry had inflow on 5/29 and 5/27" down to "these are the top companies that received that inflow on each day."

## What Changes

- When a sector is selected in `SectorMoneyFlowSankey` (via clicking a flow line or legend), show a new panel directly below the "已选中" block listing, for each trading day that sector appears in the chart, the top 5 companies by main-force net inflow that day.
- Add a backend endpoint that, given a sector name and a set of trade dates, resolves the sector to its SW2021 member stocks, computes each member's main-force net inflow per date, and returns the top N companies per date with their names, PE(TTM), and market cap (市值).
- Resolve the DC sector name shown in the chart to an SW2021 industry code via `index_classify` (with roman-numeral normalization and best-effort name matching), then fetch members via `index_member` and per-stock flow via `moneyflow`, and company names via `stock_basic`.
- Add caching for the new per-date `moneyflow` table, the SW2021 classification table, per-index member lists, and the `stock_basic` name map to keep within Tushare rate limits.

## Capabilities

### New Capabilities
- `sector-top-inflow-stocks`: On sector selection in the money-flow Sankey, display the top N companies by main-force net inflow for each trading day the sector appears, backed by a new API that maps the chart's sector name to SW2021 members and ranks per-stock money flow.

### Modified Capabilities
<!-- No existing spec's requirements change; the new panel is additive to the existing chart behavior. -->

## Impact

- **Frontend**: `frontend/src/components/SectorMoneyFlowSankey.tsx` (render the panel on selection), new `frontend/src/components/SectorTopStocksPanel.tsx`, new `frontend/src/services/sectorTopStocks.ts`.
- **Backend**: new route in `backend/api/stock.py` (`GET /api/stock/sector-top-stocks`), new method(s) in `backend/services/akshare_service.py` (sector→SW resolution, member lookup, per-date money-flow ranking), plus module-level caches following the existing `_sector_mf_cache` pattern.
- **External APIs (Tushare)**: adds usage of `index_classify`, `index_member`, `moneyflow`, `stock_basic`, and `daily_basic`. No new Python dependencies.
- **Risk**: DC (chart) ↔ SW2021 (member lookup) taxonomies differ; some sector names may not map cleanly. Handled with normalization + best-effort matching and a graceful "no match" state (documented in design.md).
