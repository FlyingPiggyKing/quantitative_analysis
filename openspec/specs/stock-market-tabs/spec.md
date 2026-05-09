# stock-market-tabs Specification

## Purpose
Provide tab-based UI switching between A-share (A股), HK (港股), and US stock (美股) markets in WatchList and PresetStockList views.

## ADDED Requirements

### Requirement: Market tab switching in WatchList
The system SHALL display a tab bar with "A股", "港股", and "美股" options above the watchlist table.

#### Scenario: Default tab selection
- **WHEN** authenticated user visits homepage
- **THEN** WatchList displays with "A股" tab selected by default

#### Scenario: Switch to US stock tab
- **WHEN** user clicks "美股" tab
- **THEN** WatchList displays only US stocks from user's watchlist
- **AND** "美股" tab shows active visual state

#### Scenario: Switch to HK stock tab
- **WHEN** user clicks "港股" tab
- **THEN** WatchList displays only HK stocks from user's watchlist
- **AND** "港股" tab shows active visual state

#### Scenario: Switch back to A-share tab
- **WHEN** user clicks "A股" tab after viewing "美股"
- **THEN** WatchList displays only A-share stocks from user's watchlist

### Requirement: Market tab switching in PresetStockList
The system SHALL display a tab bar with "A股", "港股", and "美股" options in the guest preset list.

#### Scenario: Guest views A-share preset by default
- **WHEN** guest user visits homepage
- **THEN** PresetStockList displays with "A股" tab selected by default
- **AND** shows preset A-share stocks (中国平安, 宁德时代, etc.)

#### Scenario: Guest switches to HK preset
- **WHEN** guest user clicks "港股" tab
- **THEN** PresetStockList displays HK preset stocks (腾讯, 阿里巴巴, 美团, 小米, 比亚迪)
- **AND** "港股" tab shows active visual state

#### Scenario: Guest switches to US preset
- **WHEN** guest user clicks "美股" tab
- **THEN** PresetStockList displays US preset stocks (Google, Microsoft, NVIDIA, Tesla, Coca-Cola)
- **AND** "美股" tab shows active visual state

### Requirement: Reusable StockMarketTabs component
The system SHALL provide a `StockMarketTabs` component that accepts `aShareContent`, `hkContent`, and `usContent` slots. The `hkContent` slot is optional; when not provided, the 港股 tab shall not be rendered.

#### Scenario: StockMarketTabs renders with HK tab
- **WHEN** `StockMarketTabs` is rendered with `aShareContent={<div>A</div>}`, `hkContent={<div>HK</div>}`, and `usContent={<div>US</div>}`
- **THEN** component displays three tabs and renders appropriate content when each tab is selected

#### Scenario: StockMarketTabs renders without HK tab (backward compatibility)
- **WHEN** `StockMarketTabs` is rendered with only `aShareContent` and `usContent` (no `hkContent`)
- **THEN** component displays two tabs ("A股" and "美股") and renders appropriate content when each tab is selected
- **AND** no "港股" tab is rendered

### Requirement: Watchlist filtering by market type
The system SHALL filter watchlist items by market type based on selected tab.

#### Scenario: A-share tab shows only A-share stocks
- **WHEN** user has mixed A-share, HK, and US stocks in watchlist
- **AND** "A股" tab is selected
- **THEN** display shows only stocks where market="A"

#### Scenario: HK tab shows only HK stocks
- **WHEN** user has mixed A-share, HK, and US stocks in watchlist
- **AND** "港股" tab is selected
- **THEN** display shows only stocks where market="HK"

#### Scenario: US tab shows only US stocks
- **WHEN** user has mixed A-share, HK, and US stocks in watchlist
- **AND** "美股" tab is selected
- **THEN** display shows only stocks where market="US"

### Requirement: Search input placeholder reflects selected market
The system SHALL display a market-specific placeholder in the search input based on the selected tab.

#### Scenario: Search placeholder for A-share
- **WHEN** "A股" tab is selected
- **THEN** search input placeholder shows "输入股票代码，如 000001"

#### Scenario: Search placeholder for HK stocks
- **WHEN** "港股" tab is selected
- **THEN** search input placeholder shows "输入港股代码，如 00700"

#### Scenario: Search placeholder for US stocks
- **WHEN** "美股" tab is selected
- **THEN** search input placeholder shows "输入美股代码，如 MSFT"

### Requirement: Stock detail page displays stock name from API
The system SHALL display the stock name returned by the backend API for the selected stock symbol.

#### Scenario: Display stock name from Futu API
- **WHEN** user navigates to `/stock/00700` for a HK stock
- **THEN** the page displays the name from Futu OpenAPI (e.g., "TENCENT" for 腾讯)
- **AND** the name is shown in the page header alongside the symbol

#### Scenario: Display US stock name from Futu API
- **WHEN** user navigates to `/stock/AAPL`
- **THEN** the page displays the name from Futu OpenAPI (e.g., "Apple")
- **AND** the name is shown in the page header alongside the symbol

#### Scenario: Display A-share name from Tushare API
- **WHEN** user navigates to `/stock/600938`
- **THEN** the page displays the Chinese name from Tushare (e.g., "中国海油")
- **AND** the name is shown in the page header alongside the symbol

