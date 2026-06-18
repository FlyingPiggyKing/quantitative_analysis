## Context

- The `main-business-composition` change introduced a `<MainBusinessPanel />` that renders A-share data from Tushare `fina_mainbz` (doc_id=81) below the existing `<CompanyInfoPanel />`. The panel was hard-gated on `/^\d{6}$/.test(symbol)`, so HK and US stock pages get a `CompanyInfoPanel` (via Futu `get_company_profile` + `get_company_executives`) but no revenue-mix view.
- The `hk-us-share-company-info` change established the pattern for Futu-backed endpoints: `FutuQuoteService.get_company_info(symbol)` → `_company_info_cache` (24h TTL) → `GET /api/stock/company?symbol=...` with regex dispatch.
- Futu's `OpenQuoteContext.get_financials_revenue_breakdown(code, date=None, financial_type=None, currency_code=None)` (proto 3228, v10.7+) is the canonical source. A single call returns ALL dimensions (产品 / 行业 / 地区 / 业务) in a `breakdown_list` where each item has `type` ∈ {1=Product, 2=Industry, 4=Region, 8=Business} and an `item_list` of `{name, main_oper_income, ratio}`. Historical access is via `screen_date_list` (only when `date` and `financial_type` are both unset), where each item is `{date, period_text, financial_type}`.
- Differences from Tushare `fina_mainbz`:
  1. **One call returns all dimensions** (no separate `type=P/D/I` calls). The current A-share endpoint takes a `type` query param; the Futu endpoint does not.
  2. **No cost / profit / margin data.** Futu only returns revenue and ratio. The A-share panel's 毛利率 / 利润占比 / 跨期对比 YoY columns cannot be reproduced for HK/US without a separate Futu call (`get_financials_statements`, out of scope).
  3. **`ratio` is pre-computed** by Futu (already a percentage, 0–100). No client-side recomputation.
  4. **`currency_code`** is included in the response and reflects the stock's reporting currency (HKD for HK, USD for US, etc.). Frontend converts 亿元 display per CLAUDE.md.
  5. **History is per-call** with a `date` parameter; `screen_date_list` enumerates available dates. No batched history call.
- Frontend stack: Next.js app router, Tailwind, project-local conventions captured in `AGENTS.md` ("This is NOT the Next.js you know") — any new component code must consult `frontend/node_modules/next/dist/docs/` first.
- No database, no Redis. In-memory caches only. A-share cache lives at `backend/services/akshare_service.py` (`_main_biz_cache`); Futu caches live at `backend/services/futu_quote_service.py` (`_futu_cache` and `_company_info_cache`).

## Goals / Non-Goals

