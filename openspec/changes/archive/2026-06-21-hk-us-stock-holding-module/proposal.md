## Why

The HK and US stock pages already render a `<CompanyInfoPanel />` (Futu `get_company_profile` + `get_company_executives`) and a `<MainBusinessPanel />` (Futu `get_financials_revenue_breakdown`), but neither tells the user **who actually owns the company right now and how that ownership is changing**. The Futu OpenD exposes four `get_shareholders_*` endpoints (proto 3237 overview, proto 3238 institutional aggregate, proto 3239 holder detail, plus the `holding_changes` variant) that together form a "持股研究" workflow. Layering them onto the existing stock detail page closes the loop: from K-line → company info → main business → **shareholder structure**, the same investigative flow that a human analyst follows. The module is scoped to HK and US only because A-share shareholder data lives behind a separate Tushare API with a different shape and a higher point cost; A-share support is explicitly out of scope and is left untouched.

## What Changes

- Add four classmethods on `FutuQuoteService` in `backend/services/futu_quote_service.py`:
  - `get_shareholders_overview(symbol)` wraps `OpenQuoteContext.get_shareholders_overview` (proto 3237). Normalizes the 3-sub-table response (`main_holder`, `holder_type`, `holding_period`) into a single flat dict with `static_date_str` / `name` / `holder_pct` / `holder_id` per row. Casts the synthetic "Other" row's `holder_id` from `NaN` to `null`. Reuses the existing `_company_info_cache` (24h TTL) with key `shareholders_overview:{symbol}`. Quarterly disclosure, 24h cache is appropriate. Older OpenD / "Unknown protocol ID" returns clean empty payload.
  - `get_shareholders_institutional(symbol, n_periods=30)` wraps `OpenQuoteContext.get_shareholders_institutional` (proto 3238) and **fans out across `next_key` pages server-side**, returning a single merged DataFrame. Each page returns up to 10 periods; one full pull yields 30 periods (~7.5 years of history for Tencent) and never exceeds 4 Futu round-trips. Reuses `_company_info_cache` (24h TTL) with key `shareholders_institutional:{symbol}:{n_periods}`.
  - `get_shareholders_holder_detail(symbol, holder_id=None, period_id=None, num=50, next_key=None)` wraps `OpenQuoteContext.get_shareholders_holder_detail` (proto 3239) and surfaces the `attrs.next_key` offset. **Caching is keyed by `(symbol, holder_id, period_id, next_key)`** because the same call signature can resolve to either a top-N list or a single holder's cross-period history. 24h TTL.
  - `get_shareholders_holding_changes(symbol, filter_type=1, num=50, next_key=None)` wraps `OpenQuoteContext.get_shareholders_holding_changes`. `filter_type=1` returns the latest-period increases (default), `filter_type=2` returns decreases. The Futu SDK does NOT accept a `holder_id` parameter on this method, so per-holder reduction history must go through `get_shareholders_holder_detail(holder_id=...)` (Prosus reduction tracking is supported there). 24h TTL on `_company_info_cache`.
- Add four delegation methods on `HKStockService` and `USStockService` in `backend/services/akshare_service.py` mirroring the pattern from `HKStockService.get_revenue_breakdown` (a one-liner that forwards to `FutuQuoteService`).
- Add four new HTTP routes in `backend/api/stock.py` under a new sibling prefix `/api/stock/shareholders-futu/`:
  - `GET /shareholders-futu/overview?symbol=<hk-or-us>` — proto 3237.
  - `GET /shareholders-futu/institutional?symbol=<hk-or-us>&n_periods=30` — proto 3238.
  - `GET /shareholders-futu/holder-detail?symbol=<hk-or-us>&holder_id=<int>&period_id=<int>&num=50&next_key=<int>` — proto 3239.
  - `GET /shareholders-futu/holding-changes?symbol=<hk-or-us>&filter_type=1&num=50&next_key=<int>` — holding_changes.

  All four routes use the same regex dispatch as `/api/stock/main-business-futu`: HK regex `/^HK\.\d{4,5}$/` or `/^\d{4,5}$/`, US regex `/^US\.[A-Z]{1,5}$/` or `/^[A-Z]{1,5}$/`. A-share 6-digit input returns HTTP 400 with `{"error": "Unsupported symbol"}`. All four return `{data, error}` envelope (data may be `null`, error capped at 120 chars). Older OpenD "Unknown protocol ID" → clean empty payload (never leaks raw error text). The error envelope is chosen over the A-share-style flat payload because the four endpoints are nullable in distinct ways (older OpenD, single-page detail that may genuinely be empty, etc.) and the frontend already has the `{data, error}` pattern from the company-info and main-business changes.
- Add a new frontend service module `frontend/src/services/shareholders.ts` exposing four fetchers (`getShareholdersOverview`, `getShareholdersInstitutional`, `getShareholdersHolderDetail`, `getShareholdersHoldingChanges`) and matching TypeScript types.
- Add a new frontend component `frontend/src/components/ShareholdersPanel.tsx` that renders a 4-tab sub-panel using the existing `SubModuleTabs.tsx` pattern: 概览 (Top holders + holder-type pie), 机构持股 (5-year line/bar chart), 股东明细 (Top-N table with single-holder drill-down), 近期变动 (top increases + decreases side by side). The panel is rendered for HK and US markets only.
- Update `frontend/src/app/stock/[symbol]/page.tsx` to mount `<ShareholdersPanel market={...} />` **below** `<MainBusinessPanel />`, gated on `companyInfo?.data?.market === "HK" || "US"`. A-share pages (`/^\d{6}$/`) are not affected.

