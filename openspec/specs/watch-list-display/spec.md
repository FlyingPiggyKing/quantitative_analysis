# watch-list-display Specification

## Purpose
TBD - created by archiving change pe-thumbnail-on-watch-list. Update Purpose after archive.
## Requirements
### Requirement: WatchList 表格列布局
WatchList 表格 SHALL 包含以下列（从左到右）：股票代码、股票名称、PE趋势迷你图、市盈率(PE)、市净率(PB)、趋势预测。

#### Scenario: 默认列展示
- **WHEN** 用户访问首页 WatchList 区域
- **THEN** 表格显示：股票代码 | 股票名称 | PE趋势 | 市盈率(PE) | 市净率(PB) | 趋势预测，不包含"添加日期"列


## ADDED Requirements

### Requirement: Market type in watchlist storage
The system SHALL store market type ("A" for A-share, "US" for US stocks, "HK" for HK stocks) with each watchlist entry.

#### Scenario: Add A-share stock to watchlist
- **WHEN** user adds A-share stock (e.g., "600938") to watchlist
- **THEN** watchlist entry is created with symbol="600938", name="中海油服", market="A"

#### Scenario: Add US stock to watchlist
- **WHEN** user adds US stock (e.g., "GOOGL") to watchlist
- **THEN** watchlist entry is created with symbol="GOOGL", name="Google", market="US"

#### Scenario: Add HK stock to watchlist
- **WHEN** user adds HK stock (e.g., "00700") to watchlist
- **THEN** watchlist entry is created with symbol="00700", name="TENCENT", market="HK"

#### Scenario: Legacy watchlist entries have null market
- **WHEN** querying watchlist entries created before this change
- **THEN** market field is null, treated as "A" for backward compatibility

### Requirement: Watchlist display filters by market tab
The system SHALL filter watchlist display based on selected market tab.

#### Scenario: Display A-share stocks when A股 tab selected
- **WHEN** "A股" tab is selected
- **THEN** show only stocks where market="A" OR market IS NULL

#### Scenario: Display HK stocks when 港股 tab selected
- **WHEN** "港股" tab is selected
- **THEN** show only stocks where market="HK"

#### Scenario: Display US stocks when 美股 tab selected
- **WHEN** "美股" tab is selected
- **THEN** show only stocks where market="US"

### Requirement: Independent A-share valuation data loading
The system SHALL fetch A-share valuation data independently without waiting for US stock data to load.

#### Scenario: A-share valuation loads before US valuation
- **WHEN** user views WatchList with A-share and US stocks
- **AND** A-share stocks are already in the watchlist
- **AND** A-share valuation data arrives
- **AND** US stock data is still loading or fails
- **THEN** system displays A-share valuation data immediately
- **AND** US stock section shows loading indicator or error state independently

#### Scenario: A-share valuation loads after US valuation
- **WHEN** user views WatchList with A-share and US stocks
- **AND** US stock valuation data arrives first
- **AND** A-share valuation data arrives later
- **THEN** system displays US stock valuation data first
- **AND** system displays A-share valuation data when it arrives

### Requirement: Independent US stock valuation data loading
The system SHALL fetch US stock valuation data independently without waiting for A-share data to load.

#### Scenario: US valuation loads before A-share valuation
- **WHEN** user views WatchList with A-share and US stocks
- **AND** US stocks are already in the watchlist
- **AND** US stock valuation data arrives
- **AND** A-share stock data is still loading or fails
- **THEN** system displays US stock valuation data immediately
- **AND** A-share section shows loading indicator or error state independently

#### Scenario: US valuation loads after A-share valuation
- **WHEN** user views WatchList with A-share and US stocks
- **AND** A-share valuation data arrives first
- **AND** US stock valuation data arrives later
- **THEN** system displays A-share valuation data first
- **AND** system displays US stock valuation data when it arrives

### Requirement: A-share valuation unaffected by US stock failure
The system SHALL continue to display A-share valuation data even if US stock data queries fail completely.

#### Scenario: US stock valuation query fails
- **WHEN** user views WatchList
- **AND** A-share valuation data is available
- **AND** US stock valuation query fails with an error
- **THEN** system displays A-share valuation data
- **AND** system shows error or empty state only for US stock tab

### Requirement: US stock valuation unaffected by A-share failure
The system SHALL continue to display US stock valuation data even if A-share stock data queries fail completely.

#### Scenario: A-share valuation query fails
- **WHEN** user views WatchList
- **AND** US stock valuation data is available
- **AND** A-share valuation query fails with an error
- **THEN** system displays US stock valuation data
- **AND** system shows error or empty state only for A-share tab

### Requirement: Independent trend prediction fetching
The system SHALL fetch trend predictions independently per market without blocking display.

#### Scenario: Predictions endpoint is slow or fails for one market
- **WHEN** user views WatchList
- **AND** A-share predictions are available but US predictions are slow or failing
- **THEN** system displays A-share predictions immediately
- **AND** US predictions show as loading or "-" placeholder

### Requirement: Independent HK stock valuation data loading
The system SHALL fetch HK stock valuation data independently without waiting for other market data to load.

#### Scenario: HK valuation loads independently
- **WHEN** user views WatchList with HK stocks
- **AND** HK stock valuation data arrives
- **THEN** system displays HK stock valuation data independently
- **AND** A-share and US stock sections show their own loading states independently