**Goals:**
- Add a single new Futu-backed backend route that returns the normalized main-business payload for a HK or US symbol, including:
  - `period` (e.g. "2025/FY"), `currency_code` (ISO 4217)
  - `product`, `region`, `industry`, `business` lists (each `[{item, revenue, ratio_pct, currency_code}]`, sorted by revenue desc, dedup applied)
  - `history` block with the last 4 annual periods of by-product data (each period: `{period, items: [...]}`)
  - `has_distinct_industry` flag (true iff at least one industry item's name is not in the product item set)
  - `updated_at`, `source: "futu"`
- Add a `getFutuMainBusiness(symbol)` fetcher in `frontend/src/services/mainBusiness.ts` and a `market: "A" | "HK" | "US"` discriminator prop on the existing `<MainBusinessPanel />` to switch between A-share and Futu data shapes.
- Drop the `/^\d{6}$/` guard in `frontend/src/app/stock/[symbol]/page.tsx`; render the panel on every page, branching on `companyInfo?.data?.market`.
- Reuse the existing `_company_info_cache` (24h TTL) for the latest-period payload; a separate key for history.
- Graceful empty / loading / error states consistent with the A-share panel and the `CompanyInfoPanel` placeholder pattern.

**Non-Goals:**
- No gross margin, profit share, or cost-related data for HK/US — Futu does not provide it and we do not call `get_financials_statements` to derive it (out of scope, would multiply the OpenD call count and confuse the cache key design).
- No YoY % on the 跨期对比 chart for HK/US — same reason (no prior-period revenue available cheaply; would require 8 parallel calls).
- No A-share changes. The existing `GET /api/stock/main-business?type=P&period=...&top=...` route and its Tushare cache are untouched.
- No DB persistence, no Redis, no new env vars, no new dependencies. Pure Python + existing Futu SDK.
- No i18n / locale switching.
- No `get_financials_revenue_breakdown` cross-period pre-warming.

## Decisions

### 1. New sibling route `/api/stock/main-business-futu` instead of merging into `/api/stock/main-business`
The existing A-share route at `/api/stock/main-business?symbol=600519&type=P&period=20231231&top=3` has a fixed contract (Tushare-style response, `type` / `period` / `top` query params). The Futu data shape is fundamentally different: no `type` param (all dimensions in one call), no `period` param in the same form (epoch seconds, not YYYYMMDD), and a different response structure (`{product, region, industry, business, history, has_distinct_industry, ...}` vs. `{ts_code, period, type, rows: [...]}`). Adding HK/US dispatch to the existing route would require either (a) ignoring `type` for HK/US, breaking the spec for A-share callers, or (b) branching the response shape on market, complicating the React component's typing. Adding a sibling route `/api/stock/main-business-futu?symbol=HK.00700` (with no `type` param, response always includes all dimensions) keeps both contracts clean. The frontend branches on `companyInfo?.data?.market` and calls the matching route. Alternatives considered: a single `/api/stock/main-business?market=A|HK|US&...` route (rejected — the query params diverge by market, the typing becomes a discriminated union nightmare); client-side call to Futu directly (rejected — must go through backend, OpenD only listens on localhost).

### 2. One cache entry per (symbol, period), not per (symbol, period, dimension)
Futu returns all dimensions in a single call. Caching per (symbol, period) instead of per (symbol, period, dimension) is correct because the underlying call is one. The cache key is `revenue_breakdown:{symbol}` for the latest-period payload, and `revenue_breakdown_history:{symbol}:{n_periods}:{last_period_timestamp}` for the history block. Reuse `_company_info_cache` (24h TTL) since main-business data updates only on quarterly reports. Errors are NOT cached (matches the existing `on_error_return_stale` pattern in `futu_quote_service.py`).

### 3. History block = 4 parallel `get_financials_revenue_breakdown` calls
The Futu API has no batched history call. To get N historical periods, we make N calls, each with a different `date` (epoch seconds from `screen_date_list`). The first call (latest period) returns `screen_date_list`; we then filter for annual periods (preferring `financial_type == 7` 年报, falling back to `period_text` ending in `/FY`) and take the 4 most recent. Each historical call costs ~100ms in our environment; 4 in parallel via `concurrent.futures.ThreadPoolExecutor(max_workers=4)` finishes in ~150ms. The 4 results are merged into a `history.periods[]` + `history.series[]` shape (similar to the A-share history response, but `values[]` only has `period` and `revenue` — no profit/cost/gross_margin/yoy). Alternative considered: a single call with no `date` (gives only the latest) (rejected — no cross-period data at all). Alternative considered: a single call with `currency_code=...` to normalize (rejected — the A-share code uses raw currency, and CLAUDE.md says the frontend handles unit conversion; we follow the same pattern).

### 4. Reuse `<MainBusinessPanel />` instead of a new component
The A-share panel already has all the visual primitives needed for the Futu payload: by-product table, by-region table with 海外 badge, stacked bar, 跨期对比 column chart. Adding a `market` prop and conditional rendering is smaller than a parallel component. The conditionals:
- When `market !== "A"`: hide the 毛利率 / 利润占比 columns in the by-product table; hide the 跨期对比 YoY column; keep the revenue column and stacked bar.
- The 跨期对比 chart for HK/US becomes a 4-bar column chart of revenue (no YoY overlay).
- The 业务 dimension is Futu-specific (not in Tushare). The 行业 dimension is rendered only if `has_distinct_industry` is true (same logic as A-share).
- The component still receives `product` / `region` / `industry` props, but their inner shape is the Futu `{item, revenue, ratio_pct, currency_code}` shape, not the A-share `{item, sales, profit, cost, ...}` shape. A small type guard (e.g. `'revenue' in row`) tells the renderer which shape it's looking at — or we normalize both into a single shape server-side. **Decision: normalize server-side.** The Futu service method returns the same `{item, revenue, ratio_pct, currency_code}` shape used in the props, and the A-share service method (already deployed) returns `{item, sales, profit, cost, revenue_share_pct, ...}`. The component checks for the union: if `profit` is in the row, it's A-share (full columns); if not, it's Futu (revenue-only columns). This is one if-statement in the component and avoids a parallel fetcher type.

### 5. Currency unit: divide by 1e8, suffix `亿HKD` / `亿美元` / etc.
CLAUDE.md says "HK: HKD → /1e8 显示为亿HKD; US: USD → /1e8 显示为亿美元". The Futu `get_financials_revenue_breakdown` response includes a `currency_code` per row, which the component uses to pick the suffix. This is consistent with the A-share component's `亿元` suffix.

### 6. "海外" badge logic reused
Same regex as the A-share component: `/国外|海外|境外|出口|overseas/i` against `item`. Some Futu by-region rows may use "Other countries" / "海外" / "亚太" — the regex covers all of these. The badge is a small vintage-styled label rendered next to the region name.

### 7. "Other" / "其他" rows preserved, not merged
The Futu response includes an item named "其他" / "Others" / "其他业务" / "Other Regions" / etc. We pass these through unchanged rather than merging them with the A-share "其他" bucket logic. The A-share code merges non-top-N items in the 跨期对比 cross-period chart only; the per-period by-product table preserves all rows. Same approach here for consistency.

### 8. Empty-state message is unified
When the response has no items in all dimensions, the panel renders "暂无主营业务构成数据" — same as the A-share empty state. When the Futu API returns `Unknown protocol ID` (older OpenD), the backend returns an empty payload (no error, mirroring `get_company_info`'s "Unknown protocol ID" handling) and the panel renders the same empty state. No new "service unavailable" placeholder needed.

### 9. No new Tushare / Futu quota
The Futu `get_financials_revenue_breakdown` is not in the user's documented quota limits (it's a low-frequency fundamental-data API, not a real-time subscription or historical K-line). Per the docs page, only `Subscription Quota` and `Historical Candlestick Quota` are rate-limited. 5 calls per first-visit (1 latest + 4 history) per symbol is well under any plausible limit. The 24h cache makes repeat visits cost 0 Futu calls.

## Risks / Trade-offs

- [Futu returns only revenue, no cost/profit] → The HK/US panel cannot show gross margin or profit share. Spec mandates revenue-only columns for HK/US. Trade-off: the panel is less rich than the A-share one, but the data simply doesn't exist in `get_financials_revenue_breakdown`. Deriving gross margin from `get_financials_statements` is out of scope (8+ extra calls, different cache key shape, no clean per-product mapping in the statements API).
- [No YoY % on 跨期对比 for HK/US] → Same reason. The cross-period chart shows revenue across 4 years as bars, but no growth %. Trade-off: a column chart without YoY is still useful for spotting revenue shifts across product lines.
- [First-visit latency: 1 call for latest + 4 parallel calls for history] → ~150ms in our environment. The frontend renders the latest-period sections independently with their own loading skeletons, so the page doesn't appear frozen. The 跨期对比 section's loading skeleton is shown while the 4 history calls resolve.
- [History 跨期对比 with non-existent period] → If a company IPO'd recently, `screen_date_list` may have fewer than 4 annual periods. Spec mandates rendering only the periods that exist; the chart's x-axis adapts. If 0 history periods exist, the 跨期对比 section is hidden entirely.
- [Older OpenD (< 10.7.6708) returns "Unknown protocol ID"] → Spec mandates treating this as empty data (mirroring `get_company_info`'s behavior). The panel renders the "暂无主营业务构成数据" placeholder. No raw error text leaks to the user.
- [Cache invalidation] → In-memory cache dies with the process; on next deploy all entries are fresh. No external cache to flush.
- [AGENTS.md "This is NOT the Next.js you know"] → The tasks.md step for the panel modification explicitly says to consult `frontend/node_modules/next/dist/docs/` before writing the conditional-render code.
- [Per-period cache key may drift across long sessions] → `_company_info_cache` uses an in-memory dict with TTL; entries die with the process. No external state to worry about. A repeated visit within 24h gets the cached value.

## Migration Plan

- **Backend**: deploy with one new endpoint added (`/api/stock/main-business-futu`); no DB migration. Old endpoints unchanged. Reuses existing Futu OpenD and SDK — no SDK upgrade needed beyond what the `hk-us-share-company-info` change already required (>= 10.7.6708).
- **Frontend**: deploy with one new fetcher in `mainBusiness.ts`, one new prop on `<MainBusinessPanel />`, and one guard-removal + branch in `page.tsx`. Revert is a three-file change: remove the `market` prop usage, restore the `/^\d{6}$/` guard, and drop the `getFutuMainBusiness` import.
- **No feature flag needed** — the change is purely additive (a new branch in the same component, a new route) and reversible in 3 lines.
- **Cache invalidation**: the in-memory cache dies with the process; on next deploy all entries are fresh. No external cache to flush.

## Open Questions

- Should the by-product bar chart for HK/US use the same color palette as the A-share chart, or a slightly different palette to signal "this is Futu data"? Default: same palette (consistency wins). Confirm during implementation.
- Should the panel show a small badge "数据源: Futu" vs the A-share "数据源: Tushare" to disambiguate? Default: yes — match the existing caption style and surface the data source. Confirm during implementation.
- Should the 业务 (Business) dimension (Futu-only) be rendered as a 4th section on HK/US pages? Default: render it below 按行业, with the same table shape as 按产品. If a Futu response has no 业务 items, the section is hidden. Confirm during implementation.
- Should the 跨期对比 chart for HK/US use the top-N (e.g. top-3) selection like A-share, or show all items? Default: top-3 by latest-period revenue, with the rest bucketed as "其他" — same as A-share. Confirm during implementation.
