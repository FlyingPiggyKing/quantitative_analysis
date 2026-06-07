## ADDED Requirements

### Requirement: A-share main business composition API

The backend MUST expose a `GET /api/stock/main-business` endpoint that returns Tushare `fina_mainbz` data for a given A-share symbol, with optional `period` and `type` filters. The endpoint MUST return data normalized into a consistent shape including derived share and margin metrics.

#### Scenario: Default request for an A-share returns latest period by product
- **WHEN** client calls `GET /api/stock/main-business?symbol=600519` with no `period` or `type`
- **THEN** backend calls Tushare `fina_mainbz` with the latest available annual period and `type='P'`
- **AND** returns `{ts_code, period, type, rows: [{item, sales, profit, cost, curr_type, revenue_share_pct, gross_margin_pct, profit_share_pct}], source: "tushare", updated_at}`

#### Scenario: Type filter selects dimension
- **WHEN** client calls `GET /api/stock/main-business?symbol=600519&type=D`
- **THEN** backend calls Tushare with `type='D'` and returns by-region rows
- **AND** when `type=I` returns by-industry rows
- **AND** when `type=P` (or omitted) returns by-product rows

#### Scenario: Period filter selects reporting period
- **WHEN** client calls `GET /api/stock/main-business?symbol=600519&period=20231231`
- **THEN** backend calls Tushare with that period
- **AND** if Tushare returns no rows for that period, backend returns `{rows: [], period: "20231231"}` with HTTP 200 (not an error)

#### Scenario: Derived metrics are computed server-side
- **WHEN** backend normalizes the Tushare response
- **THEN** `revenue_share_pct` is computed as `bz_sales / sum(bz_sales) * 100`, rounded to 2 decimals
- **AND** `profit_share_pct` is computed as `bz_profit / sum(bz_profit) * 100`, rounded to 2 decimals
- **AND** `gross_margin_pct` is computed as `(bz_sales - bz_cost) / bz_sales * 100` when both `bz_sales` and `bz_cost` are non-null, otherwise `null`

#### Scenario: Duplicate rows are dropped
- **WHEN** Tushare returns rows with identical `(bz_item, bz_sales, bz_cost, curr_type)` tuples
- **THEN** backend deduplicates, keeping the first occurrence
- **AND** the deduped set is sorted by `bz_sales` descending before returning

#### Scenario: Non-A-share symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/main-business?symbol=AAPL` (non-6-digit or non-A-share)
- **THEN** backend returns HTTP 400 with `{"error": "仅支持 A 股 6 位代码"}`

#### Scenario: Tushare error returns HTTP 502 with safe error message
- **WHEN** Tushare call fails or returns a non-zero code
- **THEN** backend returns HTTP 502 with `{"error": "Tushare 数据源异常", "ts_code": "..."}`

#### Scenario: Cross-period endpoint returns last 4 annual periods
- **WHEN** client calls `GET /api/stock/main-business/history?symbol=600519&type=P&top=3`
- **THEN** backend returns the top-N product lines (by latest-period revenue) with revenue across the last 4 annual periods
- **AND** response shape is `{ts_code, type, periods: [string], series: [{item, currency, values: [{period, sales, profit, cost, gross_margin_pct, yoy_pct}]}]}`

### Requirement: Main business data is cached

The backend MUST cache `fina_mainbz` responses per `(ts_code, type, period)` to avoid burning Tushare rate-limit points on repeat calls.

#### Scenario: Cache hit does not call Tushare
- **WHEN** the same `(ts_code, type, period)` is requested within 24h
- **THEN** backend returns the cached response without calling Tushare

#### Scenario: Cache miss calls Tushare and stores result
- **WHEN** `(ts_code, type, period)` has no cache entry or entry is older than 24h
- **THEN** backend calls Tushare, stores the normalized response in the cache
- **AND** subsequent calls within 24h return the cached value

#### Scenario: Tushare error does not poison cache
- **WHEN** Tushare call fails
- **THEN** backend MUST NOT store an empty/error response in the cache
- **AND** the next request retries the upstream call

### Requirement: A-share stock detail page renders main business panel

For symbols matching `/^\d{6}$/`, the stock detail page MUST render a `<MainBusinessPanel />` component directly below the existing `<CompanyInfoPanel />` component.

#### Scenario: A-share page shows all four sections
- **WHEN** user navigates to `/stock/600519`
- **THEN** page renders the main-business panel with sections in this order: 按产品, 按地区, 按行业 (only if it adds rows beyond P), 跨期对比

