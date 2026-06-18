## ADDED Requirements

### Requirement: HK/US main business composition API

The backend MUST expose a `GET /api/stock/main-business-futu` endpoint that returns Futu `get_financials_revenue_breakdown` (proto 3228, v10.7+) data for a given HK or US symbol, normalized into a consistent shape covering all four breakdown dimensions (产品 / 行业 / 地区 / 业务).

The endpoint MUST dispatch by symbol:
- Symbols matching `/^HK\.\d{4,5}$/` or `/^\d{4,5}$/` → HK path via `FutuQuoteService.get_revenue_breakdown`.
- Symbols matching `/^US\.[A-Z]{1,5}$/` or `/^[A-Z]{1,5}$/` → US path via `FutuQuoteService.get_revenue_breakdown`.
- All other inputs (including 6-digit A-share codes) → HTTP 400 with `{"error": "Unsupported symbol"}`. The existing A-share endpoint at `/api/stock/main-business?type=P&period=...&top=...` is NOT affected.

The response shape on success MUST be:

```json
{
  "symbol": "00700",
  "code": "HK.00700",
  "market": "HK",
  "period": "2024/FY",
  "currency_code": "HKD",
  "product":  [{"item": "...", "revenue": 1.23e10, "ratio_pct": 52.34, "currency_code": "HKD"}],
  "region":   [...],
  "industry": [...],
  "business": [...],
  "has_distinct_industry": false,
  "source": "futu",
  "updated_at": "2025-05-20T12:00:00Z"
}
```

Each item is `{item, revenue, ratio_pct, currency_code}`. The `revenue` field is the raw Futu value in the stock's reporting currency (HKD for HK, USD for US, etc.) — the frontend converts to 亿元 by dividing by 1e8. The `ratio_pct` field is the pre-computed percentage (e.g. 12.34 means 12.34%). The `currency_code` field is the ISO 4217 code (HKD, USD, etc.). An empty dimension (e.g. no industry items) MUST be `[]`, not `null`.

#### Scenario: HK bare-numeric symbol returns normalized payload
- **WHEN** client calls `GET /api/stock/main-business-futu?symbol=00700`
- **THEN** backend resolves to Futu code `HK.00700`
- **AND** calls `OpenQuoteContext.get_financials_revenue_breakdown("HK.00700")`
- **AND** returns `{symbol: "00700", code: "HK.00700", market: "HK", period: <from Futu>, currency_code: "HKD", product: [...], region: [...], industry: [...], business: [...], has_distinct_industry, source: "futu", updated_at}`
- **AND** each list is sorted by `revenue` desc
- **AND** `revenue` values are raw HKD (e.g. 1.23e10), not pre-divided

#### Scenario: HK dotted-form symbol returns same payload
- **WHEN** client calls `GET /api/stock/main-business-futu?symbol=HK.00700`
- **THEN** backend returns the same response shape as the bare-numeric form
- **AND** `code === "HK.00700"`

#### Scenario: US symbol returns normalized payload
- **WHEN** client calls `GET /api/stock/main-business-futu?symbol=AAPL`
- **THEN** backend resolves to Futu code `US.AAPL`
- **AND** returns `{symbol: "AAPL", code: "US.AAPL", market: "US", ..., currency_code: "USD", ...}`

