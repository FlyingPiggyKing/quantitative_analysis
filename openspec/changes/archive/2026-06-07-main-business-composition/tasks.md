## 1. Backend: service method

- [x] 1.1 Add `_main_biz_cache = _YFCache(ttl=86400)` module-level instance in `backend/services/akshare_service.py` next to the existing `_yf_cache`.
- [x] 1.2 Add `AShareService.get_main_business_composition(ts_code, period=None, type='P')` method that:
  - calls `ts.pro_api().fina_mainbz(ts_code=ts_code, period=period, type=type)`,
  - drops rows where `bz_sales` is NaN,
  - drops fully duplicate `(bz_item, bz_sales, bz_cost, curr_type)` tuples (keep first),
  - computes `revenue_share_pct`, `profit_share_pct`, `gross_margin_pct` per row,
  - sorts by `bz_sales` desc,
  - caches the normalized response under key `(ts_code, type, period or 'latest')`,
  - returns `{ts_code, period, type, rows, source: 'tushare', updated_at}` or `{'rows': []}` on empty.
- [x] 1.3 Add `AShareService.get_main_business_history(ts_code, type='P', top=3)` method that:
  - computes the 4 most recent annual periods (`YYYY1231`) ending at the last full year,
  - calls `fina_mainbz(ts_code=ts_code, type=type, end_date=last_period)` with the explicit list,
  - groups rows by `bz_item`, picks top-`top` by latest-period `bz_sales`, buckets the rest as `其他`,
  - for each series computes `gross_margin_pct` and `yoy_pct` per period (null for first period),
  - caches under `(ts_code, type, 'history', top, last_period)`.
- [x] 1.4 Add a `has_distinct_industry(ts_code, period=None)` helper or fold the check into the response by also fetching `type='I'` once and comparing item sets.

## 2. Backend: API routes

- [x] 2.1 Add `GET /api/stock/main-business` route in `backend/api/stock.py`:
  - validates `symbol` is `/^\d{6}$/` (else HTTP 400 with `{"error": "仅支持 A 股 6 位代码"}`),
  - converts symbol → ts_code via existing `_symbol_to_ts_code`,
  - accepts optional `period` and `type` (default `type='P'`, default `period=None`),
  - calls the service method, returns JSON.
  - on Tushare error returns HTTP 502 with `{"error": "Tushare 数据源异常", "ts_code": "..."}`.
- [x] 2.2 Add `GET /api/stock/main-business/history` route:
  - same symbol validation,
  - accepts `type` (default `'P'`) and `top` (default `3`),
  - calls `get_main_business_history` and returns JSON.
- [x] 2.3 Verify both routes with a local curl:
  - `curl 'http://localhost:8000/api/stock/main-business?symbol=600519&type=P'` returns the by-product table,
  - `curl 'http://localhost:8000/api/stock/main-business?symbol=600519&type=D'` returns the by-region table,
  - `curl 'http://localhost:8000/api/stock/main-business/history?symbol=600519'` returns 3-series cross-period data,
  - `curl 'http://localhost:8000/api/stock/main-business?symbol=AAPL'` returns HTTP 400.

## 3. Frontend: data fetching

- [x] 3.1 Open `frontend/src/app/stock/[symbol]/page.tsx` and locate the `<CompanyInfoPanel />` insertion point.
- [x] 3.2 Add `mainBusiness`, `mainBusinessLoading`, `mainBusinessError` state and a fetcher for `/api/stock/main-business?symbol=...&type=P` triggered inside the existing `useEffect` chain (matching the `CompanyInfoPanel` pattern, no `useSWR`).
- [x] 3.3 Add a second fetcher for `?type=D` and a third for `?type=I` (or fold into a single call by adding an `expand` flag — match the backend contract from step 1.4). Default: 3 separate calls, each with its own loading state.
- [x] 3.4 Add a fourth fetcher for `/api/stock/main-business/history?symbol=...&type=P` for the cross-period section.
- [x] 3.5 Compute `hasDistinctIndustry` client-side from the P and I responses: `I items ⊆ P items` ⇒ `false`; else `true`.
- [x] 3.6 Render `<MainBusinessPanel />` only when `symbol` matches `/^\d{6}$/` AND `mainBusiness` is non-null (i.e. the by-product call has resolved). Place it directly below `<CompanyInfoPanel />`.

