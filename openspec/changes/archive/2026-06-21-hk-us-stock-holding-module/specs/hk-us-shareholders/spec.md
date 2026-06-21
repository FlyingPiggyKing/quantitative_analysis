# hk-us-shareholders Specification

## Purpose

Renders a single Overview panel on HK and US stock detail pages with four
analytical sub-sections backed by Futu OpenD v10.7.6708+:

1. **股东概览** — donut of holder-type distribution + Top-5 holders progress
   bar (name / 持股数 / 本期变动 / 占比), each row clickable to a drill-down
   drawer.
2. **持 股 变 化** — Top-5 holders dual-axis multi-line chart (solid 持股数
   + dashed 占比, 5-year window) + institutional dual-axis chart with
   hover tooltip (30 quarters).
3. **增持榜 / 减持榜** — two side-by-side ranked lists of latest-period
   position changes (top 5 per side, 前 50 合计 totals).
4. **Single-holder drill-down drawer** — opens on row click, fetches the
   holder's full cross-period history.

The panel is collapsible via a shared `<CollapsibleHeader>` primitive used
across all three stock-detail panels (公司信息 / 主营业务构成 / 股东持仓研究).
A-share pages skip the panel entirely.

## Requirements
### Requirement: HK/US shareholders overview API

The backend MUST expose a `GET /api/stock/shareholders-futu/overview?symbol=<hk-or-us>` endpoint that returns Futu `get_shareholders_overview` (proto 3237) data for a given HK or US symbol, normalized into a consistent shape with three sub-tables (`main_holder`, `holder_type`, `holding_period`).

The endpoint MUST dispatch by symbol:
- Symbols matching `/^HK\.\d{4,5}$/` or `/^\d{4,5}$/` → HK path via `HKStockService.get_shareholders_overview`.
- Symbols matching `/^US\.[A-Z]{1,5}$/` or `/^[A-Z]{1,5}$/` → US path via `USStockService.get_shareholders_overview`.
- All other inputs (including 6-digit A-share codes) → HTTP 400 with `{"error": "Unsupported symbol"}`.

The response envelope on success MUST be:
```json
{
  "data": {
    "symbol": "00700",
    "code": "HK.00700",
    "market": "HK",
    "main_holder": [
      {"static_date": 1781856206, "static_date_str": "2026-06-19", "name": "Prosus Ventures N.V.", "holder_pct": 23.0871, "holder_id": 337488017}
    ],
    "holder_type": [
      {"static_date": 1781856206, "static_date_str": "2026-06-19", "name": "VC/PE Fund", "holder_pct": 23.17562, "holder_id": null}
    ],
    "holding_period": [
      {"period_text": "2026/Q2", "period_id": 90}
    ],
    "source": "futu",
    "updated_at": "2026-06-19T08:00:00Z"
  },
  "error": null
}
```

The `holder_id` field MUST be a JSON integer when present, and JSON `null` when absent (e.g. the synthetic "Other" row in `main_holder` or every row in `holder_type`).

#### Scenario: HK bare-numeric symbol returns overview payload
- **WHEN** client calls `GET /api/stock/shareholders-futu/overview?symbol=00700`
- **THEN** backend resolves to Futu code `HK.00700`
- **AND** calls `OpenQuoteContext.get_shareholders_overview("HK.00700")`
- **AND** returns `{data: {symbol, code, market, main_holder, holder_type, holding_period, source, updated_at}, error: null}`

#### Scenario: US symbol returns overview payload
- **WHEN** client calls `GET /api/stock/shareholders-futu/overview?symbol=AAPL`
- **THEN** backend returns the same shape with `market: "US"` and `code: "US.AAPL"`

#### Scenario: Synthetic Other row has null holder_id
- **WHEN** Futu returns a `main_holder` row with `NaN` `holder_id` (the synthetic "Other" bucket)
- **THEN** backend serializes that row's `holder_id` as JSON `null`
- **AND** does NOT serialize `NaN` or `Infinity`