#### Scenario: A-share symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/main-business-futu?symbol=600519`
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`
- **AND** does NOT call the Tushare `fina_mainbz` endpoint

#### Scenario: Invalid symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/main-business-futu?symbol=BAD-CHAR!` or any string matching none of the regexes above
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`
- **AND** does NOT call Futu

#### Scenario: All four dimensions returned in a single call
- **WHEN** Futu returns `breakdown_list` with `type` ∈ {1=Product, 2=Industry, 4=Region, 8=Business}
- **THEN** backend splits them into the response's `product`, `industry`, `region`, `business` lists
- **AND** each list is sorted by `revenue` desc
- **AND** items with null or zero revenue are dropped
- **AND** fully duplicate `(item, revenue, ratio_pct, currency_code)` tuples are deduplicated (keep first)

#### Scenario: `has_distinct_industry` flag is computed
- **WHEN** backend normalizes the Futu response
- **THEN** `has_distinct_industry` is `true` if at least one industry item's `item` name is not in the product item set
- **AND** `false` otherwise

#### Scenario: Older OpenD returns clean empty payload
- **WHEN** Futu OpenD is older than 10.7.6708 and returns "Unknown protocol ID" on `get_financials_revenue_breakdown`
- **THEN** backend returns 200 with `{symbol, code, market, period: "", currency_code: "", product: [], region: [], industry: [], business: [], has_distinct_industry: false, source: "futu", updated_at: <now>}`
- **AND** does NOT leak the raw "Unknown protocol ID" error to the client

#### Scenario: Other Futu upstream error returns clean error envelope
- **WHEN** Futu raises any other exception (network blip, unknown symbol, etc.)
- **THEN** backend returns 200 with `{"data": null, "error": "获取主营构成失败: <msg capped at 120 chars>"}`
- **AND** does NOT return a 5xx status

#### Scenario: Futu error does not poison cache
- **WHEN** `get_revenue_breakdown` raises
- **THEN** backend MUST NOT store an empty/error response in `_company_info_cache`
- **AND** the next request retries the upstream call

### Requirement: HK/US main business composition history API

The backend MUST expose a `GET /api/stock/main-business-futu/history?symbol=<hk-or-us>&n_periods=4` endpoint that returns the last N annual periods of by-product data via parallel `get_financials_revenue_breakdown` calls (each with a different `date` from `screen_date_list`).

The response shape MUST be:

```json
{
  "symbol": "00700",
  "code": "HK.00700",
  "market": "HK",
  "currency_code": "HKD",
  "periods": ["2021/FY", "2022/FY", "2023/FY", "2024/FY"],
  "items": [
    {
      "item": "增值服务",
      "currency_code": "HKD",
      "values": [
        {"period": "2021/FY", "revenue": 1.0e10, "ratio_pct": 50.0},
        {"period": "2022/FY", "revenue": 1.1e10, "ratio_pct": 51.0},
        {"period": "2023/FY", "revenue": 1.2e10, "ratio_pct": 52.0},
        {"period": "2024/FY", "revenue": 1.3e10, "ratio_pct": 53.0}
      ]
    }
  ],
  "source": "futu",
  "updated_at": "..."
}
```

The top 3 product lines (by latest-period revenue) are kept; the rest are bucketed as `其他`. The `values` array length MUST equal `periods.length`. Each `revenue` is raw reporting currency (HKD / USD), not pre-divided.

#### Scenario: HK history returns 4 annual periods
- **WHEN** client calls `GET /api/stock/main-business-futu/history?symbol=00700`
- **THEN** backend calls `get_financials_revenue_breakdown("HK.00700")` first to obtain `screen_date_list`
- **AND** filters for annual periods (preferring `financial_type == 7` 年报, falling back to `period_text` ending in `/FY`)
- **AND** takes the 4 most recent `date` values
- **AND** fires 4 parallel `get_financials_revenue_breakdown("HK.00700", date=d)` calls
- **AND** merges the results into a `periods[]` + `items[]` response
- **AND** returns the top 3 by latest-period revenue, with the rest bucketed as `其他`

#### Scenario: History with fewer than 4 annual periods
- **WHEN** the company has fewer than 4 annual periods in `screen_date_list` (e.g. recent IPO)
- **THEN** backend returns only the periods that exist
- **AND** the response is HTTP 200 (not an error)
- **AND** the `periods` array length equals the actual number of periods returned

#### Scenario: History with empty screen_date_list returns empty payload
- **WHEN** `screen_date_list` is empty or only has non-annual entries
- **THEN** backend returns 200 with `{periods: [], items: [], source: "futu", updated_at: <now>}`
- **AND** does NOT raise

#### Scenario: A-share symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/main-business-futu/history?symbol=600519`
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`

#### Scenario: Older OpenD returns empty history
- **WHEN** Futu OpenD is older than 10.7.6708 and returns "Unknown protocol ID"
- **THEN** backend returns 200 with `{periods: [], items: [], source: "futu", updated_at: <now>}`
- **AND** does NOT leak the raw error

### Requirement: HK/US main business data is cached

The backend MUST cache `get_financials_revenue_breakdown` responses to avoid burning Futu OpenD capacity on repeat calls. The cache MUST be the existing `_company_info_cache` (24h TTL).

#### Scenario: Cache hit does not call Futu
- **WHEN** the same `revenue_breakdown:{symbol}` key is requested within 24h
- **THEN** backend returns the cached payload without calling Futu

#### Scenario: Cache miss calls Futu and stores result
- **WHEN** the cache key has no entry or entry is older than 24h
- **THEN** backend calls Futu, stores the normalized payload in the cache
- **AND** subsequent calls within 24h return the cached value

#### Scenario: History cache is keyed by (symbol, n_periods)
- **WHEN** the same `revenue_breakdown_history:{symbol}:{n_periods}` key is requested within 24h
- **THEN** backend returns the cached payload without calling Futu

#### Scenario: Futu error does not poison cache
- **WHEN** the upstream Futu call fails
- **THEN** backend MUST NOT store an empty/error response in the cache
- **AND** the next request retries the upstream call

### Requirement: HK and US stock detail pages render main business panel

For symbols matching the HK regex (`/^\d{4,5}$/` or `/^HK\.\d{4,5}$/`) or US regex (`/^[A-Z]{1,5}$/` or `/^US\.[A-Z]{1,5}$/`), the stock detail page MUST render the `<MainBusinessPanel />` component directly below the existing `<CompanyInfoPanel />`. The component MUST be passed a `market` prop set to `"HK"` or `"US"`. For A-share symbols, the existing A-share behavior (unchanged) is preserved.

#### Scenario: HK page renders the panel with HK data
- **WHEN** user navigates to `/stock/00700`
- **THEN** page fetches `/api/stock/main-business-futu?symbol=00700` and `/api/stock/main-business-futu/history?symbol=00700`
- **AND** renders `<MainBusinessPanel market="HK" product={...} region={...} industry={...} business={...} history={...} />` below `<CompanyInfoPanel />`
- **AND** the panel renders sections in this order: 按产品, 按地区, 按行业 (only if `has_distinct_industry` is true), 业务 (only if non-empty), 跨期对比 (only if 1+ period exists)

#### Scenario: US page renders the panel with US data
- **WHEN** user navigates to `/stock/AAPL`
- **THEN** page fetches `/api/stock/main-business-futu?symbol=AAPL` and `/api/stock/main-business-futu/history?symbol=AAPL`
- **AND** renders `<MainBusinessPanel market="US" ... />` below `<CompanyInfoPanel />`

#### Scenario: A-share page is unaffected
- **WHEN** user navigates to `/stock/600519`
- **THEN** page continues to call the existing A-share endpoints (`/api/stock/main-business?type=P` etc.)
- **AND** renders `<MainBusinessPanel market="A" ... />` with the existing A-share columns (full 6-column by-product table including 毛利率 / 利润占比; 跨期对比 with YoY column)
- **AND** the new Futu endpoints are NOT called

#### Scenario: HK/US panel renders loading skeleton during fetch
- **WHEN** the Futu fetch is in flight
- **THEN** panel renders the same vintage-style skeleton as the A-share panel (4 placeholder rows × 4 columns) in place of the by-product table

#### Scenario: HK/US panel renders empty state on no data
- **WHEN** backend returns `{product: [], region: [], industry: [], business: []}` (empty payload from older OpenD, or symbol with no breakdown)
- **THEN** panel renders "暂无主营业务构成数据" placeholder
- **AND** does not throw

#### Scenario: HK/US panel renders error state on upstream failure
- **WHEN** backend returns `{data: null, error: "..."}`
- **THEN** panel renders "暂无主营业务构成数据" placeholder (mirrors the older-OpenD empty case; the error is logged but not surfaced to the user)
- **AND** the rest of the page is unaffected

### Requirement: HK/US by-product section shows revenue-only table

The by-product section for HK/US pages MUST display each product as a row with item name, revenue (in 亿元 with currency suffix), and ratio percentage. It MUST NOT display profit, cost, gross margin, or profit share (Futu does not provide these fields).

#### Scenario: Each row shows 3 columns for HK/US
- **WHEN** `market` is `"HK"` or `"US"` and the by-product section renders
- **THEN** each row shows: 产品名称, 收入 (亿元 + currency suffix), 占比 (%)
- **AND** the 利润 / 利润占比 / 毛利率 columns are hidden
- **AND** the currency suffix is `亿HKD` for HK and `亿美元` for US (derived from `currency_code`)

#### Scenario: Stacked bar visualizes revenue share
- **WHEN** the by-product section renders 3+ rows
- **THEN** a horizontal stacked bar (one segment per product, color-coded) shows revenue share
- **AND** segment widths are proportional to `ratio_pct`
- **AND** segments are sorted left-to-right by ratio descending

### Requirement: HK/US by-region section emphasizes overseas share

The by-region section for HK/US pages MUST show a compact 2-column table (region, revenue share) and visually emphasize any "国外" / "海外" / "境外" / "其他境外" / "出口" / "overseas" segment with a distinct badge.

#### Scenario: Overseas badge appears for non-domestic rows
- **WHEN** by-region data includes any row whose `item` matches `/国外|海外|境外|出口|overseas/i` (case-insensitive)
- **THEN** that row renders with an "海外" badge
- **AND** the row's revenue share is highlighted in the bar visualization

#### Scenario: Empty by-region data is hidden
- **WHEN** backend returns `region: []` for the by-region section
- **THEN** the by-region section header is hidden (not rendered with empty state)

### Requirement: HK/US by-industry section is shown only when distinct

The by-industry section for HK/US pages MUST be rendered only when `has_distinct_industry` is `true` (i.e. at least one industry item's name is not in the product item set). When hidden, no header, no placeholder.

#### Scenario: Industries identical to products hides the by-industry section
- **WHEN** every industry row's `item` matches a product row's `item` (or the industry list is empty)
- **THEN** the by-industry section is hidden

#### Scenario: Distinct industries are shown
- **WHEN** `has_distinct_industry` is `true`
- **THEN** the by-industry section is rendered with revenue-only columns (产品 / 收入 / 占比)

### Requirement: HK/US by-business section is shown when present

The by-business section for HK/US pages MUST be rendered when `business` is non-empty. The by-business dimension is Futu-specific (Tushare does not provide it). When empty, the section is hidden.

#### Scenario: Empty by-business data is hidden
- **WHEN** backend returns `business: []` for the by-business section
- **THEN** the by-business section is hidden (no header, no placeholder)

#### Scenario: Non-empty by-business data is shown
- **WHEN** backend returns 1+ business items
- **THEN** the by-business section is rendered below 按行业 with revenue-only columns (业务 / 收入 / 占比)
- **AND** a small vintage caption "数据源: Futu · 业务" identifies the dimension

### Requirement: HK/US cross-period section shows top-3 product lines over up to 4 years

The cross-period section for HK/US pages MUST fetch up to 4 annual periods of by-product data and display, for the top-3 product lines by latest-period revenue, a column chart of revenue. The chart MUST NOT include a year-over-year percentage column (Futu does not provide cost/profit, so YoY revenue % is not surfaced; the bar heights themselves communicate the trend).

#### Scenario: Top-3 selection with 其他 bucket
- **WHEN** cross-period history is rendered
- **THEN** backend selects the 3 product lines with highest latest-period revenue
- **AND** other product lines are aggregated into a single "其他" row

#### Scenario: Bar heights proportional to revenue
- **WHEN** the cross-period section renders
- **THEN** bar heights are `revenue / max(revenue) * 100`% within each period
- **AND** the y-axis label is `收入` with the currency suffix
- **AND** the x-axis lists the periods chronologically

#### Scenario: Fewer than 2 periods hides the cross-period section
- **WHEN** the history response has 0 or 1 period (e.g. recent IPO)
- **THEN** the cross-period section is hidden

### Requirement: Currency and unit normalization for HK/US

All monetary values in the HK/US panel MUST be rendered in the stock's reporting currency, divided by 1e8 to display in 亿元 (with the currency suffix).

#### Scenario: Backend returns raw values
- **WHEN** backend returns the response
- **THEN** `revenue` is the raw Futu value in the stock's reporting currency (HKD for HK, USD for US, etc.)
- **AND** `currency_code` is included per item and at the top level (informational; matches Futu's response)

#### Scenario: Frontend converts to 亿元 with currency suffix
- **WHEN** the panel renders any monetary value
- **THEN** the value is divided by 1e8 and displayed with the suffix `亿HKD` for HK, `亿美元` for US, etc.
- **AND** values are right-aligned and shown with 2 decimals (or `—` when null)
- **AND** the suffix is derived from the `currency_code` field of the response

### Requirement: HK/US data source caption identifies Futu

The panel header caption for HK/US pages MUST read `数据源: Futu` (vs the A-share caption `数据源: Tushare`).

#### Scenario: HK/US panel shows Futu caption
- **WHEN** `market` is `"HK"` or `"US"`
- **THEN** the panel header caption is `数据源: Futu`

#### Scenario: A-share panel continues to show Tushare caption
- **WHEN** `market` is `"A"`
- **THEN** the panel header caption is `数据源: Tushare` (unchanged from the existing A-share behavior)
