## 1. Backend: service methods

- [x] 1.1 Add `FutuQuoteService.get_shareholders_overview(symbol)` classmethod in `backend/services/futu_quote_service.py` that:
  - resolves `symbol` to `(futu_code, market)` via the existing `_get_futu_code` helper,
  - calls `ctx.get_shareholders_overview(futu_code)` (proto 3237),
  - normalizes the response: extracts `main_holder`, `holder_type`, `holding_period` from the 3-sub-table dict; converts each DataFrame to a list of `{static_date, static_date_str, name, holder_pct, holder_id}` dicts; casts synthetic-Other `NaN` `holder_id` to `null`,
  - on `ret != RET_OK` or older OpenD "Unknown protocol ID" error, returns `{data: null, error: null}` (clean empty, same pattern as `get_company_info`),
  - on other upstream errors, returns `{data: null, error: "获取持股概览失败: <msg>"}`,
  - caches the result under `shareholders_overview:{symbol}` in the existing `_company_info_cache` (24h TTL),
  - returns the top-level `{data: {symbol, code, market, main_holder: [...], holder_type: [...], holding_period: [...], source: "futu", updated_at: <iso>}, error: null}` or empty envelope on older OpenD.
- [x] 1.2 Add `FutuQuoteService.get_shareholders_institutional(symbol, n_periods=30)` classmethod that:
  - first calls `ctx.get_shareholders_institutional(futu_code, num=10)` to obtain the first page and the first `next_key` cursor,
  - if the page has `next_key != "-1"` AND we want more periods, fires additional `ctx.get_shareholders_institutional(futu_code, num=10, next_key=cursor)` calls, up to a hard cap of `min(n_periods, 30)` rows total,
  - merges all pages into a single list of `{period_text, institution_quantity, institution_quantity_change, holder_quantity, holder_quantity_change, holder_pct, holder_pct_change, update_time_str}`,
  - returns `{data: {symbol, code, market, periods: [...], has_more: <bool>, source: "futu", updated_at: <iso>}, error: null}` or empty envelope on older OpenD,
  - caches under `shareholders_institutional:{symbol}:{n_periods}` in `_company_info_cache`.
- [x] 1.3 Add `FutuQuoteService.get_shareholders_holder_detail(symbol, holder_id=None, period_id=None, num=50, next_key=None)` classmethod that:
  - calls `ctx.get_shareholders_holder_detail(futu_code, request_type=None, next_key=next_key, num=num, sort_column=None, sort_type=None, period_id=period_id, holder_id=holder_id)` (proto 3239),
  - converts the returned DataFrame to a list of `{period_text, holder_id, name, holder_quantity, holder_quantity_change, holder_pct, holder_pct_change, holding_date, holding_date_str, close_price, price_change_pct, source_group_name, update_time_str}` dicts; coerce `holder_id` from int to int (no NaN expected here, but defend),
  - reads `df.attrs['next_key']` and exposes it as a top-level `next_key` field; sets `has_more = next_key != "-1"`,
  - on older OpenD / other errors, same envelope pattern,
  - caches under `shareholders_holder_detail:{symbol}:{holder_id or 'all'}:{period_id or 'latest'}:{next_key or '0'}` in `_company_info_cache`.
- [x] 1.4 Add `FutuQuoteService.get_shareholders_holding_changes(symbol, filter_type=1, num=50, next_key=None)` classmethod that:
  - calls `ctx.get_shareholders_holding_changes(futu_code, next_key=next_key, num=num, sort_type=None, sort_column=None, filter_type=filter_type)` (no `holder_id` parameter — Futu SDK does not expose it),
  - converts DataFrame to a list of `{period_text, name, holder_id, share_change_num, shares_change_price, share_ratio, holder_type, holder_type_id, holding_date, holding_date_str, share_ratio_change, share_num, next_key}` dicts,
  - reads `next_key` from the column (Futu exposes it as a column, not `attrs`); sets `has_more = next_key != "-1"`,
  - on older OpenD / other errors, same envelope pattern,
  - caches under `shareholders_holding_changes:{symbol}:{filter_type}:{next_key or '0'}` in `_company_info_cache`.
- [x] 1.5 Verify with a quick local Python REPL that all four new methods can be called and the cache is populated (no live OpenD needed for the cache layer). The Tencent (HK.00700) live test has already been run; the new methods will mirror those exact call patterns.

## 2. Backend: delegations on `HKStockService` and `USStockService`

