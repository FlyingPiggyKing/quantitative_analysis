## ADDED Requirements

### Requirement: Display top inflow companies on sector selection

When a sector is selected in the money-flow Sankey chart, the system SHALL display, in a panel directly below the "已选中" block, the top N companies by main-force net inflow for each trading day that sector appears in the chart.

#### Scenario: Sector selected shows per-date company rankings

- **WHEN** the user selects a sector (e.g. 白酒) by clicking its flow line or legend entry, and that sector appears in the chart on 2026-05-29 and 2026-05-27
- **THEN** a panel appears below the "已选中: 白酒" block
- **AND** the panel shows one group per date (newest first): 2026-05-29 and 2026-05-27
- **AND** each group lists up to 5 companies ranked by main-force net inflow descending, showing company name, stock code, PE(TTM), market cap (市值), and net inflow in 亿元
- **AND** on mobile, company name appears above its code on a second line
- **AND** market cap is displayed as 万亿 for values ≥10000亿 (e.g. 1.29万亿), else as 亿元

#### Scenario: Deselecting hides the panel

- **WHEN** the user clicks the selected sector again or clicks empty chart area to clear the selection
- **THEN** the panel is removed and no company rankings are shown

#### Scenario: Selecting a different sector refreshes the panel

- **WHEN** a panel is shown for one sector and the user selects a different sector
- **THEN** the panel updates to show the newly selected sector's per-date company rankings

#### Scenario: Loading state while fetching

- **WHEN** the panel is fetching company rankings for a newly selected sector
- **THEN** the panel shows a loading indicator until data arrives or an error occurs

### Requirement: Sector-top-stocks API endpoint

The system SHALL provide `GET /api/stock/sector-top-stocks` that, given a sector name, a set of trade dates, and an optional `top_n`, returns the top companies by main-force net inflow per date.

#### Scenario: Returns ranked companies per requested date

- **WHEN** a request is made with `sector=白酒&dates=2026-05-29,2026-05-27&top_n=5`
- **THEN** the response includes `by_date` keyed by each requested date that has data
- **AND** each date maps to a list of up to 5 objects with `ts_code`, `name`, `net_inflow` (in 亿元), `pe_ttm`, and `total_mv_yi` (市值 in 亿元, divide by 1e4 to get 万亿 for ≥10000亿)
- **AND** each date's list is sorted by `net_inflow` descending
- **AND** the response includes the resolved SW2021 `index_code` and `matched_name`

#### Scenario: top_n defaults to 5 and is bounded

- **WHEN** a request omits `top_n`
- **THEN** the system returns at most 5 companies per date
- **AND** when `top_n` is provided it is constrained to a sane range (1–20)

### Requirement: Resolve chart sector name to SW2021 industry members

The system SHALL resolve the chart's sector name (东方财富/DC classification) to an SW2021 industry index code and its member stocks, tolerating roman-numeral variants and naming differences between the two taxonomies.

#### Scenario: Exact name resolves to SW2021 index

- **WHEN** the sector name matches an SW2021 industry name after normalization (trimming whitespace and trailing roman-numeral variants such as Ⅱ/Ⅲ)
- **THEN** the system uses that industry's `index_code` and fetches its member `ts_code` list via `index_member`

#### Scenario: No SW2021 match returns a graceful error

- **WHEN** the sector name cannot be matched to any SW2021 industry
- **THEN** the response has an empty `by_date` and a non-null `error` message indicating no industry match
- **AND** the panel displays a "无法匹配到申万行业成分股" message instead of company rows

### Requirement: Rank companies by main-force net inflow

The system SHALL rank member companies for each date by main-force net inflow, computed from the per-stock `moneyflow` data.

#### Scenario: Net inflow computed from 特大单 and 大单

- **WHEN** computing a company's net inflow for a date
- **THEN** net inflow equals `(buy_elg_amount - sell_elg_amount) + (buy_lg_amount - sell_lg_amount)`
- **AND** the value is converted from 万元 to 亿元 by dividing by 10000 for display

#### Scenario: Only industry members are considered

- **WHEN** ranking companies for a date
- **THEN** only stocks that are members of the resolved SW2021 industry are included
- **AND** non-member A-shares from the day's money-flow table are excluded

### Requirement: Cache money-flow and classification lookups

The system SHALL cache classification, member, company-name, and per-date money-flow lookups to stay within Tushare rate limits.

#### Scenario: Per-date money-flow reused across sectors

- **WHEN** the day's `moneyflow` table for a given trade date has already been fetched
- **THEN** subsequent requests for any sector on that date reuse the cached table instead of calling Tushare again

#### Scenario: Tushare permission or rate-limit error degrades gracefully

- **WHEN** the per-stock `moneyflow` call fails due to missing permission or rate limiting
- **THEN** the response returns a non-null `error` message and an empty `by_date`
- **AND** the panel surfaces the error instead of crashing or showing stale data
