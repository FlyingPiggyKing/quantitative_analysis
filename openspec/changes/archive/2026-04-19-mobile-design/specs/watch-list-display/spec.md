## MODIFIED Requirements

### Requirement: WatchList 表格列布局
WatchList 表格 SHALL 包含以下列（从左到右）：股票代码、股票名称、PE趋势迷你图、市盈率(PE)、市净率(PB)、趋势预测。

#### Scenario: 默认列展示
- **WHEN** 用户访问首页 WatchList 区域（桌面端）
- **THEN** 表格显示：股票代码 | 股票名称 | PE趋势 | 市盈率(PE) | 市净率(PB) | 趋势预测，不包含"添加日期"列

#### Scenario: Mobile card view display
- **WHEN** 用户访问首页 WatchList 区域（移动端，iPhone 320px-428px）
- **THEN** 表格 SHALL 变换为卡片布局显示
- **AND** 每个卡片 SHALL 显示：股票代码、股票名称、PE趋势迷你图、趋势预测
- **AND** 市盈率(PE)和市净率(PB) SHALL 隐藏在可展开区域或通过图标提示

### Requirement: Watch List Trend Display
The frontend SHALL display trend indicators for each stock in the watch list.

#### Scenario: Display trend on watch list
- **WHEN** watch list page loads
- **THEN** each stock row SHALL display:
  - Trend direction arrow: green up arrow for "up", red down arrow for "down", gray dash for "neutral"
  - Confidence percentage in parentheses (e.g., "↑ 75%")
- **AND** if no prediction exists, display "-" instead

#### Scenario: Display trend on mobile card
- **WHEN** watch list renders in card view on mobile
- **THEN** each card SHALL display trend indicator prominently
- **AND** trend SHALL be visible without expanding the card

#### Scenario: Color coding for trends
- **WHEN** trend direction is "up"
- **THEN** display green (#10B981) color for up arrow
- **WHEN** trend direction is "down"
- **THEN** display red (#EF4444) color for down arrow
- **WHEN** trend direction is "neutral"
- **THEN** display gray (#6B7280) color for neutral indicator

#### Scenario: Mobile card tap interaction
- **WHEN** user taps a watchlist card on mobile
- **THEN** app SHALL navigate to stock detail page for that symbol
- **AND** card SHALL have visual feedback (opacity:0.7) during tap

#### Scenario: Mobile card touch target
- **WHEN** watchlist card renders on mobile
- **THEN** entire card SHALL have minimum 44px height
- **AND** card SHALL have `cursor-pointer` behavior indication

## ADDED Requirements

### Requirement: Mobile Watchlist Card Layout
Watchlist SHALL render as cards on mobile viewport for better usability.

#### Scenario: Card grid on mobile
- **WHEN** watchlist renders on mobile (width < 640px)
- **THEN** stocks SHALL display in single column card layout
- **AND** each card SHALL show: symbol (bold), name, trend arrow with confidence, mini PE sparkline

#### Scenario: Card spacing on mobile
- **WHEN** watchlist cards render on mobile
- **THEN** cards SHALL have `mb-3` vertical spacing
- **AND** cards SHALL have `p-3` internal padding
- **AND** cards SHALL have rounded corners (`rounded-lg`)
