## MODIFIED Requirements

### Requirement: Analysis module shows index metrics sub-tab
The "投资分析" module SHALL display an additional "指数指标" sub-tab option.

#### Scenario: Index metrics tab appears in analysis module
- **WHEN** "投资分析" module is selected
- **THEN** the sub-module tabs show "资金流向", "机构龙虎榜", and "指数指标" options

#### Scenario: Index metrics tab not visible in watchlist module
- **WHEN** "我的自选" module is selected
- **THEN** "指数指标" tab is NOT displayed

## ADDED Requirements

### Requirement: Index metrics sub-module displays in analysis tab
The system SHALL display an "指数指标" sub-module tab in the Investment Analysis section.

#### Scenario: Display index metrics tab
- **WHEN** user selects "投资分析" module
- **THEN** "指数指标" tab appears alongside "资金流向" and "机构龙虎榜" tabs
- **AND** "指数指标" tab is NOT visible when "我的自选" module is selected

### Requirement: Index list displays six major A-share indices
The system SHALL display six major A-share indices in the order specified.

#### Scenario: Index list order
- **WHEN** user views the index metrics panel
- **THEN** indices are displayed in this order:
  1. 科创50 (000688.SH)
  2. 创业板指 (399006.SZ)
  3. 上证指数 (000001.SH)
  4. 深证成指 (399001.SZ)
  5. 沪深300 (000300.SH)
  6. 中证500 (000905.SH)

### Requirement: Each index card shows PE-TTM metrics
Each index card SHALL display the following metrics:

| Metric | Description |
|--------|-------------|
| 当前PE_TTM | Current trailing twelve months P/E ratio |
| 机会值 | 30th percentile PE-TTM (low valuation threshold) |
| 危险值 | 70th percentile PE-TTM (high valuation threshold) |
| 当前百分位 | Current PE-TTM percentile in historical data |
| 历史最高 | Historical maximum PE-TTM |
| 历史最低 | Historical minimum PE-TTM |

#### Scenario: Index card displays all metrics
- **WHEN** index metrics data is loaded
- **THEN** the card shows current PE_TTM, opportunity value, danger value, current percentile, historical high, and historical low

#### Scenario: Index card shows loading state
- **WHEN** index metrics data is being fetched
- **THEN** a loading indicator is displayed
- **AND** metric fields show placeholder values

#### Scenario: Index card shows error state
- **WHEN** index metrics fetch fails
- **THEN** an error message is displayed
- **AND** a retry button is available

### Requirement: Time range selection per index
Each index card SHALL have a time range selector allowing 5-year or 10-year periods.

#### Scenario: Change time range to 5 years
- **WHEN** user selects "5年" from dropdown
- **THEN** index card refreshes with 5-year historical data
- **AND** opportunity/danger values recalculate based on 5-year data

#### Scenario: Change time range to 10 years
- **WHEN** user selects "10年" from dropdown
- **THEN** index card refreshes with 10-year historical data
- **AND** opportunity/danger values recalculate based on 10-year data

### Requirement: Individual index refresh
Each index card SHALL have an independent refresh mechanism.

#### Scenario: Refresh single index
- **WHEN** user clicks refresh button on an index card
- **THEN** only that index's data is refreshed
- **AND** other index cards remain unchanged

### Requirement: Daily cache with expiration
Index metrics SHALL be cached with daily expiration.

#### Scenario: Cache hit within same day
- **WHEN** user views index metrics for a date that was already queried today
- **THEN** cached data is returned immediately
- **AND** no API call is made

#### Scenario: Cache miss next day
- **WHEN** user views index metrics on a new day after previous query
- **THEN** fresh data is fetched from API
- **AND** new cache entry is created

### Requirement: Valuation status indicator
Each index card SHALL visually indicate the current valuation status.

#### Scenario: Low valuation (below 30th percentile)
- **WHEN** current percentile is below 30%
- **THEN** card shows green "低估" indicator

#### Scenario: Normal valuation (30% - 70%)
- **WHEN** current percentile is between 30% and 70%
- **THEN** card shows yellow "正常" indicator

#### Scenario: High valuation (above 70th percentile)
- **WHEN** current percentile is above 70%
- **THEN** card shows red "高估" indicator

## ADDED Requirements (Industry Index)

### Requirement: Industry index selection dropdown
The system SHALL provide a dropdown to select from 28 申万一级行业 indices.

#### Scenario: Industry dropdown displays all industries
- **WHEN** user views the industry metrics panel
- **THEN** dropdown shows all 28 申万一级行业 options
- **AND** "有色金属" is selected by default

#### Scenario: Select different industry
- **WHEN** user selects a different industry from dropdown
- **THEN** metrics and chart update to show selected industry's data
- **AND** "有色金属" remains selected on subsequent visits

### Requirement: Industry selector mobile layout
The industry selector SHALL display as a stacked two-row layout on mobile and inline single-row layout on desktop.

#### Scenario: Mobile displays selectors stacked
- **WHEN** user views industry metrics on a screen narrower than 640px
- **THEN** the Level-1 selector (一级行业) occupies one full row with its label
- **AND** the Level-2 selector (二级行业) occupies a second full row with its label
- **AND** the 估值状态 badge sits inline with the Level-2 selector

#### Scenario: Desktop displays selectors inline
- **WHEN** user views industry metrics on a screen 640px or wider
- **THEN** the Level-1 and Level-2 selectors appear on a single row side by side

### Requirement: Section header titles and visual hierarchy
The index metrics panel SHALL display two section headers with distinct visual prominence.

#### Scenario: Section header text content
- **WHEN** user views the index metrics panel
- **THEN** the first section header displays "行业估值 · PE 百分位"
- **AND** the second section header displays "热门指数估值 · PE 百分位"

#### Scenario: Section headers are visually subdued
- **WHEN** user views the section headers
- **THEN** headers use vt-engraved parchment serif styling (not the bold brass-emboss used by top-level tabs)
- **AND** headers display at text-[13px] on mobile and text-sm on desktop
- **AND** each header has a subtle 1px brass hairline underline accent
Selected industry SHALL display PE metrics similar to broad indices.

#### Scenario: Industry displays same metrics as index
- **WHEN** industry is selected
- **THEN** metrics grid shows current PE, percentile, opportunity, danger, historical high/low
- **AND** chart displays PE trend with opportunity/danger lines

### Requirement: Industry list from API
The system SHALL fetch industry list from `/api/index/industry/list` endpoint.

#### Scenario: Industry list loaded on mount
- **WHEN** IndexMetricsPanel loads
- **THEN** industry list is fetched from `/api/index/industry/list`
- **AND** first industry is auto-selected

### Requirement: Industry supports time range selection
Industry panel SHALL support 5-year and 10-year time range like broad indices.

#### Scenario: Change industry time range
- **WHEN** user selects different time range for industry
- **THEN** industry metrics and chart refresh with new time range
