## ADDED Requirements

### Requirement: Dragon Tiger List displays in Guest View
The system SHALL display an "机构龙虎榜" section below the "热门股" section in the Guest View homepage for unauthenticated users.

#### Scenario: Guest views Dragon Tiger List section
- **WHEN** guest user visits homepage
- **THEN** "机构龙虎榜" section appears below "热门股" section
- **AND** section contains two tabs: "净买入" and "净卖出"

### Requirement: Net Buy tab shows top 5 stocks by cumulative net amount
The system SHALL display the top 5 A-share stocks with highest cumulative positive net buy amount in the "净买入" tab.

#### Scenario: Net buy data is available
- **WHEN** "净买入" tab is selected
- **THEN** system displays up to 5 stocks ranked by cumulative net_amount (summed across N trading days) in descending order
- **AND** each row shows: 日期, 代码, 名称(上榜次数), 收盘价, 涨幅, 净买入额, 上榜原因

#### Scenario: Net buy data is empty
- **WHEN** "净买入" tab is selected and no data is available
- **THEN** system displays "暂无数据" placeholder

### Requirement: Net Sell tab shows top 5 stocks by cumulative net sell amount
The system SHALL display the top 5 A-share stocks with highest cumulative net sell amount (shown as absolute value) in the "净卖出" tab.

#### Scenario: Net sell data is available
- **WHEN** "净卖出" tab is selected
- **THEN** system displays up to 5 stocks ranked by cumulative net_amount (summed across N trading days) in ascending order (most negative first)
- **AND** each row shows: 日期, 代码, 名称(上榜次数), 收盘价, 涨幅, 净卖出额 (displayed as positive/absolute value), 上榜原因

#### Scenario: Net sell data is empty
- **WHEN** "净卖出" tab is selected and no data is available
- **THEN** system displays "暂无数据" placeholder

### Requirement: Tab switching preserves selected market tab state
The system SHALL NOT reset the "热门股" market tab when switching between Dragon Tiger List tabs.

#### Scenario: Switch between Dragon Tiger List tabs
- **WHEN** user is on "净买入" tab of Dragon Tiger List
- **AND** switches to "净卖出" tab
- **THEN** "热门股" section maintains its current market tab selection

### Requirement: Backend API returns Dragon Tiger List data with cumulative aggregation
The system SHALL provide a `GET /api/stock/dragon-tiger-list` endpoint that returns aggregated Dragon Tiger List data.

#### Scenario: API returns valid data
- **WHEN** client requests `GET /api/stock/dragon-tiger-list?days=3`
- **THEN** API aggregates top_list data from last 3 trading days
- **AND** for each stock, sums net_amount across all days to get cumulative net amount
- **AND** returns `net_buy` array (top 5 by cumulative net_amount descending) and `net_sell` array (top 5 by cumulative net_amount ascending)
- **AND** each entry contains: trade_date (latest date), ts_code, name, close (latest), pct_change (latest), net_amount (cumulative sum), reason (latest), appear_count (number of days appeared)

#### Scenario: API handles empty data
- **WHEN** no Dragon Tiger List data exists for the period
- **THEN** API returns `net_buy: []` and `net_sell: []` with `error: null`

### Requirement: Data unit formatting for display
The system SHALL format net_amount in units of 亿元 (100 million yuan) with appropriate sign prefix.

#### Scenario: Display net buy amount
- **WHEN** displaying net_buy data with net_amount = 2042078343.49 (in 元)
- **THEN** display shows "+20.42亿"

#### Scenario: Display net sell amount
- **WHEN** displaying net_sell data with net_amount = -1500000000.00 (in 元)
- **THEN** display shows "-15.00亿"

### Requirement: Dragon Tiger List is independent of Hot Stocks
The system SHALL ensure Dragon Tiger List stocks do NOT affect the Hot Stocks (热门股) section or its AI analysis queue.

#### Scenario: Dragon Tiger List stocks do not appear in Hot Stocks
- **WHEN** Dragon Tiger List displays stock X
- **THEN** stock X is NOT automatically added to the Hot Stocks preset list
- **AND** stock X does NOT appear in ASharePresetList

#### Scenario: Dragon Tiger List stocks do not trigger AI analysis
- **WHEN** Dragon Tiger List fetches or displays stock data
- **THEN** no trend prediction (AI analysis) is triggered for those stocks
- **AND** Dragon Tiger List data retrieval does NOT interact with the trend prediction service

#### Scenario: Hot Stocks AI analysis queue unchanged
- **WHEN** Dragon Tiger List feature is active
- **THEN** Hot Stocks preset stocks continue to be analyzed for trend predictions
- **AND** Dragon Tiger List data fetching has no side effect on the analysis queue
