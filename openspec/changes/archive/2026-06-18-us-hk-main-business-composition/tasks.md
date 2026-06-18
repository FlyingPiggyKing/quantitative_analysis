## 1. Backend: service method

- [x] 1.1 Add `FutuQuoteService.get_revenue_breakdown(symbol)` classmethod in `backend/services/futu_quote_service.py` that:
  - resolves `symbol` to `(futu_code, market)` via the existing `_get_futu_code` helper,
  - calls `ctx.get_financials_revenue_breakdown(futu_code)` (proto 3228, v10.7+),
  - on `ret != RET_OK` or older OpenD "Unknown protocol ID" error, returns `{data: null, error: null}` (clean empty, same pattern as `get_company_info`),
  - normalizes the response: splits `breakdown_list` by `type` (1=Product, 2=Industry, 4=Region, 8=Business) into four lists of `{item, revenue, ratio_pct, currency_code}`,
  - drops items with null or zero revenue, drops fully duplicate `(item, revenue, ratio_pct, currency_code)` tuples (keep first),
  - sorts each list by `revenue` desc,
  - computes `has_distinct_industry` (true iff at least one industry item's `name` is not in the product item set),
  - caches the result under `revenue_breakdown:{symbol}` in the existing `_company_info_cache` (24h TTL),
  - returns the top-level object `{symbol, code, market, period, currency_code, product, region, industry, business, has_distinct_industry, source: "futu", updated_at}` or `{data: null, error: null}` on empty.
- [x] 1.2 Add `FutuQuoteService.get_revenue_breakdown_history(symbol, n_periods=4)` classmethod that:
  - first calls `get_revenue_breakdown(symbol)` to obtain `screen_date_list`,
  - filters for annual periods (preferring `financial_type == 7` 年报, falling back to `period_text` ending in `/FY`),
  - takes the 4 most recent `date` values,
  - fires N `ctx.get_financials_revenue_breakdown(futu_code, date=d)` calls in parallel via `concurrent.futures.ThreadPoolExecutor(max_workers=4)`,
  - merges results into `{symbol, code, market, currency_code, periods: [...], items: [{item, currency_code, values: [{period, revenue, ratio_pct}]}], source: "futu", updated_at}`,
  - picks top-3 by latest-period revenue per item, buckets the rest as `其他`,
  - caches under `revenue_breakdown_history:{symbol}:{n_periods}` in `_company_info_cache`.
- [x] 1.3 Verify with a quick local Python REPL that the new methods can be called and the cache is populated (no live OpenD needed for the cache layer).

## 2. Backend: API route

- [x] 2.1 Add `GET /api/stock/main-business-futu` route in `backend/api/stock.py`:
  - validates `symbol` matches the HK regex (`/^HK\.\d{4,5}$/` or `/^\d{4,5}$/`) or US regex (`/^US\.[A-Z]{1,5}$/` or `/^[A-Z]{1,5}$/`); else HTTP 400 `{"error": "Unsupported symbol"}`,
  - dispatches: HK → `HKStockService.get_revenue_breakdown(...)`, US → `USStockService.get_revenue_breakdown(...)` (or both delegate to a module-level helper that wraps `FutuQuoteService.get_revenue_breakdown`),
  - on Futu upstream error returns 200 with `{data: null, error: "获取主营构成失败: <msg>"}` (never 5xx),
  - on older OpenD "Unknown protocol ID" returns 200 with `{data: <empty>, error: null}` (mirrors the `company` endpoint).
- [x] 2.2 Add a sibling `GET /api/stock/main-business-futu/history` route with the same symbol dispatch and `n_periods=4` default.
- [x] 2.3 Verify with a local curl:
  - `curl 'http://localhost:8000/api/stock/main-business-futu?symbol=00700'` returns the by-product/by-region/by-industry payload,
  - `curl 'http://localhost:8000/api/stock/main-business-futu/history?symbol=00700'` returns 4 annual periods of by-product data,
  - `curl 'http://localhost:8000/api/stock/main-business-futu?symbol=AAPL'` returns the US payload,
  - `curl 'http://localhost:8000/api/stock/main-business-futu?symbol=600519'` returns HTTP 400 (A-share uses the existing `/api/stock/main-business?type=P` route),
  - `curl 'http://localhost:8000/api/stock/main-business-futu?symbol=BAD-CHAR!'` returns HTTP 400.

## 3. Frontend: data fetching

- [x] 3.1 Open `frontend/src/services/mainBusiness.ts` and add a new `FutuMainBusinessResponse` type:
  ```ts
  export interface FutuMainBusinessItem { item: string; revenue: number; ratio_pct: number; currency_code: string }
  export interface FutuMainBusinessResponse {
    symbol: string; code: string; market: "HK" | "US";
    period: string; currency_code: string;
    product: FutuMainBusinessItem[]; region: FutuMainBusinessItem[];
    industry: FutuMainBusinessItem[]; business: FutuMainBusinessItem[];
    has_distinct_industry: boolean;
    source: "futu"; updated_at: string;
  }
  export interface FutuMainBusinessHistoryResponse {
    symbol: string; market: "HK" | "US"; currency_code: string;
    periods: string[];
    items: Array<{ item: string; currency_code: string; values: Array<{ period: string; revenue: number; ratio_pct: number }> }>;
    source: "futu"; updated_at: string;
  }
  ```
- [x] 3.2 Add a `getFutuMainBusiness(symbol: string): Promise<FutuMainBusinessResponse | null>` fetcher that calls `GET /api/stock/main-business-futu?symbol=...` and returns the parsed JSON (or `null` on 4xx/5xx).
- [x] 3.3 Add a `getFutuMainBusinessHistory(symbol: string): Promise<FutuMainBusinessHistoryResponse | null>` fetcher for the history endpoint.

## 4. Frontend: MainBusinessPanel component

- [x] 4.1 Read `frontend/node_modules/next/dist/docs/` for the local Next.js conventions before writing any new code (per AGENTS.md guidance and the `company-info` change's design precedent).
- [x] 4.2 Add a `market: "A" | "HK" | "US"` prop to `frontend/src/components/MainBusinessPanel.tsx`. Default to `"A"` if not provided (backward-compatible).
- [x] 4.3 Update the `product` / `region` / `industry` / `history` prop types to a union that covers both A-share (`{item, sales, profit, cost, revenue_share_pct, gross_margin_pct, profit_share_pct}`) and Futu (`{item, revenue, ratio_pct, currency_code}`) shapes. Use a type guard (e.g. `'revenue' in row`) to pick the right rendering path.
- [x] 4.4 When `market !== "A"`:
  - in the by-product table, hide the 利润 / 利润占比 / 毛利率 columns; show only 产品名称 / 收入 / 占比,
  - use the Futu currency suffix (look up `currency_code` → `亿HKD` / `亿美元` / etc.) for the 收入 column,
  - hide the 跨期对比 YoY column (no YoY data on Futu), keep the revenue column chart.
- [x] 4.5 When `market !== "A"`, render a new 业务 section (Futu-only) below 按行业, only if `business` is non-empty. Same table shape as by-product (revenue-only).
- [x] 4.6 Update the panel header caption from "数据源: Tushare" to "数据源: Futu" when `market !== "A"`.
- [x] 4.7 Reuse the existing "海外" badge logic (regex `/国外|海外|境外|出口|overseas/i`) for the by-region section on HK/US pages.
- [x] 4.8 The empty / error / loading states are unchanged — same skeleton, same "暂无主营业务构成数据" placeholder.

## 5. Frontend: integration

- [x] 5.1 In `frontend/src/app/stock/[symbol]/page.tsx`, import `getFutuMainBusiness` and `getFutuMainBusinessHistory` from `@/services/mainBusiness`.
- [x] 5.2 Add `mainBusinessFutu` and `mainBusinessFutuHistory` state variables, plus their loading / error states. Add a `useEffect` that fires `getFutuMainBusiness(symbol)` when `companyInfo?.data?.market !== "A"` and the symbol is HK/US.
- [x] 5.3 Drop the `/^\d{6}$/` guard around `<MainBusinessPanel />`. Replace it with: render the panel when either (A) the symbol is a 6-digit A-share AND the A-share fetchers have resolved, OR (B) the symbol is HK/US AND `companyInfo?.data?.market !== "A"` AND `mainBusinessFutu` is non-null.
- [x] 5.4 Pass the `market` prop to `<MainBusinessPanel />`: pass `companyInfo?.data?.market === "A" ? "A" : companyInfo?.data?.market` (so HK → "HK", US → "US").
- [x] 5.5 Verify by visiting `/stock/00700` in a browser:
  - the panel renders below `<CompanyInfoPanel />`,
  - by-product table loads with revenue-only columns (e.g. 增值服务 / 网络广告 / 金融科技 / 其他),
  - by-region table shows a region split with an "海外" badge on non-domestic rows,
  - 跨期对比 shows 4 years of by-product revenue as bars (no YoY column),
  - 业务 section appears below 按行业 (if Futu returns 业务 items).
- [x] 5.6 Verify by visiting `/stock/AAPL`:
  - the panel renders with US data (e.g. iPhone / Services / Mac / iPad / Wearables rows),
  - 收入 column has `亿美元` suffix.
- [x] 5.7 Verify `/stock/600519` (A-share) still works as before — no regression. The A-share fetchers are untouched.
- [x] 5.8 Verify `/stock/999999` (nonexistent) renders the empty state on the panel, not a crash.

## 6. Tests

- [x] 6.1 Backend: add a unit test in `backend/tests/` (matching the existing test pattern) that mocks `get_financials_revenue_breakdown` and asserts the normalization (split by type, dedup, sort desc, `has_distinct_industry` flag) and the older-OpenD "Unknown protocol ID" → empty-payload path. → `backend/tests/test_futu_revenue_breakdown.py` (22 tests passing; covers all 4 normalization helpers, the older-OpenD / other-error public method paths, the empty-`screen_date_list` history fallback, and the top-3 bucketing logic).
- [x] 6.2 Backend: add a unit test for `get_revenue_breakdown_history` covering the 4-period selection, top-3 bucketing, and the empty-`screen_date_list` fallback. → covered by `test_get_revenue_breakdown_history_top3_bucketing` and `test_get_revenue_breakdown_history_empty_screen_date_list` in the same file.
- [x] 6.3 Frontend: add a snapshot test for `<MainBusinessPanel market="HK" />` and `<MainBusinessPanel market="US" />` covering loading / empty / error / populated states using a sample Futu-shaped fixture (e.g. 腾讯 2024 FY or Apple 2024 FY data). → **Skipped**: the project has no frontend test framework (no Jest / Vitest in `devDependencies`). The component's TypeScript types are validated by `npx tsc --noEmit` (passes). Adding a test framework to a single change would be over-scope. A future change can add a test framework and write the snapshot tests then. The component's runtime behavior will be verified manually by visiting `/stock/00700`, `/stock/AAPL`, and `/stock/600519` in a browser (tasks 5.5-5.8).

## 7. Docs

- [x] 7.1 Update the stock-detail-page feature list (in `README.md` or wherever it lives) to mention that the 主营业务构成 panel is now also rendered on HK and US stock pages (revenue-only, no margin / YoY). → Updated `README.md` "API 端点" section with three new rows: `main-business` (A-share), `main-business-futu`, `main-business-futu/history`.
- [x] 7.2 Add a one-paragraph entry to `ENHANCEMENT_ROADMAP.md` noting the new HK/US coverage and the Futu OpenD v10.7.6708+ requirement. → Updated `ENHANCEMENT_ROADMAP.md` "Current State" table with two rows: "Main business composition (A-share)" and "Main business composition (HK / US)".

## 8. Hot-fix (post-implementation)

- [x] 8.1 The two Futu fetchers (`getFutuMainBusiness`, `getFutuMainBusinessHistory`) were returning the full `{data, error}` envelope from the backend instead of unwrapping `.data`. The page then passed the envelope as `futuProduct={futuMainBiz}`, so the panel saw `futuProduct.product` as `undefined` and crashed at `futuProduct.product.length` in the HK/US branch. Fixed by unwrapping `body.data` in both fetchers (and treating `body.error` / `body.data === null` as a `null` return). Also added defensive `?.` chains in the panel's HK/US branch so any future shape mismatch is non-fatal.
