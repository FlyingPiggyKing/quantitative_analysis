## Why

The `main-business-composition` change (sibling openspec change) added a `<MainBusinessPanel />` to A-share stock pages using Tushare `fina_mainbz` (doc_id=81) — by-product, by-region, by-industry, and cross-period views. HK and US stock pages already render a `<CompanyInfoPanel />` (Futu `get_company_profile` / `get_company_executives`) but get **no equivalent revenue-mix view**. Futu's `get_financials_revenue_breakdown` (proto 3228, v10.7+) returns the same conceptual data (产品 / 行业 / 地区 / 业务 breakdowns with `main_oper_income` and `ratio`) and is the canonical Futu source for this view. Layering it on top of the existing panel gives HK/US users the same actionable context (e.g. "Apple iPhone is ~52% of revenue, Services is now ~22%", "Tencent 增值服务 vs 网络广告 split") that A-share users already have.

## What Changes

- Add `FutuQuoteService.get_revenue_breakdown(symbol)` in `backend/services/futu_quote_service.py` that wraps `OpenQuoteContext.get_financials_revenue_breakdown` and normalizes the response (split `breakdown_list` by `RevenueBreakdownType` 1/2/4/8 into `product` / `industry` / `region` / `business` lists of `{item, revenue, ratio_pct, currency_code}`, drop items with null/zero revenue, drop fully duplicate items, sort by revenue desc). No new cache class — reuse the existing `_company_info_cache` (24h TTL) with a new key prefix.
- Add `GET /api/stock/main-business?symbol=<hk-or-us>` in `backend/api/stock.py` that dispatches by market (HK regex → HK, US regex → US, A-share regex → 400 "仅支持 A 股 6 位代码" — wait, see below) and returns the normalized payload plus a `history` block of the last 4 annual periods for the by-product dimension. The A-share-specific `type` / `period` / `top` query parameters are NOT supported on this endpoint — Futu's API returns all dimensions in a single call, and `screen_date_list` is the only history access.
- Reuse the existing `<MainBusinessPanel />` component (no new component file). Add a new `MarketKind` discriminator prop (`"A" | "HK" | "US"`) that switches:
  - **A-share path** (existing, unchanged): Tushare `fina_mainbz` → `/api/stock/main-business?symbol=6digits&type=P` etc., shows full 4 sections including 毛利率 / 利润占比 / 跨期对比 top-3 column chart.
  - **HK / US path** (new): Futu `get_financials_revenue_breakdown` → `/api/stock/main-business?symbol=HK.00700` etc., shows 3 sections (按产品, 按地区, 跨期对比) using only `revenue` and `ratio_pct` — no gross margin, no profit share (Futu data does not provide 成本 / 利润). The 跨期对比 chart uses revenue bars (no YoY %, since each period requires a separate Futu call with a `date` filter).
- Update `frontend/src/app/stock/[symbol]/page.tsx` to remove the `/^\d{6}$/` guard on `<MainBusinessPanel />` and instead branch by `market` (`companyInfo?.data?.market`). Add a single new fetch for the HK/US endpoint; the existing 4-call A-share fetch is left untouched.
- Update `frontend/src/services/mainBusiness.ts` types: add a new `FutuMainBusinessResponse` shape and a `getFutuMainBusiness(symbol)` fetcher. Keep the existing A-share types intact.

## Capabilities

### New Capabilities

- `us-hk-main-business-composition`: HK / US listed-company main-business composition. Backend exposes Futu `get_financials_revenue_breakdown` (proto 3228) data via `/api/stock/main-business` for HK and US symbols; the existing `<MainBusinessPanel />` component renders a Futu-shaped subset of the A-share panel (按产品, 按地区, 跨期对比) on HK and US stock pages, with currency derived from the response's `currency_code` field and unit conversion in the frontend (raw value already in the stock's reporting currency, divided by 1e8 for 亿元 display).

### Modified Capabilities

