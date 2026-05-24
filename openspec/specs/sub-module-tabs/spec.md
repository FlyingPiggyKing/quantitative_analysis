# sub-module-tabs Specification

## Purpose
Provide bottom sub-module tab switching for each top-level module. WatchList has A股/美股/港股 tabs, Investment Analysis has 机构龙虎榜 tab.

## ADDED Requirements

### Requirement: Bottom sub-module tab bar display
The system SHALL display a bottom tab bar that shows sub-module options based on the selected top-level module.

#### Scenario: WatchList sub-tabs display
- **WHEN** "我的自选" top-level module is selected
- **THEN** bottom tab bar displays "A股", "美股", "港股" options

#### Scenario: Analysis sub-tabs display
- **WHEN** "投资分析" top-level module is selected
- **THEN** bottom tab bar displays "机构龙虎榜" option

### Requirement: Sub-module tab position at bottom
The sub-module tabs SHALL be displayed at the bottom of the module content area, below the content.

#### Scenario: Bottom placement below content
- **WHEN** user views WatchList module
- **THEN** the stock table/content appears first
- **AND** the sub-module tab bar appears below the content

### Requirement: Sub-module default selection
Each module's sub-module SHALL have a default selection when the parent module is selected.

#### Scenario: WatchList default to A-share
- **WHEN** user selects "我的自选" module
- **THEN** "A股" sub-tab is selected by default

#### Scenario: Analysis default to DragonTiger
- **WHEN** user selects "投资分析" module
- **THEN** "机构龙虎榜" sub-tab is selected by default

### Requirement: Sub-module selection resets on parent change
When the top-level module changes, the sub-module selection SHALL reset to its default.

#### Scenario: Reset sub-module when switching modules
- **WHEN** user is on "我的自选" with "美股" sub-tab selected
- **AND** user switches to "投资分析" module
- **THEN** "机构龙虎榜" sub-tab is selected
- **AND** if user returns to "我的自选", "A股" sub-tab is selected (not "美股")

### Requirement: Tab styling consistent with existing design
The sub-module tabs SHALL use the same visual styling as the existing StockMarketTabs component.

#### Scenario: Tab appearance matches StockMarketTabs
- **WHEN** sub-module tabs are rendered
- **THEN** visual styling (colors, underline, transitions) matches the existing StockMarketTabs component

### Requirement: Investment Analysis module styling
The "机构龙虎榜" tab SHALL be displayed without a surrounding panel border and padding, using only the tab bar with date on the right.

#### Scenario: DragonTiger tab without border
- **WHEN** "投资分析" module is selected
- **THEN** "机构龙虎榜" tab bar is displayed inline without vt-panel container
- **AND** date is shown on the right side of the tab bar

#### Scenario: DragonTiger tab text styling
- **WHEN** "机构龙虎榜" tab is rendered
- **THEN** text uses larger font (text-base) and semibold weight to match main module tabs

### Requirement: DragonTigerList merged buy/sell display
The DragonTigerList SHALL display 净买入 and 净卖出 as two stacked sections within the same view, without using tabs to switch between them.

#### Scenario: Net buy and net sell displayed together
- **WHEN** DragonTigerList content is rendered
- **THEN** 净买入 section appears above 净卖出 section
- **AND** each section has its own header indicator (▲ for buy, ▼ for sell)
- **AND** both sections are visible without tab switching