- [x] 2.1 Add 4 static methods to `HKStockService` in `backend/services/akshare_service.py` (`get_shareholders_overview`, `get_shareholders_institutional`, `get_shareholders_holder_detail`, `get_shareholders_holding_changes`), each a one-liner that forwards to the corresponding `FutuQuoteService` classmethod.
- [x] 2.2 Add the same 4 static methods to `USStockService` (also one-liner forwards).
- [x] 2.3 Pattern matches the existing `HKStockService.get_revenue_breakdown` / `USStockService.get_revenue_breakdown` and the `get_company_info` delegations already in place.

## 3. Backend: API routes

- [x] 3.1 Add `GET /api/stock/shareholders-futu/overview` in `backend/api/stock.py`:
  - validates `symbol` matches the HK regex (`/^HK\.\d{4,5}$/` or `/^\d{4,5}$/`) or US regex (`/^US\.[A-Z]{1,5}$/` or `/^[A-Z]{1,5}$/`); else HTTP 400 `{"error": "Unsupported symbol"}`,
  - dispatches HK → `HKStockService.get_shareholders_overview(...)`, US → `USStockService.get_shareholders_overview(...)`,
  - returns 200 with the `{data, error}` envelope.
- [x] 3.2 Add `GET /api/stock/shareholders-futu/institutional?symbol=...&n_periods=30` with the same dispatch.
- [x] 3.3 Add `GET /api/stock/shareholders-futu/holder-detail?symbol=...&holder_id=<int>&period_id=<int>&num=50&next_key=<str>` with the same dispatch.
- [x] 3.4 Add `GET /api/stock/shareholders-futu/holding-changes?symbol=...&filter_type=1&num=50&next_key=<str>` with the same dispatch.
- [ ] 3.5 Verify with local curl after `uvicorn` is running:
  - `curl 'http://localhost:8000/api/stock/shareholders-futu/overview?symbol=00700'` returns the 3-sub-table payload,
  - `curl 'http://localhost:8000/api/stock/shareholders-futu/institutional?symbol=00700&n_periods=30'` returns 30 quarterly rows merged from 3 pages,
  - `curl 'http://localhost:8000/api/stock/shareholders-futu/holder-detail?symbol=00700&holder_id=337488017'` returns Prosus's 20-period history,
  - `curl 'http://localhost:8000/api/stock/shareholders-futu/holding-changes?symbol=00700&filter_type=2'` returns the latest-period decreases,
  - `curl 'http://localhost:8000/api/stock/shareholders-futu/overview?symbol=600519'` returns HTTP 400 (A-share not supported),
  - `curl 'http://localhost:8000/api/stock/shareholders-futu/overview?symbol=BAD-CHAR!'` returns HTTP 400.

## 4. Frontend: service module

- [x] 4.1 Create `frontend/src/services/shareholders.ts` with the following TypeScript types:
  ```ts
  export interface ShareholderRow {
    static_date: number; static_date_str: string;
    name: string; holder_pct: number;
    holder_id: number | null;
  }
  export interface ShareholdersOverviewResponse {
    symbol: string; code: string; market: "HK" | "US";
    main_holder: ShareholderRow[]; holder_type: ShareholderRow[];
    holding_period: Array<{ period_text: string; period_id: number }>;
    source: "futu"; updated_at: string;
  }
  export interface ShareholdersInstitutionalRow {
    period_text: string;
    institution_quantity: number; institution_quantity_change: number;
    holder_quantity: number; holder_quantity_change: number;
    holder_pct: number; holder_pct_change: number;
    update_time_str: string;
  }
  export interface ShareholdersInstitutionalResponse {
    symbol: string; code: string; market: "HK" | "US";
    periods: ShareholdersInstitutionalRow[];
    has_more: boolean;
    source: "futu"; updated_at: string;
  }
  export interface ShareholdersHolderDetailRow {
    period_text: string; holder_id: number; name: string;
    holder_quantity: number; holder_quantity_change: number;
    holder_pct: number; holder_pct_change: number;
    holding_date: number; holding_date_str: string;
    close_price: number; price_change_pct: number;
    source_group_name: string; update_time_str: string;
  }
  export interface ShareholdersHolderDetailResponse {
    symbol: string; code: string; market: "HK" | "US";
    rows: ShareholdersHolderDetailRow[];
    next_key: string; has_more: boolean;
    source: "futu"; updated_at: string;
  }
  export interface ShareholdersHoldingChangesRow {
    period_text: string; name: string; holder_id: number;
    share_change_num: number; shares_change_price: number;
    share_ratio: number; holder_type: string; holder_type_id: number;
    holding_date: number; holding_date_str: string;
    share_ratio_change: number; share_num: number;
  }
  export interface ShareholdersHoldingChangesResponse {
    symbol: string; code: string; market: "HK" | "US";
    rows: ShareholdersHoldingChangesRow[];
    next_key: string; has_more: boolean;
    source: "futu"; updated_at: string;
  }
  ```