#### Scenario: A-share symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/shareholders-futu/overview?symbol=600519`
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`
- **AND** does NOT call Futu

#### Scenario: Invalid symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/shareholders-futu/overview?symbol=BAD-CHAR!` or any string matching none of the regexes
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`
- **AND** does NOT call Futu

#### Scenario: Older OpenD returns clean empty payload
- **WHEN** Futu OpenD is older than 10.7.6708 and returns "Unknown protocol ID" on `get_shareholders_overview`
- **THEN** backend returns 200 with `{data: {symbol, code, market, main_holder: [], holder_type: [], holding_period: [], source: "futu", updated_at: <now>}, error: null}`
- **AND** does NOT leak the raw "Unknown protocol ID" error

#### Scenario: Other Futu upstream error returns clean error envelope
- **WHEN** Futu raises any other exception (network blip, unknown symbol, etc.)
- **THEN** backend returns 200 with `{data: null, error: "获取持股概览失败: <msg capped at 120 chars>"}`
- **AND** does NOT return a 5xx status

#### Scenario: Futu error does not poison cache
- **WHEN** `get_shareholders_overview` raises
- **THEN** backend MUST NOT store an empty/error response in `_company_info_cache`
- **AND** the next request retries the upstream call

### Requirement: HK/US shareholders institutional aggregate API with server-side pagination

The backend MUST expose a `GET /api/stock/shareholders-futu/institutional?symbol=<hk-or-us>&n_periods=30` endpoint that returns Futu `get_shareholders_institutional` (proto 3238) data, paginated **server-side** across `next_key` cursors and merged into a single response.

The response envelope on success MUST be:
```json
{
  "data": {
    "symbol": "00700",
    "code": "HK.00700",
    "market": "HK",
    "periods": [
      {"period_text": "2026/Q2", "institution_quantity": 857, "institution_quantity_change": -4, "holder_quantity": 4206836369, "holder_quantity_change": -660808, "holder_pct": 46.705, "holder_pct_change": 0.078, "update_time_str": "2026-06-19 16:03:26"}
    ],
    "has_more": true,
    "source": "futu",
    "updated_at": "2026-06-19T08:00:00Z"
  },
  "error": null
}
```

`periods[]` MUST be sorted in descending period order (latest first), with a maximum length of `n_periods` (default 30, hard cap 50). `has_more` MUST be `true` if the upstream `next_key` is not `"-1"` and we hit the cap, `false` otherwise.

#### Scenario: HK institutional returns up to 30 periods merged from 3 pages
- **WHEN** client calls `GET /api/stock/shareholders-futu/institutional?symbol=00700&n_periods=30`
- **THEN** backend fires up to 3 `OpenQuoteContext.get_shareholders_institutional("HK.00700", num=10, next_key=...)` calls (one per page)
- **AND** merges the results into a single `periods[]` of up to 30 rows
- **AND** sets `has_more` based on whether the last page returned `next_key == "-1"`
- **AND** returns 200 with the merged payload

#### Scenario: Default n_periods is 30
- **WHEN** client calls `GET /api/stock/shareholders-futu/institutional?symbol=00700` (no `n_periods`)
- **THEN** backend behaves as if `n_periods=30`

#### Scenario: n_periods is capped at 50
- **WHEN** client calls `GET /api/stock/shareholders-futu/institutional?symbol=00700&n_periods=200`
- **THEN** backend caps the request at 50 periods (5 pages max)
- **AND** does NOT raise

#### Scenario: A-share symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/shareholders-futu/institutional?symbol=600519`
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`

#### Scenario: Older OpenD returns empty payload
- **WHEN** Futu OpenD is older than 10.7.6708 and returns "Unknown protocol ID"
- **THEN** backend returns 200 with `{data: {symbol, code, market, periods: [], has_more: false, source, updated_at}, error: null}`

### Requirement: HK/US shareholders holder detail API

The backend MUST expose a `GET /api/stock/shareholders-futu/holder-detail?symbol=<hk-or-us>&holder_id=<int>&period_id=<int>&num=50&next_key=<str>` endpoint that returns Futu `get_shareholders_holder_detail` (proto 3239) data.

The response envelope on success MUST be:
```json
{
  "data": {
    "symbol": "00700",
    "code": "HK.00700",
    "market": "HK",
    "rows": [
      {"period_text": "2026/Q2", "holder_id": 337488017, "name": "Prosus Ventures N.V.", "holder_quantity": 2079512000, "holder_quantity_change": 0, "holder_pct": 23.087, "holder_pct_change": 0.0, "holding_date": 1767110400, "holding_date_str": "2025-12-31", "close_price": 491.3, "price_change_pct": 2.6321, "source_group_name": "Annual Report", "update_time_str": "2026-06-19 00:32:25"}
    ],
    "next_key": "20",
    "has_more": true,
    "source": "futu",
    "updated_at": "2026-06-19T08:00:00Z"
  },
  "error": null
}
```

`next_key` MUST be the Futu SDK's `df.attrs['next_key']` lifted to a top-level field, or `"-1"` when there are no more pages. `has_more` MUST be `next_key != "-1"`. The `holder_id` filter, when provided, MUST scope the result to a single holder's cross-period history (e.g. Prosus's 20 quarters). The `period_id` filter, when provided, MUST scope the result to a single period (the `period_id` is opaque and comes from the overview endpoint's `holding_period[]`).

#### Scenario: HK holder detail top-50 returns first page
- **WHEN** client calls `GET /api/stock/shareholders-futu/holder-detail?symbol=00700&num=50`
- **THEN** backend calls `OpenQuoteContext.get_shareholders_holder_detail("HK.00700", num=50)`
- **AND** returns up to 50 rows
- **AND** `next_key` is the SDK's `df.attrs['next_key']` (e.g. "50")
- **AND** `has_more` is `true` if `next_key != "-1"`

#### Scenario: holder_id filter returns single holder's history
- **WHEN** client calls `GET /api/stock/shareholders-futu/holder-detail?symbol=00700&holder_id=337488017`
- **THEN** backend calls `OpenQuoteContext.get_shareholders_holder_detail("HK.00700", holder_id=337488017)`
- **AND** returns that holder's cross-period history (e.g. Prosus's 20 quarters)
- **AND** `has_more` reflects whether more periods are available

#### Scenario: period_id filter returns single period's data
- **WHEN** client calls `GET /api/stock/shareholders-futu/holder-detail?symbol=00700&period_id=90` (the period_id of "2026/Q2")
- **THEN** backend calls `OpenQuoteContext.get_shareholders_holder_detail("HK.00700", period_id=90)`
- **AND** returns rows for that single period

#### Scenario: next_key paginates the result
- **WHEN** client calls `GET /api/stock/shareholders-futu/holder-detail?symbol=00700&next_key=20`
- **THEN** backend forwards `next_key=20` to the SDK
- **AND** returns the next 50 rows starting at offset 20

#### Scenario: A-share symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/shareholders-futu/holder-detail?symbol=600519`
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`

#### Scenario: Older OpenD returns empty payload
- **WHEN** Futu OpenD is older than 10.7.6708 and returns "Unknown protocol ID"
- **THEN** backend returns 200 with `{data: {symbol, code, market, rows: [], next_key: "-1", has_more: false, source, updated_at}, error: null}`

### Requirement: HK/US shareholders holding changes API

The backend MUST expose a `GET /api/stock/shareholders-futu/holding-changes?symbol=<hk-or-us>&filter_type=<int>&num=50&next_key=<str>` endpoint that returns Futu `get_shareholders_holding_changes` data, filtered by `filter_type`.

The `filter_type` parameter MUST map as follows:
- `1` → increases (增持) — top changes where `share_change_num` is positive.
- `2` → decreases (减持) — top changes where `share_change_num` is negative.
- `0` or omitted → default to `1` (increases).

The response envelope on success MUST be:
```json
{
  "data": {
    "symbol": "00700",
    "code": "HK.00700",
    "market": "HK",
    "rows": [
      {"period_text": "2026/Q2", "name": "CSOP Asset Management Limited", "holder_id": 112337755, "share_change_num": 3603631, "shares_change_price": 1605057247, "share_ratio": 0.194, "holder_type": "Mutual Fund", "holder_type_id": 2, "holding_date": 1779984000, "holding_date_str": "2026-05-29", "share_ratio_change": 0.040, "share_num": 17522551}
    ],
    "next_key": "20",
    "has_more": true,
    "source": "futu",
    "updated_at": "2026-06-19T08:00:00Z"
  },
  "error": null
}
```

The Futu SDK does NOT accept a `holder_id` parameter on `get_shareholders_holding_changes`. The endpoint MUST NOT accept `holder_id` either; per-holder reduction history (e.g. "show me Prosus's reductions") is served by `get_shareholders_holder_detail?holder_id=...` instead. This is documented in the OpenAPI spec via a comment on the route.

#### Scenario: filter_type=1 returns latest-period increases
- **WHEN** client calls `GET /api/stock/shareholders-futu/holding-changes?symbol=00700&filter_type=1`
- **THEN** backend calls `OpenQuoteContext.get_shareholders_holding_changes("HK.00700", filter_type=1)`
- **AND** returns rows sorted by `share_change_num` descending

#### Scenario: filter_type=2 returns latest-period decreases
- **WHEN** client calls `GET /api/stock/shareholders-futu/holding-changes?symbol=00700&filter_type=2`
- **THEN** backend returns rows sorted by `share_change_num` ascending (most negative first)

#### Scenario: holder_id query is rejected
- **WHEN** client calls `GET /api/stock/shareholders-futu/holding-changes?symbol=00700&holder_id=337488017`
- **THEN** backend ignores the `holder_id` parameter (does NOT pass it to Futu)
- **AND** returns the unfiltered default `filter_type=1` list
- **AND** documents this behavior in the route docstring

#### Scenario: A-share symbol returns HTTP 400
- **WHEN** client calls `GET /api/stock/shareholders-futu/holding-changes?symbol=600519`
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}`

