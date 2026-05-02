# stock-market-tabs Specification

## Purpose
Provide tab-based UI switching between A-share (A股) and US stock (美股) markets in WatchList and PresetStockList views.

## ADDED Requirements

### Requirement: Market tab switching in WatchList
The system SHALL display a tab bar with "A股" and "美股" options above the watchlist table.

#### Scenario: Default tab selection
- **WHEN** authenticated user visits homepage
- **THEN** WatchList displays with "A股" tab selected by default

#### Scenario: Switch to US stock tab
- **WHEN** user clicks "美股" tab
- **THEN** WatchList displays only US stocks from user's watchlist
- **AND** "美股" tab shows active visual state

#### Scenario: Switch back to A-share tab
- **WHEN** user clicks "A股" tab after viewing "美股"
- **THEN** WatchList displays only A-share stocks from user's watchlist

### Requirement: Market tab switching in PresetStockList
The system SHALL display a tab bar with "A股" and "美股" options in the guest preset list.

#### Scenario: Guest views A-share preset by default
- **WHEN** guest user visits homepage
- **THEN** PresetStockList displays with "A股" tab selected by default
- **AND** shows preset A-share stocks (中国平安, 宁德时代, etc.)

#### Scenario: Guest switches to US preset
- **WHEN** guest user clicks "美股" tab
- **THEN** PresetStockList displays US preset stocks (Google, Microsoft, NVIDIA, Tesla, Coca-Cola)
- **AND** "美股" tab shows active visual state

### Requirement: Reusable StockMarketTabs component
The system SHALL provide a `StockMarketTabs` component that accepts `aShareContent` and `usContent` slots.

#### Scenario: StockMarketTabs renders correctly
- **WHEN** `StockMarketTabs` is rendered with `aShareContent={<div>A</div>}` and `usContent={<div>US</div>}`
- **THEN** component displays two tabs and renders appropriate content when each tab is selected

### Requirement: Watchlist filtering by market type
The system SHALL filter watchlist items by market type based on selected tab.

#### Scenario: A-share tab shows only A-share stocks
- **WHEN** user has mixed A-share and US stocks in watchlist
- **AND** "A股" tab is selected
- **THEN** display shows only stocks where market="A" or market is null

#### Scenario: US tab shows only US stocks
- **WHEN** user has mixed A-share and US stocks in watchlist
- **AND** "美股" tab is selected
- **THEN** display shows only stocks where market="US"