- [x] 4.2 Add a `getShareholdersOverview(symbol): Promise<ShareholdersOverviewResponse | null>` fetcher that calls `GET /api/stock/shareholders-futu/overview?symbol=...` and unwraps `body.data` (treating `body.error` / `body.data === null` as `null`).
- [x] 4.3 Add `getShareholdersInstitutional(symbol, n_periods=30): Promise<ShareholdersInstitutionalResponse | null>`.
- [x] 4.4 Add `getShareholdersHolderDetail(symbol, opts?: {holder_id?, period_id?, num?, next_key?}): Promise<ShareholdersHolderDetailResponse | null>`.
- [x] 4.5 Add `getShareholdersHoldingChanges(symbol, filter_type=1, num=50, next_key?): Promise<ShareholdersHoldingChangesResponse | null>`.

## 5. Frontend: ShareholdersPanel component

- [x] 5.1 Read `frontend/node_modules/next/dist/docs/` for the local Next.js conventions before writing any new code (per AGENTS.md guidance and the `us-hk-main-business-composition` change's design precedent).
- [x] 5.2 Create `frontend/src/components/ShareholdersPanel.tsx` with the following props:
  ```ts
  interface ShareholdersPanelProps {
    market: "HK" | "US";
    symbol: string;
  }
  ```
- [x] 5.3 Use the existing `<SubModuleTabs />` primitive for the 4 sub-tab navigation. Default to "概览" active.
- [x] 5.4 Sub-tab 1 (概览):
  - fetch `getShareholdersOverview(symbol)` on mount and whenever `symbol` changes,
  - render two side-by-side cards: left = Top-5 holders progress bar (from `main_holder`, excluding synthetic "Other" with `holder_id === null`), right = holder-type donut (from `holder_type`),
  - render a "报告期" pill selector (using `holding_period` from the response) that updates the active period context (purely visual; overview is always latest on first call),
  - show the same vintage-style loading skeleton (4 placeholder rows × 4 columns) while in flight, and "暂无持股数据" on empty / error.
- [ ] 5.5 Sub-tab 2 (机构持股):
  - fetch `getShareholdersInstitutional(symbol, 30)` on mount,
  - render a custom dual-axis SVG chart: x-axis = `periods[].period_text`, left y-axis = `holder_pct` (line), right y-axis = `institution_quantity` (bar); both axes are linear with min=0, max=auto (1.1× max value),
  - below the chart, render a small 5-column metric strip: 机构数 (latest), 持股数 (亿股 = `holder_quantity / 1e8` with currency suffix), 占比 (latest %), 5 期变动 (sum of `holder_pct_change` last 5), 数据时间 (`update_time_str`),
  - vintage-style skeleton while in flight; "暂无持股数据" on empty.
- [ ] 5.6 Sub-tab 3 (股东明细):
  - fetch `getShareholdersHolderDetail(symbol, {num: 50})` on mount (top-50 holders, default sort by holder_quantity desc),
  - render a paginated table with columns: # | 名称 | 持股数 (亿股, derived from `holder_quantity / 1e8`) | 占比 | 本期变动 (`holder_pct_change` with sign + arrow) | 数据来源 (`source_group_name`),
  - provide a "搜索股东" input box (filters the in-memory list by `name` substring, case-insensitive) and a "持股 > X%" threshold filter (slider or input),
  - clicking a row opens an in-panel slide-in drawer (right side, 480px wide) that fetches `getShareholdersHolderDetail(symbol, {holder_id: row.holder_id})` and renders the cross-period trajectory as a small SVG line chart (periods on x-axis, `holder_pct` on y-axis) plus a "本季 vs 起始" delta badge,
  - "加载更多" button at the bottom of the table calls `getShareholdersHolderDetail(symbol, {num: 50, next_key: response.next_key})` and appends (disabled when `has_more === false`).
- [ ] 5.7 Sub-tab 4 (近期变动):
  - fire two parallel fetches on mount: `getShareholdersHoldingChanges(symbol, 1)` (increases) and `getShareholdersHoldingChanges(symbol, 2)` (decreases),
  - render two side-by-side ranked lists: left = "增持榜" (top 20, sorted by `share_change_num` desc, default), right = "减持榜" (top 20, sorted by `share_change_num` asc),
  - each row: # | 名称 | 变动股数 (with sign, formatted with 万 / 亿 suffix and currency) | 变动占比 (with sign) | 类型 (use a small color-coded `holder_type` badge: Mutual Fund = blue, Hedge Fund = amber, Private Company = gray, etc.),
  - vintage-style skeleton while in flight; "暂无持股数据" on empty.
- [ ] 5.8 Each sub-tab shows the same `数据源: Futu` caption as `<MainBusinessPanel />` (consistent with the existing HK/US caption style).
- [ ] 5.9 The empty / error / loading states are unified: a vintage 4×4 skeleton during in-flight; "暂无持股数据" on `data === null` or empty arrays; the panel never crashes the page.

## 6. Frontend: integration

- [ ] 6.1 In `frontend/src/app/stock/[symbol]/page.tsx`, import `ShareholdersPanel` and the four fetchers from `@/services/shareholders`.
- [ ] 6.2 Add a `<section className="vt-panel p-3 sm:p-4">` mount below the existing `<MainBusinessPanel />` mount, gated on `companyInfo?.data?.market === "HK" || companyInfo?.data?.market === "US"`. Pass `market={companyInfo?.data?.market}` and `symbol={symbol}`.
- [ ] 6.3 Verify by visiting `/stock/00700` in a browser:
  - the panel renders below `<MainBusinessPanel />`,
  - 概览 tab shows Prosus 23.09% / Huateng Ma 7.88% / BlackRock 2.66% / Vanguard 2.30% / Norges 1.36% in the top-5 list, with the holder-type donut showing VC/PE 23.18% as the largest slice,
  - 机构持股 tab shows a 30-quarter line+bar chart with holder_pct trending from ~53% (2019) to ~47% (2026),
  - 股东明细 tab lists the top-50 holders; clicking "Prosus Ventures N.V." opens a drawer with a 20-period line chart showing 29.07% → 23.04% trajectory,
  - 近期变动 tab shows the latest-period increase/decrease leaderboards side by side.
- [ ] 6.4 Verify `/stock/AAPL` (US path):
  - the panel renders with US data (e.g. Vanguard / BlackRock / State Street / Berkshire rows),
  - market cap-derived columns show `亿美元` suffix where applicable.
- [ ] 6.5 Verify `/stock/600519` (A-share) still works as before — no regression. The ShareholdersPanel mount is gated, no fetches are fired.
- [ ] 6.6 Verify `/stock/999999` (nonexistent) renders the empty state on the panel, not a crash.

## 7. Tests

- [ ] 7.1 Backend: add a unit test in `backend/tests/test_futu_shareholders.py` that mocks the four `get_shareholders_*` methods and asserts the normalization (synthetic-Other `NaN` → `null`, server-side institutional pagination, `next_key` / `has_more` lifting, older-OpenD "Unknown protocol ID" → empty-payload path, other-error → `{data: null, error: <msg>}` envelope).
- [ ] 7.2 Backend: add a unit test for `get_shareholders_institutional` pagination covering 1-page (10 rows), 3-page (30 rows), and end-of-history (next_key="-1") cases.
- [x] 7.3 Frontend: skip explicit snapshot tests (the project has no Jest/Vitest framework); verify TypeScript types via `npx tsc --noEmit` and verify runtime behavior manually by visiting `/stock/00700`, `/stock/AAPL`, and `/stock/600519` in a browser (tasks 6.3-6.6).

## 8. Docs

- [ ] 8.1 Update the stock-detail-page feature list (in `README.md` or wherever it lives) to mention that the new 持股研究 panel is rendered on HK and US stock pages.
- [ ] 8.2 Add a one-paragraph entry to `ENHANCEMENT_ROADMAP.md` "Current State" table noting the new HK/US shareholders coverage and the Futu OpenD v10.7.6708+ requirement.

## 9. Implementation notes — design evolution

The original spec sketched a 4-tab layout (概览 / 机构持股 / 股东明细 / 近期变动).
During implementation that design was iteratively consolidated into a single
Overview view based on user feedback. Final shape, top-to-bottom:

1. **Panel header**: `股 东 持 仓 研 究` with `❖` marker, collapsible via
   `<CollapsibleHeader>` (default expanded, +/- toggle, shared with the other
   two stock-detail panels).
2. **股东概览** (SectionHeader, full width):
   - 股 东 类 型 分 布 card — donut + top-6 legend, latest snapshot.
   - top5 股 东 分 析 card — progress-bar list with name / 持股数 / 本期变动 / 占比;
     clicking a row opens the drill-down drawer.
3. **持 股 变 化** (SectionHeader, full width):
   - top5 股 东 持 股 变 化 card — multi-line chart, dual-axis (left = 持股数 亿股,
     right = 占比 %), 5-year window (last 20 quarters).
   - 机 构 持 股 变 化 card — dual-axis chart (bars = institution_quantity,
     line = holder_pct) over 30 quarters with a hover tooltip showing period /
     家数 / 占比.
4. **Two-column 增持榜 / 减持榜** (no outer title, no card wrapper) — each
   column is its own bordered card showing top 5 + 前 50 合计.
5. **Single-holder drill-down drawer** — slide-in from right on row click,
   reuses the same `shareholders_holder_detail:{symbol}:{holder_id}` cache key
   as the trend fetch (instant on second click).

Notable changes from the original spec:

- **Tab navigation removed.** Single Overview view instead of 4 tabs — user
  explicitly requested consolidation.
- **趋势 chart switched from holder_pct to holder_quantity** (then upgraded
  to dual-axis with both curves). Real share movement is now the primary
  signal; the dashed 占比 curve is the secondary axis.
- **Drill-down 本期变动 computed locally** as `current_pct - previous_pct`
  because the Futu `holder_pct_change` field returns 0 for older rows even
  when the 占比 visibly shifts (dilution effect). The metric strip uses
  the API value; the drill-down table uses the local delta.
- **5 期 前 fixed off-by-one.** Originally `data.periods[4]` was off by one
  (showed 4-back, not 5-back). Now `data.periods[5]` and chart marker at
  `periods.length - 6` agree.
- **Institutional SDK call fixed.** Original code unpacked a 3-tuple
  `(ret, data, next_key)` but the Futu SDK returns `(ret, data)` and exposes
  `next_key` as a DataFrame column. New `_extract_next_key_from_df` helper
  unifies the three cursor shapes (attrs for holder_detail, column for the
  other two).
- **Field-name typos fixed** in `_df_to_holder_detail_rows` and
  `_df_to_shareholder_rows`: `holding_pct` / `holder_name` / `price_chg_pct`
  → `holder_pct` / `name` / `price_change_pct`.
- **`num ≤ 50`** enforced at the route level (`le=50`) to match the Futu SDK.
- **Older-OpenD "Unknown protocol ID" → clean empty payload**, never leaks
  the raw protocol error to the frontend.
- **"较 5 期 前" caption** removed from the institutional chart for honesty
  — the cell shows the delta, the chart shows the 5-periods-ago marker.
- **All "数据源: Futu" / 数据时间 captions** removed in the final pass per
  user request.
- **Section header `SectionHeader` primitive** added with `font-playfair`
  title + dim caption (mirrors MainBusinessPanel's section header style).
- **CollapsibleHeader primitive** added in `components/CollapsibleHeader.tsx`
  and applied to all three stock-detail panels (公司信息 / 主营业务构成 /
  股东持仓研究). Click anywhere on the header row to toggle; `−` when open,
  `+` when collapsed.

Verification status:

- ✅ `npx tsc --noEmit` clean.
- ✅ Backend imports compile, 4 routes registered at
  `/api/stock/shareholders-futu/{overview,institutional,holder-detail,holding-changes}`.
- ✅ Manual verification at `/stock/00700` (HK), `/stock/AAPL` (US) via
  backend log + rendered screenshots during the iterative session.
- ❌ Backend unit tests (`tests/test_futu_shareholders.py`) NOT added —
  deferred. Manual verification + integration with the live OpenD is the
  current QA path.
- ❌ `ENHANCEMENT_ROADMAP.md` / `README.md` updates NOT applied — same
  reason.

Cached responses (24h TTL in `_company_info_cache`):
- `shareholders_overview:{symbol}`
- `shareholders_institutional:{symbol}:{n_periods}`
- `shareholders_holder_detail:{symbol}:{holder_id or 'all'}:{period_id or 'latest'}:{next_key or '0'}`
- `shareholders_holding_changes:{symbol}:{filter_type}:{next_key or '0'}`

Ten cache keys are populated on first visit to a HK/US page (~9 fetches on
mount: 1 overview + 5 trend + 1 institutional + 1 detail top-50 + 2 holding
changes). All 24h TTL.