#### Scenario: Older OpenD returns empty payload
- **WHEN** Futu OpenD is older than 10.7.6708 and returns "Unknown protocol ID"
- **THEN** backend returns 200 with `{data: {symbol, code, market, rows: [], next_key: "-1", has_more: false, source, updated_at}, error: null}`

### Requirement: HK/US shareholder data is cached

The backend MUST cache all four shareholder responses to avoid burning Futu OpenD capacity on repeat calls. The cache MUST be the existing `_company_info_cache` (24h TTL). Cache keys MUST be scoped by query-signature so distinct calls do not collide.

- `shareholders_overview:{symbol}` — overview payload (no further signature).
- `shareholders_institutional:{symbol}:{n_periods}` — institutional aggregate.
- `shareholders_holder_detail:{symbol}:{holder_id or 'all'}:{period_id or 'latest'}:{next_key or '0'}` — holder detail (4-part signature).
- `shareholders_holding_changes:{symbol}:{filter_type}:{next_key or '0'}` — holding changes (3-part signature).

#### Scenario: Cache hit does not call Futu
- **WHEN** the same key is requested within 24h
- **THEN** backend returns the cached payload without calling Futu

#### Scenario: Cache miss calls Futu and stores result
- **WHEN** the cache key has no entry or entry is older than 24h
- **THEN** backend calls Futu, stores the normalized payload in the cache
- **AND** subsequent calls within 24h return the cached value