- (none) — the existing `main-business-composition` and `hk-us-share-company-info` specs' REQUIREMENTS are unchanged. The change is purely additive at the spec level: a new capability `us-hk-main-business-composition`, a new sibling route (`/api/stock/main-business-futu`), a new `market` prop on the existing `<MainBusinessPanel />` component, and a new fetcher in `mainBusiness.ts`. The A-share `GET /api/stock/main-business?type=P&period=...&top=...` endpoint contract, the A-share normalization (dedup, derived share/margin metrics, 24h cache), and the A-share frontend fetch path are all preserved without delta.

## Impact

- **Backend**:
  - `backend/services/futu_quote_service.py` — new `get_revenue_breakdown(symbol, periods=4)` classmethod on `FutuQuoteService`. Reuses `_company_info_cache` (24h TTL) with key `revenue_breakdown:{symbol}` for the latest-period payload, and a separate `revenue_breakdown_history:{symbol}:{n}` key for the cross-period history. Errors are not cached. Older OpenD (< 10.7.6708) returns "Unknown protocol ID" → handled the same way `get_company_info` does (clean empty result, no raw error leak).
  - `backend/api/stock.py` — new `GET /api/stock/main-business` route. Symbol dispatch mirrors the existing `get_company_info` route: `/^\d{6}$/` → existing A-share path (UNCHANGED; we do NOT add `type` to this route since the A-share variant is already exposed at `/api/stock/main-business?symbol=6digits&type=P`); for HK/US symbols we return the Futu payload. To keep the A-share contract intact, the new HK/US path is added as a separate query-string discriminator on a NEW sibling route `GET /api/stock/main-business-futu?symbol=...` (rationale in design.md §1).
  - Requires Futu OpenD v10.7.6708+ on the user's machine — same constraint as the existing `hk-us-share-company-info` change. No new dependencies.
- **Frontend**:
  - `frontend/src/app/stock/[symbol]/page.tsx` — drop the `/^\d{6}$/` guard, branch on `companyInfo?.data?.market` to pick A-share vs Futu data, add `mainBusinessFutu` state + fetcher.
  - `frontend/src/services/mainBusiness.ts` — add `getFutuMainBusiness(symbol)` and a `FutuMainBusinessResponse` type. Keep the existing A-share types and fetchers intact.
  - `frontend/src/components/MainBusinessPanel.tsx` — add a `market: "A" | "HK" | "US"` prop; when market !== "A", skip the 毛利率 / 利润占比 / 跨期对比 YoY columns and use the Futu-shaped data. Component file is modified, not duplicated.
- **Data caveats** (encoded in backend normalization, surfaced in spec):
  - Futu returns only `main_oper_income` and `ratio` per item — no 成本, no 利润. So the by-product table on HK/US pages has columns (产品, 收入, 占比) only; gross margin and profit share are not rendered for HK/US. The 跨期对比 section is a 4-bar column chart of revenue with no YoY overlay.
  - `ratio` is provided directly by Futu (already a percentage, e.g. 12.34 = 12.34%). No client-side recomputation needed.
  - `currency_code` comes back as ISO 4217 (HKD for HK, USD for US, etc.). The frontend divides `revenue` by 1e8 for 亿元 display and suffixes `亿HKD` / `亿美元` accordingly. CLAUDE.md says raw Futu values are in the stock's reporting currency, not cents — confirmed for `get_financials_revenue_breakdown`.
  - History access: only by `date` (epoch seconds) from `screen_date_list` plus a `financial_type` filter. We pull the 4 most recent annual dates from `screen_date_list` (filtering on `financial_type == 7` for 年报 if present) and call the API 4 times in parallel. If `screen_date_list` is empty, the 跨期对比 section is hidden. Per-call Futu round-trip is ~100ms; 4 parallel calls are bounded by `ThreadPoolExecutor(max_workers=4)`.
  - "海外" badge logic from the A-share spec is reused (regex `/国外|海外|境外|出口|overseas/i`).
  - Older OpenD on `get_financials_revenue_breakdown` → panel renders the same "暂无主营业务构成数据" placeholder used for empty data; the rest of the page is unaffected.
- **Failure modes**: Futu error / empty / older OpenD → panel shows "暂无主营业务构成数据"; page otherwise unaffected. The panel must never block the rest of the page from rendering.