#### Scenario: Panel renders loading skeleton during fetch
- **WHEN** panel is fetching data
- **THEN** panel renders a vintage-style skeleton (4 placeholder rows × 4 columns) in place of the by-product table

#### Scenario: Panel renders empty state on no data
- **WHEN** backend returns `{rows: []}` for all four sections
- **THEN** panel renders "暂无主营业务构成数据" placeholder and does not throw

#### Scenario: Panel renders error state on upstream failure
- **WHEN** backend returns HTTP 502
- **THEN** panel renders "数据加载失败，请稍后重试" placeholder; the rest of the page is unaffected

#### Scenario: Non-A-share pages do not render the panel
- **WHEN** user navigates to a US or HK stock page (e.g. `/stock/AAPL`, `/stock/00700`)
- **THEN** the main-business panel MUST NOT be rendered

### Requirement: By-product section shows table and bar chart

The by-product section MUST display each product as a row with revenue, profit, gross margin, revenue share, and profit share. It MUST also display a horizontal stacked bar visualizing revenue share.

#### Scenario: Each row shows 6 columns
- **WHEN** by-product section renders
- **THEN** each row shows: 产品名称, 收入(亿), 收入占比, 利润(亿), 利润占比, 毛利率
- **AND** gross margin is shown as `—` when cost is null

#### Scenario: Stacked bar visualizes revenue share
- **WHEN** by-product section renders 3+ rows
- **THEN** a horizontal stacked bar (one segment per product, color-coded) shows revenue share
- **AND** segment widths are proportional to `revenue_share_pct`
- **AND** segments are sorted left-to-right by share descending

### Requirement: By-region section emphasizes overseas share

The by-region section MUST show a compact 2-column table (region, revenue share) and visually emphasize any "国外" / "海外" / "境外" / "其他境外" / "出口" / "overseas" segment with a distinct badge.

#### Scenario: Overseas badge appears for non-domestic rows
- **WHEN** by-region data includes any row whose `item` matches `/国外|海外|境外|出口|overseas/i`
- **THEN** that row renders with a "海外" badge
- **AND** the row's revenue share is highlighted in the bar visualization

#### Scenario: Empty by-region data is hidden
- **WHEN** backend returns `{rows: []}` for the by-region section
- **THEN** the by-region section header is hidden (not rendered with empty state)

### Requirement: By-industry section is shown only when distinct

The by-industry section MUST be rendered only when the by-industry rows add items beyond the by-product rows, or when at least one by-industry row has a different `item` name than any by-product row.

#### Scenario: Identical to P hides the by-industry section
- **WHEN** every by-industry row's `item` matches a by-product row's `item`
- **THEN** the by-industry section is hidden

#### Scenario: Distinct industries are shown
- **WHEN** by-industry data contains an `item` not present in by-product data
- **THEN** the by-industry section is rendered with that distinct row

### Requirement: Cross-period section shows top-3 product lines over 4 years

The cross-period section MUST fetch the last 4 annual periods of by-product data and display, for the top-3 product lines by latest-period revenue, a column chart of revenue and a year-over-year growth table.

#### Scenario: Top-3 selection
- **WHEN** cross-period data is rendered
- **THEN** backend selects the 3 product lines with highest `bz_sales` in the most recent annual period
- **AND** other product lines are aggregated into a single "其他" row

#### Scenario: YoY growth computed for each period transition
- **WHEN** cross-period data spans periods P1, P2, P3, P4 (chronological)
- **THEN** `yoy_pct` for P_n is `(sales_Pn - sales_Pn-1) / sales_Pn-1 * 100`, rounded to 2 decimals
- **AND** P1's yoy is `null` (no prior period to compare)

#### Scenario: YoY rendered as colored delta
- **WHEN** cross-period section renders
- **THEN** each non-null yoy value is shown with a sign prefix (`+` for ≥ 0, `-` for < 0) and color (green / red)
- **AND** null yoy is shown as `—`

### Requirement: Currency and unit normalization

All monetary values MUST be returned and rendered in CNY 亿元 (divide by 1e8 from raw `bz_sales`/`bz_profit`/`bz_cost`).

#### Scenario: Backend returns raw values
- **WHEN** backend returns the response
- **THEN** `sales`, `profit`, `cost` are raw CNY 元 (matching Tushare)
- **AND** `curr_type` is included per row (informational, always `CNY` for A-shares)

#### Scenario: Frontend converts to 亿元
- **WHEN** the panel renders any monetary value
- **THEN** the value is divided by 1e8 and displayed with the suffix `亿元`
- **AND** values are right-aligned and shown with 2 decimals (or `—` when null)