#### Scenario: Distinct signatures do not collide
- **WHEN** `shareholders_holder_detail:00700:all:latest:0` and `shareholders_holder_detail:00700:337488017:latest:0` are both requested
- **THEN** backend caches and returns them as two independent entries

#### Scenario: Futu error does not poison cache
- **WHEN** the upstream Futu call fails (any of the four endpoints)
- **THEN** backend MUST NOT store an empty/error response in the cache
- **AND** the next request retries the upstream call

### Requirement: HK and US stock detail pages render shareholders panel

For symbols matching the HK regex (`/^\d{4,5}$/` or `/^HK\.\d{4,5}$/`) or US regex (`/^[A-Z]{1,5}$/` or `/^US\.[A-Z]{1,5}$/`), the stock detail page MUST render the `<ShareholdersPanel />` component directly below the existing `<MainBusinessPanel />`. The component MUST receive a `market` prop set to `"HK"` or `"US"`. For A-share symbols (6 digits), the component MUST NOT be rendered and no fetches MUST be fired.

The panel header MUST render `❖ 股 东 持 仓 研 究` (with the `❖` decorative marker) and MUST be collapsible via the shared `<CollapsibleHeader>` primitive (`−` when open, `+` when collapsed). Default state is open.

#### Scenario: HK page renders the panel with HK data
- **WHEN** user navigates to `/stock/00700`
- **THEN** page fires ~9 parallel fetches on mount:
  - 1 × `GET /api/stock/shareholders-futu/overview?symbol=00700`
  - 5 × `GET /api/stock/shareholders-futu/holder-detail?holder_id=<top5>` (one per top-5 holder, used for the 持股变化 chart's per-holder trend lines)
  - 1 × `GET /api/stock/shareholders-futu/institutional?symbol=00700`
  - 2 × `GET /api/stock/shareholders-futu/holding-changes?filter_type=1|2`
- **AND** renders `<ShareholdersPanel market="HK" symbol="00700" />` below `<MainBusinessPanel />`
- **AND** the panel renders a single vertical Overview (no tab navigation), with sub-sections stacked top-to-bottom

#### Scenario: US page renders the panel with US data
- **WHEN** user navigates to `/stock/AAPL`
- **THEN** page fires the same ~9 parallel fetches with `symbol=AAPL`
- **AND** renders `<ShareholdersPanel market="US" symbol="AAPL" />`

#### Scenario: A-share page is unaffected
- **WHEN** user navigates to `/stock/600519`
- **THEN** page does NOT render `<ShareholdersPanel />`
- **AND** does NOT call any of the 4 `/api/stock/shareholders-futu/*` endpoints
- **AND** the existing `<MainBusinessPanel />` A-share path is unchanged

#### Scenario: Each sub-section renders its own skeleton during fetch
- **WHEN** any sub-section's data is still loading
- **THEN** that sub-section renders a vintage-style skeleton (matching the existing `<MainBusinessPanel />` skeleton style)
- **AND** already-loaded sub-sections render their content independently

#### Scenario: Sub-section renders empty state on no data
- **WHEN** any sub-section receives `{data: null, ...}` or empty arrays
- **THEN** that sub-section renders a "暂无持股数据" placeholder (matching the existing `<MainBusinessPanel />` empty-state style)
- **AND** does NOT throw

### Requirement: Panel renders a single Overview view (no tabs)

The `<ShareholdersPanel />` MUST render a single vertical flow with no tab navigation. Sub-sections, top-to-bottom:

1. **股东概览** (`SectionHeader`, full width) — two side-by-side cards on `lg`, stacked on `sm`:
   - 股 东 类 型 分 布 card — donut chart + top-6 legend, latest snapshot.
   - top5 股 东 分 析 card — progress-bar list (name, 持股数, 本期变动, 占比, progress fill); each row clickable.
2. **持 股 变 化** (`SectionHeader`, full width) — two stacked cards:
   - top5 股 东 持 股 变 化 card — multi-line dual-axis chart (left axis = 持股数 亿股, right axis = 占比 %), 5-year window (last 20 quarters).
   - 机 构 持 股 变 化 card — dual-axis chart (bars = institution_quantity, line = holder_pct) over 30 quarters; hover tooltip on bar OR line dot shows period / 家数 / 占比.
3. **Two-column 增持榜 / 减持榜** (no outer title, no card wrapper) — each column is its own bordered card showing top 5 + 前 50 合计.

The holder-type donut card and the institutional chart card have inner sub-titles (`股 东 类 型 分 布` / `机 构 持 股 变 化`) inside their bordered cards.

#### Scenario: 股东概览 card renders donut + top-5 progress bar
- **WHEN** the panel mounts with valid overview data
- **THEN** the donut chart displays one slice per `holder_type` row, sized by `holder_pct`, sorted descending, with a top-6 legend on the right
- **AND** the progress-bar list displays the top 5 holders by `holder_pct` descending (excluding the synthetic "Other" row whose `holder_id === null`)
- **AND** each progress row shows: name (left, colored left border matching the trend chart color), 持股数 (亿股, from holder_detail trend cache), 本期变动 (▲/▼ + %, from API), 占比 (right), with a colored progress bar fill below

#### Scenario: Top-5 progress row click opens drill-down drawer
- **WHEN** user clicks a progress row in the top5 list
- **THEN** an in-panel slide-in drawer opens from the right (480px wide)
- **AND** the drawer fetches `getShareholdersHolderDetail(symbol, {holder_id: row.holder_id, num: 50})` (cache hit; the trend chart already populated this key)
- **AND** the drawer shows a cross-period line chart of `holder_pct` over time
- **AND** the drawer's history table shows period_text / 持股数 / 占比 / 本期变动, where 本期变动 is computed locally as `current - previous` (the API's `holder_pct_change` returns 0 for older rows even when 占比 visibly shifts due to dilution)