## Capabilities

### New Capabilities

- `hk-us-shareholders`: HK and US listed-company shareholder research module. Four Futu-backed HTTP routes (`/api/stock/shareholders-futu/{overview,institutional,holder-detail,holding-changes}`) and a new `<ShareholdersPanel />` component rendered on HK and US stock detail pages, exposing main-holder distribution, institutional-holding trend (up to 30 quarters / ~7.5 years), per-holder detail with single-holder cross-period drill-down, and a latest-period increase/decrease leaderboard.

### Modified Capabilities

- (none) — the existing `hk-us-share-company-info` and `us-hk-main-business-composition` specs' REQUIREMENTS are unchanged. The change is purely additive at the spec level: four new HTTP routes, one new service module, one new component, and one new mount point in `page.tsx`. The existing Futu cache, the existing main-business panel, and the existing company-info panel are all preserved without delta. A-share behavior is unchanged.

## Impact

- **Backend**:
  - `backend/services/futu_quote_service.py` — four new classmethods (`get_shareholders_overview`, `get_shareholders_institutional`, `get_shareholders_holder_detail`, `get_shareholders_holding_changes`). All reuse `_company_info_cache` (24h TTL). `get_shareholders_institutional` runs a server-side pagination loop (max 4 Futu round-trips) and returns a single merged DataFrame. `get_shareholders_holder_detail` exposes `attrs.next_key` as a top-level `next_key` field on the response (matches the SDK's `df.attrs` convention). `get_shareholders_overview` casts synthetic-Other `NaN` `holder_id` to `None` for clean JSON. All four handle the "Unknown protocol ID" older-OpenD case by returning `{data: <empty>, error: null}` (no raw error leak), mirroring the existing `get_company_info` and `get_revenue_breakdown` patterns.
  - `backend/services/akshare_service.py` — eight new delegating static methods (4 on `HKStockService`, 4 on `USStockService`).
  - `backend/api/stock.py` — four new routes under `/api/stock/shareholders-futu/`. Symbol dispatch and error envelope shape match the existing `/api/stock/main-business-futu` and `/api/stock/company` routes.
  - No new dependencies. No DB. No new env vars.
- **Frontend**:
  - `frontend/src/services/shareholders.ts` (new file) — 4 fetchers + TypeScript types (`ShareholdersOverviewResponse`, `ShareholdersInstitutionalResponse`, `ShareholdersHolderDetailResponse`, `ShareholdersHoldingChangesResponse`).
  - `frontend/src/components/ShareholdersPanel.tsx` (new file) — 4-tab sub-panel using `<SubModuleTabs />` and `<ModuleTabs />` per the existing `MainBusinessPanel` pattern. The 概览 tab shows a Top-5 holders progress bar and a holder-type pie/donut. The 机构持股 tab shows a dual-axis line+bar chart over 30 quarters. The 股东明细 tab shows a paginated table with a holder search and a single-holder drill-down drawer (clicks a row → fetch `get_shareholders_holder_detail(holder_id=)` for that holder's 20+ periods). The 近期变动 tab shows two side-by-side ranked lists: increases (filter_type=1) and decreases (filter_type=2). The 股东明细 drill-down does **not** pre-aggregate cross-period data; each click fetches a fresh period list and the panel renders the trajectory in-place.
  - `frontend/src/app/stock/[symbol]/page.tsx` — one new mount point: `<ShareholdersPanel market="HK" | "US" symbol={symbol} />` below `<MainBusinessPanel />`, gated on `companyInfo?.data?.market`.
- **Data caveats** (encoded in backend normalization, surfaced in spec):
  - `holder_id` from `get_shareholders_overview.main_holder` is `float64` in pandas; the synthetic "Other" row has `NaN`. Backend must cast to `int | null` for clean JSON.
  - `close_price` in `get_shareholders_holder_detail` is currently the latest snapshot price across all rows in a single period (a known Futu-side quirk; not historical close on `holding_date`). Spec documents the behavior; frontend does not derive P&L from it.
  - `get_shareholders_holding_changes` does NOT accept a `holder_id` parameter in the Futu SDK. Per-holder reduction history (e.g. "show me every Prosus sale") is done via `get_shareholders_holder_detail(holder_id=...)`. This is documented in the spec.
  - `next_key` shapes differ: institutional is a timestamp cursor (`"1704038399"`), holder-detail / holding-changes are integer offsets (`"20"`, `"40"`). The backend exposes both as opaque `next_key` strings; the frontend passes them through without parsing.
  - Older OpenD (< 10.7.6708) on any of the four protos → clean empty payload; the panel renders "暂无持股数据" placeholder; the rest of the page is unaffected.
- **Failure modes**: Futu error / empty / older OpenD → panel shows "暂无持股数据"; page otherwise unaffected. The panel must never block the rest of the page from rendering.
- **Quota**: None of the four protos are in Futu's documented rate-limit surface (not real-time subscriptions or K-line). First-visit cost is 1 (overview) + 1 (institutional paginated) + 1 (holder detail) + 1 (holding changes) = ~4 Futu round-trips per first visit per symbol; cached for 24h after.
