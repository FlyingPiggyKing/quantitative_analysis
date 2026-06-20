## Context

- The `us-hk-main-business-composition` change established the pattern for Futu-backed HK/US panels: a `FutuQuoteService.<method>(symbol)` classmethod, a delegation on `HKStockService` / `USStockService`, an HTTP route under a sibling path, and a new conditional branch in the existing `<MainBusinessPanel />` driven by a `market` prop. This change follows the same pattern with a brand-new component file (because the data shape and the visual layout diverge enough that reusing `MainBusinessPanel` is no cleaner than a separate component).
- Futu's `OpenQuoteContext` exposes four `get_shareholders_*` methods (verified in `backend/.venv/lib/python3.11/site-packages/futu/quote/open_quote_context.py:3600,3651,3704,3762`). The Tencent (HK.00700) live call confirmed that:
  - `get_shareholders_overview` returns a 3-sub-table dict (`main_holder` 6 rows, `holder_type` 10 rows, `holding_period` 20 rows) and is the only way to get a `period_id` for the detail endpoint.
  - `get_shareholders_institutional` paginates 10 periods per page; cursor is a timestamp string shared across all rows on a page; 3 pages yield 30 periods (~7.5 years).
  - `get_shareholders_holder_detail` paginates 20 rows per page by an offset integer exposed as `df.attrs['next_key']`. The `holder_id` query parameter enables per-holder cross-period drill-down (Prosus: 20 periods returned with attrs.next_key='20').
  - `get_shareholders_holding_changes` paginates 20 rows per page by offset; `filter_type=1` returns increases, `filter_type=2` returns decreases; the SDK does NOT support `holder_id` on this endpoint.
- `CLAUDE.md` documents the project conventions: HK currency is HKD, US currency is USD, market cap / turnover-rate unit conversions are documented. The `us-hk-main-business-composition` change established the pattern of returning raw Futu values (not pre-divided) and letting the frontend convert to 亿元 with currency suffix.
- Frontend stack: Next.js app router, Tailwind, project-local conventions captured in `AGENTS.md` ("This is NOT the Next.js you know") — any new component code must consult `frontend/node_modules/next/dist/docs/` first.
- No database, no Redis. In-memory caches only. Futu caches live at `backend/services/futu_quote_service.py` (`_futu_cache` and `_company_info_cache`); A-share caches live at `backend/services/akshare_service.py`. The 24h `_company_info_cache` is the right home for quarterly disclosure data.
- Existing UI primitives in scope: `SubModuleTabs.tsx` (tab UI for the 4 internal sub-tabs), `ModuleTabs.tsx` (top-level page tabs), `MainBusinessPanel.tsx` (45KB reference for stacked bar, 海外 badge, by-period column chart), `StockChart.tsx` (lightweight-charts wrapper for the K-line). For the new component we will **not** introduce a chart library — a custom SVG line+bar chart is sufficient for 30 data points and avoids pulling in recharts/echarts just for this module.

## Goals / Non-Goals

**Goals:**
- Expose four Futu-backed HTTP routes that return normalized shareholder data for HK and US symbols, each wrapped in a `{data, error}` envelope (matching the existing `company` and `main-business-futu` envelope shape).
- Reuse `_company_info_cache` (24h TTL) for all four endpoints; key per (symbol, call-signature) so that `get_shareholders_holder_detail(symbol, holder_id=337488017)` does not collide with the default top-N call.
- A single new `<ShareholdersPanel />` component that renders four sub-tabs (概览 / 机构持股 / 股东明细 / 近期变动) using the existing `<SubModuleTabs />` primitive.
- A single-holder drill-down in the 股东明细 tab: click a row in the Top-N table → fetch that holder's cross-period history (calls `get_shareholders_holder_detail` again with `holder_id=`), render the trajectory inline (e.g. Prosus 29.07% → 23.09% over 5 years).
- Graceful empty / loading / error states consistent with `<MainBusinessPanel />` and `<CompanyInfoPanel />` (same `暂无持股数据` placeholder, same vintage-style skeleton, panel never blocks the page).
- No new dependencies, no DB, no new env vars, no SDK upgrade.

**Non-Goals:**
- A-share shareholder research. The Tushare `top10_holders` API is gated behind 2000+ points and has a different shape; explicitly out of scope. A-share pages get a clean "无 A 股股东数据" placeholder at most.
- Real-time shareholder data. The Futu APIs are quarterly disclosure, not real-time; 24h cache is sufficient.
- Per-holder reduction history via `holding_changes`. The Futu SDK does not support `holder_id` on that endpoint; per-holder history goes through `holder_detail(holder_id=)`.
- A new chart library. Custom SVG is enough.
- i18n / locale switching.
- `holding_changes` cross-period aggregation. The endpoint already provides the latest-period ranked list; pulling N periods would require N additional calls with a `period_id` filter (Futu does not document such a filter, so the endpoint is treated as latest-only).
- New Tushare / Futu quota; same Futu OpenD v10.7.6708+ requirement as the existing `hk-us-share-company-info` and `us-hk-main-business-composition` changes.

