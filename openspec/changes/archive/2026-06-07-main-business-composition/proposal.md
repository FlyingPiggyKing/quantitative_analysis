## Why

The `CompanyInfoPanel` introduced in the `company-info` change (Tushare `stock_company`, doc_id=112) shows static profile text (registered capital, chairman, main_business 文本简介) but tells the user **nothing about revenue mix** — i.e. which products / regions / industries actually drive the business and how that's shifting over time. Tushare's `fina_mainbz` (doc_id=81) returns structured revenue/profit/cost rows by product (P), region (D), and industry (I), and is the canonical source for this view. Mining it gives users actionable context (e.g. "auto revenue is 79% of BYD's mix", "CATL overseas is now 30%") that the existing panel cannot provide.

## What Changes

- Add `AShareService.get_main_business_composition(ts_code, period?, type?)` that wraps Tushare `fina_mainbz` and normalizes the response (drop fully-NaN cost rows, drop exact-duplicate `(bz_item, bz_sales, bz_cost)` rows, compute `revenue_share_pct`, `gross_margin_pct`, `profit_share_pct`).
- Add `GET /api/stock/main-business?symbol=...&period=...&type=...` returning the latest available period by default, with optional `period` override and `type` ∈ {`P`, `D`, `I`}. A-share only (HTTP 400 for other symbols).
- Add a new `<MainBusinessPanel />` React component that renders below the existing `CompanyInfoPanel` with four sections:
  1. **按产品 (P)** — table + stacked bar of revenue share per product, with gross margin overlay.
  2. **按地区 (D)** — table + revenue-share bar; visually emphasize overseas/国外 share.
  3. **按行业 (I)** — table (often identical to P for vertically-integrated firms; render only if it adds rows beyond P).
  4. **跨期对比** — line/column chart of the top-3 product lines' revenue across the last 4 annual periods (2021/2022/2023/2024), with year-over-year growth %.
- Cache main-business data per `(ts_code, type, period)` for 24h — Tushare data updates only on quarterly reports.
- Graceful empty/error states; loading skeleton in vintage style consistent with `CompanyInfoPanel`.

## Capabilities

### New Capabilities

- `main-business-composition`: A-share listed-company main-business composition. Backend exposes Tushare `fina_mainbz` data (with derived share/margin metrics) via `/api/stock/main-business`; frontend renders a panel below the existing `CompanyInfoPanel` showing by-product, by-region, by-industry, and cross-period views.

### Modified Capabilities

- (none) — the existing `company-info` spec's REQUIREMENTS are unchanged. This change is purely additive: a new panel below the existing one. No existing endpoint or component behavior is altered.

## Impact

- **Backend**:
  - `backend/services/akshare_service.py` — new `AShareService.get_main_business_composition` (and a thin batch helper if convenient).
  - `backend/api/stock.py` — new `GET /api/stock/main-business` route.
  - Reuse `_YFCache` pattern with a 24h TTL keyed by `(ts_code, type, period)`.
  - Requires Tushare token with ≥ 2000 points (`fina_mainbz` tier).
- **Frontend**:
  - `frontend/src/app/stock/[symbol]/page.tsx` — for A-share symbols, render the new `<MainBusinessPanel />` directly below `<CompanyInfoPanel />`.
  - New component `frontend/src/components/MainBusinessPanel.tsx`.
  - Reuse the existing `useState`/`useEffect` fetch pattern (no new `useSWR`).
- **Data caveats** (encoded in backend normalization, surfaced in spec):
  - Some `bz_cost` values are `NaN` (esp. in `D` dimension) → gross margin shown as `—`.
  - Duplicate `(bz_item, bz_sales, bz_cost)` rows exist for some companies (茅台 系列酒 / 其他酒系列) → dedup at the backend.
  - No `update_flag` field in actual response — do not promise it in the API.
  - 货币统一为 `CNY`（A 股），no FX conversion needed.
- **Failure modes**: Tushare error / empty → panel shows "暂无主营业务构成数据"; page otherwise unaffected. The panel must never block the rest of the page from rendering.
