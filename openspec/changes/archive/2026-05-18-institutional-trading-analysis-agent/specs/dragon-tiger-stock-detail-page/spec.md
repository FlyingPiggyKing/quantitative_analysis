# dragon-tiger-stock-detail-page

## ADDED Requirements

### Requirement: Dragon Tiger List stock detail page shall display at dedicated URL

The system SHALL provide a dedicated detail page for stocks appearing on the Dragon Tiger List at URL path `/stock/dragon-tiger/[symbol]`, accessible by clicking a stock in the DragonTigerList component.

#### Scenario: User navigates to Dragon Tiger stock detail page
- **WHEN** User clicks on a stock in DragonTigerList component
- **THEN** Browser SHALL navigate to `/stock/dragon-tiger/{symbol}` (e.g., `/stock/dragon-tiger/300750`)
- **THEN** Page SHALL load and display stock information

#### Scenario: Page does not conflict with existing stock detail page
- **WHEN** User visits `/stock/dragon-tiger/300750`
- **THEN** Page SHALL be entirely separate from `/stock/300750`
- **THEN** Changes to dragon-tiger page SHALL NOT affect existing stock detail page

### Requirement: Detail page shall display AI 趋势分析 module with 立刻分析 button

The detail page SHALL include an AI trend analysis section with a prominent "立刻分析" (Analyze Now) button, similar to the existing stock detail page's trend analysis section.

#### Scenario: Page displays AI 趋势分析 section header
- **WHEN** Page loads successfully
- **THEN** Section header SHALL display "AI 趋 势 分 析"
- **THEN** Section SHALL include the "立刻分析" button

#### Scenario: User clicks 立刻分析 button (authenticated)
- **WHEN** Authenticated user clicks "立刻分析" button
- **THEN** System SHALL submit analysis to background queue
- **THEN** Button SHALL change to "分析中…" state
- **THEN** Progress SHALL be displayed during analysis
- **THEN** Results SHALL appear when analysis completes

#### Scenario: User clicks 立刻分析 button (unauthenticated)
- **WHEN** Guest user clicks "立刻分析" button
- **THEN** System SHALL show authentication modal with appropriate message
- **THEN** Analysis SHALL NOT proceed until user authenticates

### Requirement: Detail page shall display analysis results

After analysis completes, the page SHALL display the full analysis results in a format compatible with the existing `TrendAnalysisPanel` component.

#### Scenario: Display hero prediction section
- **WHEN** Analysis completes successfully
- **THEN** System SHALL display trend direction badge (▲ 看涨 / ▼ 看跌 / ◆ 中性)
- **THEN** System SHALL display confidence percentage
- **THEN** System SHALL display analysis timestamp

#### Scenario: Display extended analysis panels
- **WHEN** Analysis includes extended data (情绪分析, 技术分析, 趋势判断)
- **THEN** System SHALL render TrendAnalysisPanel component
- **THEN** Panel SHALL display news sentiment, technical analysis, and trend judgment

#### Scenario: Display error state
- **WHEN** Analysis fails
- **THEN** System SHALL display error message in red text
- **THEN** System SHALL allow user to retry analysis

### Requirement: Detail page shall show loading state during analysis

The page SHALL provide clear visual feedback during the analysis process.

#### Scenario: Analysis in progress
- **WHEN** User submits analysis and waits for results
- **THEN** Page SHALL display "分析进行中，请稍候…" message
- **THEN** Button SHALL be disabled during analysis

### Requirement: Detail page shall fetch and display stock data

The page SHALL load stock information from backend APIs.

#### Scenario: Page loads stock information
- **WHEN** Page loads
- **THEN** System SHALL fetch stock info from `/api/stock/{symbol}`
- **THEN** System SHALL fetch K-line data from `/api/stock/{symbol}/kline?days=100`
- **THEN** System SHALL fetch indicators from `/api/stock/{symbol}/indicators?days=100`

#### Scenario: Page handles data loading errors
- **WHEN** API returns error or network failure
- **THEN** Page SHALL display error message
- **THEN** Page SHALL show "返回" button to navigate back

### Requirement: Detail page header shall show stock identity

The page header SHALL clearly identify the stock being analyzed.

#### Scenario: Page header displays stock info
- **WHEN** Page loads successfully
- **THEN** Header SHALL display stock name
- **THEN** Header SHALL display stock symbol in monospace font
- **THEN** Header SHALL display latest price and daily change percentage
- **THEN** Header SHALL include "← 返回" link to go back