## Decisions

### 1. New sibling route prefix `/api/stock/shareholders-futu/` instead of adding to existing routes
The existing `/api/stock/main-business-futu?symbol=...` route and `/api/stock/company?symbol=...` route each have a fixed contract for a single shape. The four shareholder endpoints have distinct signatures (different query params, different response shapes) and the A-share-specific routes (`/api/stock/main-business?type=P`, etc.) cannot absorb HK/US dispatch. A dedicated prefix `/api/stock/shareholders-futu/{overview,institutional,holder-detail,holding-changes}` keeps each route's contract clean. The frontend calls the matching route per sub-tab.

### 2. `{data, error}` envelope on every route (not the A-share flat shape)
The A-share routes return flat shapes (`{ts_code, period, type, rows, ...}` or `{symbol, data, latest, ...}`) because the underlying data is always present when Tushare responds. The four shareholder endpoints are nullable in three distinct ways: (a) older OpenD returns "Unknown protocol ID", (b) `holder_detail(holder_id=)` for a holder Futu has never seen may return empty, (c) any of the four can return empty if the symbol has no Futu coverage. The existing `company` and `main-business-futu` routes already use the `{data, error}` envelope for this reason; the four new routes follow the same convention. Frontend treats `data === null` as the "暂无持股数据" empty state.

### 3. Server-side pagination for `get_shareholders_institutional`, client-side for the other three
Institutional returns 10 periods per page, and the use case ("5–7 year trend") wants 30+ periods in a single chart. We paginate server-side up to `n_periods=30` (max 4 Futu round-trips, ~400ms total), cache the merged DataFrame, and return it as one payload. Holder detail and holding changes return 20 rows per page and the use case ("top 50 holders" or "top 50 movers") is naturally paginated client-side; the server exposes `next_key` for the next page and the frontend decides when to load more. This avoids burning Futu quota for a feature the user might not use.

### 4. Cache key includes query-signature, not just symbol
A naive `shareholders_holder_detail:{symbol}` key would collapse two semantically different calls: `get_shareholders_holder_detail(symbol)` (top-N) and `get_shareholders_holder_detail(symbol, holder_id=337488017)` (Prosus history). The cache key is therefore `shareholders_holder_detail:{symbol}:{holder_id or 'all'}:{period_id or 'latest'}:{next_key or '0'}`. This matches the existing `revenue_breakdown_history:{symbol}:{n_periods}` pattern from the `us-hk-main-business-composition` change. Errors are not cached (matches `on_error_return_stale`).

### 5. Reuse the existing `{data, error}` shape but expose `next_key` and `has_more` as top-level fields
The Futu SDK exposes `next_key` as `df.attrs['next_key']` for holder_detail and as a column for institutional / holding_changes. The backend lifts this into a top-level `next_key: "20"` field on the response, and adds a boolean `has_more: true` so the frontend doesn't have to compare `next_key === "-1"` strings. (For institutional, `has_more` is `false` once we've paginated to the bottom or hit `n_periods`.)

### 6. Single new component file `<ShareholdersPanel />`, no in-place modification of `<MainBusinessPanel />`
The new panel needs four sub-tabs, a Top-N drill-down drawer, a dual-axis chart, and two side-by-side leaderboards. The shape of the data is entirely different from `<MainBusinessPanel />` (no by-product / by-region / by-industry dimensions, no 海外 badge, no stacked bar). A new component is cleaner than weaving four more branches into the 45KB `MainBusinessPanel.tsx`. We still reuse `<SubModuleTabs />` (the tab UI primitive) and the same vintage-style skeleton / `暂无持股数据` placeholder, so the visual language is consistent.

### 7. Custom SVG line+bar chart for the 机构持股 tab (no new chart library)
30 data points × 2 series (institutional_pct line + institution_quantity bars) does not justify pulling in recharts or echarts. A small ~80-line custom SVG component (in the same file or a sibling `DualAxisChart.tsx`) renders the trend. Y-axis scales independently for the two series (line on left axis, bars on right axis), x-axis is the period list. Same pattern as the lightweight-charts K-line already in the project — minimal dependencies, full control over the vintage style.

### 8. Top-N drill-down: click a row → in-panel drawer, not a modal
The 股东明细 tab renders the Top-50 (paginated) as a table. Clicking a row opens an in-panel drawer (slide-in from the right) that fetches `getShareholdersHolderDetail(symbol, holder_id=row.holder_id)` and renders the cross-period trajectory as a small line chart (20+ data points). Closing the drawer returns to the Top-50 list. This is a single-page experience — no route change, no URL state, no modal stacking.