## 4. Frontend: MainBusinessPanel component

- [x] 4.1 Create `frontend/src/components/MainBusinessPanel.tsx`. Read `frontend/node_modules/next/dist/docs/` for the local Next.js conventions before writing (per AGENTS.md guidance and the `company-info` change's design precedent).
- [x] 4.2 Define props: `{ symbol: string; product: ProductResponse | null; region: ProductResponse | null; industry: ProductResponse | null; history: HistoryResponse | null; loading: { p: boolean; d: boolean; i: boolean; h: boolean }; error: ApiError | null }`. Convert monetary values from 元 → 亿元 in the component (`value / 1e8`, suffix `亿元`, 2 decimals, `—` for null).
- [x] 4.3 Render the panel header: `主营业务构成` in vintage style, with a small "数据源: Tushare" caption.
- [x] 4.4 Render `按产品` section: 6-column table (产品名称, 收入, 收入占比, 利润, 利润占比, 毛利率) + a CSS-only horizontal stacked bar (one segment per product, distinct Tailwind muted color per row, widths = `revenue_share_pct`). Sort by `bz_sales` desc. While loading, show a 4×6 skeleton.
- [x] 4.5 Render `按地区` section: 2-column table (地区, 收入) + bar. Apply the `/国外|海外|境外|出口|overseas/i` regex to `item` and render an "海外" badge on matching rows. Hide section if `region.rows` is empty.
- [x] 4.6 Render `按行业` section only if `hasDistinctIndustry === true`. Same table shape as the by-product section. Otherwise render nothing (no header, no placeholder).
- [x] 4.7 Render `跨期对比` section: column chart (4 columns per top-3 product) + a 4-column YoY table. Bar heights = `sales / max(sales) * 100`%. Color-code yoy: `+` and ≥ 0 → green, `< 0` → red. Null yoy → `—`. Hide section if `history` is null or has fewer than 2 non-null periods.
- [x] 4.8 Render empty state: if all four section data sources are empty/null, render a single `暂无主营业务构成数据` placeholder inside the panel; do not throw.
- [x] 4.9 Render error state: if `error` is non-null, render a single `数据加载失败，请稍后重试` placeholder inside the panel; the rest of the page must remain functional.

## 5. Frontend: integration

- [x] 5.1 In `frontend/src/app/stock/[symbol]/page.tsx`, import `MainBusinessPanel` and the fetcher helpers.
- [x] 5.2 Insert `<MainBusinessPanel ... />` below `<CompanyInfoPanel />`, gated on `/^\d{6}$/.test(symbol)`.
- [x] 5.3 Verify by visiting `/stock/600519` in a browser:
  - panel renders below company info,
  - by-product table loads with茅台酒 / 系列酒 / 其他业务 rows and a 3-segment stacked bar,
  - by-region table shows 中国大陆 97% / 国外 3% with an "海外" badge on the 国外 row,
  - by-industry section is hidden (茅台 reports industries identical to products),
  - cross-period section shows 3 series × 4 years with green YoY deltas.
- [x] 5.4 Verify `/stock/AAPL` does NOT render the panel.
- [x] 5.5 Verify `/stock/999999` (nonexistent) renders an empty state, not a crash.

## 6. Tests

- [x] 6.1 Backend: add a test in `backend/` (matching the existing test pattern) that mocks `fina_mainbz` and asserts the normalization (dedup, sort desc, derived metrics) and the HTTP 400 / 502 error paths.
- [x] 6.2 Backend: add a test for `get_main_business_history` covering the top-N selection and yoy computation.
- [x] 6.3 Frontend: add a snapshot test for `MainBusinessPanel` covering all four states (loading, empty, error, populated) using a sample `ProductResponse` fixture (e.g. 比亚迪 2024 by-product data).

## 7. Docs

- [x] 7.1 Update `README.md` (or wherever the stock-detail-page feature list lives) to mention the new panel.
- [x] 7.2 Add a one-paragraph entry to `ENHANCEMENT_ROADMAP.md` noting the new panel and the Tushare permission tier required.