#### Scenario: 持 股 变 化 card renders dual-axis multi-line chart
- **WHEN** the panel mounts with trend data
- **THEN** the top5 chart shows one polyline per top-5 holder, last 20 quarters (5-year window)
- **AND** each holder has TWO lines in the same color: solid = 持股数 (left axis, 亿股 units), dashed = 占比 (right axis, % units)
- **AND** the legend shows: line-style key (持 ┄┄ 占) + per-holder latest 持股数 + 占比

#### Scenario: 持 股 变 化 card renders dual-axis institutional chart
- **WHEN** the panel mounts with institutional data
- **THEN** the institutional chart shows bars (institution_quantity, right axis) + a line (holder_pct, left axis) over 30 quarters
- **AND** hovering either a bar OR a line dot reveals a floating tooltip showing period_text / institution_quantity / holder_pct at that period
- **AND** a dashed vertical guideline + hollow ring marks the 5-periods-ago reference point (anchors the 较 5 期 前 metric strip cell)
- **AND** the metric strip below shows: 机构数, 持股数 (亿 HKD/USD), 机构占比 (highlighted), 较 5 期 前 (latest - 5-periods-ago delta, sign + tone), 数据时间

#### Scenario: 增持榜 / 减持榜 columns render
- **WHEN** the panel mounts with both holding-changes fetches complete
- **THEN** two columns render side-by-side on `lg`, stacked on `sm`
- **AND** left column = 增持榜 (filter_type=1, increases) showing top 5 rows sorted by `share_change_num` desc
- **AND** right column = 减持榜 (filter_type=2, decreases) showing top 5 rows sorted by `share_change_num` asc
- **AND** each column header shows the reporting period (e.g. `2026/Q2`)
- **AND** each column shows a 前 50 合计 cell at the top (sum of positive values for 增持, sum of negative values for 减持, signed and tone-colored)