### 9. 近期变动 tab: two parallel ranked lists
The `filter_type=1` (increases) and `filter_type=2` (decreases) calls are fired in parallel from the panel; the 概览 tab and 近期变动 tab each fetch their own data independently. Each list shows the top 20 (with `next_key` to load more if needed, but typically 20 is enough for a quarterly disclosure). Layout: two columns on `lg`, stacked on `sm`.

### 10. A-share pages are unchanged
The mount in `page.tsx` is gated on `companyInfo?.data?.market === "HK" || "US"`. A 6-digit symbol still gets the existing panels (K-line, indicators, fundamentals, company info, main business) with no new fetches fired.

### 11. Older OpenD / empty payload → clean placeholder, no raw error text
Mirrors the existing `get_company_info` and `get_revenue_breakdown` patterns: when Futu returns "Unknown protocol ID" (older OpenD < 10.7.6708) or any other upstream error, the backend returns 200 with `{data: <empty>, error: null}` for older-OpenD and `{data: null, error: "获取持股数据失败: <msg>"}` for other errors. The frontend renders "暂无持股数据" in both cases; the rest of the page is unaffected.

## Risks / Trade-offs

- [Server-side institutional pagination burns 1–4 Futu round-trips on first visit] → 24h cache makes repeat visits cost 0; the cap `n_periods=30` bounds the worst case. Mitigated.
- [`holder_id` is opaque across periods] → if Futu ever changes the `holder_id` namespace (e.g. after a corporate restructuring), cached cross-period histories may go stale. Cache TTL is 24h; the staleness window is bounded.
- [`close_price` in `holder_detail` is the latest snapshot price, not the historical close on `holding_date`] → documented in the spec; frontend does not derive P&L from it. The UI shows the price as informational only.
- [Custom SVG chart could regress on a future Next.js / React upgrade] → the chart is plain React state + JSX, no `useEffect`-driven DOM measurement; the SVG renders purely from props. Should be stable. A future change can swap it for recharts if the chart grows beyond two series.
- [In-panel drill-down drawer requires per-row fetch on click] → first click per row is a new Futu round-trip (cached for 24h after); repeat clicks for the same holder cost 0. UX: a brief skeleton inside the drawer.
- [Cache invalidation] → in-memory cache dies with the process; on next deploy all entries are fresh. No external cache to flush.
- [AGENTS.md "This is NOT the Next.js you know"] → the tasks.md step for the panel mount explicitly says to consult `frontend/node_modules/next/dist/docs/` before writing the new component.
- [Holding changes has no `holder_id` filter] → the 近期变动 tab cannot do "show me Prosus's reductions" via that endpoint. The single-holder drill-down goes through `holder_detail(holder_id=)` instead. Documented in the spec.
- [First-visit cost] → 4 Futu round-trips (overview + institutional + holder detail + holding changes) per first visit per symbol, ~400ms total. Cached for 24h. Acceptable for a quarterly disclosure view.

## Migration Plan

- **Backend**: deploy with four new endpoints added under `/api/stock/shareholders-futu/`. No DB migration. Old endpoints unchanged. Reuses existing Futu OpenD and SDK.
- **Frontend**: deploy with one new service module (`shareholders.ts`), one new component (`ShareholdersPanel.tsx`), and one new mount point in `page.tsx` (gated on market). Revert is a three-file change: remove the import + mount from `page.tsx`, delete `shareholders.ts` and `ShareholdersPanel.tsx`.
- **No feature flag needed** — the change is purely additive (a new panel, a new branch). Reversible in 3 lines.
- **Cache invalidation**: in-memory cache dies with the process; on next deploy all entries are fresh. No external cache to flush.

## Open Questions

- Should the 概览 tab's holder-type distribution be a donut chart or a horizontal stacked bar? Default: donut for ≥5 segments, horizontal bar for <5. Confirm during implementation.
- Should the 股东明细 tab's drill-down drawer show absolute-share change (`holder_quantity_change` from `holder_detail`) or percentage change (`holder_pct_change`)? Default: percentage change is the headline, absolute change is the secondary line (matching the 机构持股 dual-axis pattern). Confirm during implementation.
- Should the 概览 tab's Top-5 holders progress bar use a log or linear scale? Default: linear (Top-5 spreads are usually within one order of magnitude). Confirm during implementation.
- Should the `period_id` selector in the 概览 tab (using `holding_period` from the overview response) be a dropdown or a horizontal scroll of pills? Default: pills (more discoverable, ≤20 periods is fine). Confirm during implementation.
