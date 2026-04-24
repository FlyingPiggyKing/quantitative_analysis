## MODIFIED Requirements

### Requirement: WatchList 表格列布局
WatchList 表格 SHALL 包含以下列（从左到右）：股票代码、股票名称、PE趋势迷你图、市盈率(PE)、市净率(PB)、趋势预测。

#### Scenario: 默认列展示
- **WHEN** 用户访问首页 WatchList 区域
- **THEN** 表格显示：股票代码 | 股票名称 | PE趋势 | 市盈率(PE) | 市净率(PB) | 趋势预测，不包含"添加日期"列

### Requirement: Adding stock to watchlist requires authentication
The system SHALL require user authentication before adding a stock to the watchlist.

#### Scenario: Guest user attempts to add stock to watchlist
- **WHEN** unauthenticated user clicks "Add to Watchlist" button
- **THEN** system SHALL display login/register prompt
- **AND** stock SHALL NOT be added to any watchlist
- **AND** user SHALL remain on current page

#### Scenario: Authenticated user adds stock to watchlist
- **WHEN** authenticated user clicks "Add to Watchlist" button
- **THEN** system SHALL add stock to user's watchlist
- **AND** success confirmation SHALL be displayed

### Requirement: Removing stock from watchlist requires authentication
The system SHALL require user authentication before removing a stock from the watchlist.

#### Scenario: Guest user attempts to remove stock from watchlist
- **WHEN** unauthenticated user clicks "Remove" button on watchlist item
- **THEN** system SHALL display login/register prompt
- **AND** stock SHALL NOT be removed from any watchlist

#### Scenario: Authenticated user removes stock from watchlist
- **WHEN** authenticated user clicks "Remove" button on watchlist item
- **THEN** system SHALL remove stock from user's watchlist
- **AND** item SHALL be removed from the watchlist display