### Requirement: Currency and unit normalization for HK/US

All monetary / share-quantity values in the panel MUST be rendered in a human-friendly unit (亿股 or 万) with the appropriate currency suffix.

#### Scenario: holder_quantity is divided by 1e8 for 亿股 display
- **WHEN** the panel renders a `holder_quantity` value (in the top-5 progress bar, drill-down table, institutional trend chart, or institutional metric strip)
- **THEN** the value is divided by `1e8` and displayed with the suffix `亿股` (or `万股` for values < 1e7)

#### Scenario: holder_quantity is divided by 1e8 for 亿HKD / 亿美元 display
- **WHEN** the panel renders a `holder_quantity` value via `formatYiSharesWithCurrency`
- **THEN** the value is divided by `1e8` and displayed with the suffix `亿HKD` (HK) or `亿美元` (US)

#### Scenario: share_change_num is formatted with 万 / 亿 suffix
- **WHEN** the panel renders a `share_change_num` value (in 增持榜 / 减持榜)
- **THEN** if `|share_change_num| >= 1e8` it is divided by `1e8` and displayed with the suffix `亿股`
- **AND** if `1e4 <= |share_change_num| < 1e8` it is divided by `1e4` and displayed with the suffix `万股`
- **AND** if `|share_change_num| < 1e4` the raw integer is displayed
- **AND** the sign is preserved (`+` for positive, `-` for negative)

### Requirement: 较 5 期 前 computes latest minus 5 quarters ago

The institutional card's 较 5 期 前 metric MUST compute the delta between the latest period's `holder_pct` and the period 5 quarters before. The Futu backend returns periods in descending order, so `data.periods[0]` = latest and `data.periods[5]` = 5 quarters back.

#### Scenario: 5 quarters ago available
- **WHEN** the institutional response has ≥ 6 periods
- **THEN** 较 5 期 前 shows `latest.holder_pct - periods[5].holder_pct`, formatted with sign (`+0.12%` or `-0.25%`) and tone-colored (red for `≥ 0`, green for `< 0`)

#### Scenario: fewer than 6 periods available
- **WHEN** the institutional response has < 6 periods (e.g. newly-listed stock or older OpenD)
- **THEN** 较 5 期 前 shows `—` (NA)

### Requirement: A-share pages do not render the panel

The `<ShareholdersPanel />` MUST NOT be rendered on A-share pages, and no `/api/stock/shareholders-futu/*` fetches MUST be fired.

#### Scenario: A-share page has no ShareholdersPanel
- **WHEN** user navigates to `/stock/600519`
- **THEN** the page does NOT contain `<ShareholdersPanel />` in the React tree
- **AND** the network panel shows zero calls to `/api/stock/shareholders-futu/*`
- **AND** the existing `<MainBusinessPanel />` A-share path is unchanged

### Requirement: All three stock-detail panels share a collapsible header

The three stock-detail panels (公司信息, 主营业务构成, 股东持仓研究) MUST use the shared `<CollapsibleHeader>` primitive. The header MUST:
- Render the `❖` decorative marker (default glyph, configurable via prop)
- Render the title using the `font-playfair text-base sm:text-lg tracking-[0.16em] text-vt-parchment uppercase` style
- Be clickable anywhere on the header row to toggle the panel's `open` state
- Render `−` when open, `+` when collapsed (in the top-right corner, no rotation animation)
- Have default state `open = true`
- Support an optional `rightSlot` for sub-titles / captions

#### Scenario: Clicking the header toggles the panel
- **WHEN** user clicks the header row
- **THEN** the panel content area collapses (when open) or expands (when collapsed)
- **AND** the toggle icon swaps `−` ↔ `+`
- **AND** the rest of the page is unaffected

#### Scenario: Independent collapse state per panel
- **WHEN** user collapses one panel (e.g. 公司信息)
- **THEN** the other two panels (主营业务构成, 股东持仓研究) remain in their previous state
- **AND** collapse state is local to each panel — no global state coordination needed

### Requirement: Futu OpenD v10.7.6708+ required

The panel fetches `get_shareholders_overview` (proto 3237), `get_shareholders_institutional` (proto 3238), `get_shareholders_holder_detail` (proto 3239), and `get_shareholders_holding_changes` (the holding_changes variant). All four protos require Futu OpenD v10.7.6708 or newer.

#### Scenario: Older OpenD returns clean empty payload
- **WHEN** Futu OpenD < v10.7.6708 returns "Unknown protocol ID" on any of the four endpoints
- **THEN** the backend returns 200 with `{data: <empty>, error: null}` (clean empty payload, never leaks the raw protocol error)
- **AND** the frontend renders "暂无持股数据" placeholder for that sub-section
