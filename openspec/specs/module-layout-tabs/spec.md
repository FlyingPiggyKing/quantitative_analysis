# module-layout-tabs Specification

## Purpose
Provide top-level module tab switching between "我的自选" (WatchList) and "投资分析" (Investment Analysis) modules on the homepage.

## ADDED Requirements

### Requirement: Top-level module tab bar display
The system SHALL display a top-level tab bar with two options: "我的自选" and "投资分析".

#### Scenario: Default module selection
- **WHEN** authenticated user visits homepage
- **THEN** "我的自选" tab is selected by default

#### Scenario: Switch to Investment Analysis module
- **WHEN** user clicks "投资分析" tab
- **THEN** system displays the Investment Analysis content (机构龙虎榜)
- **AND** "投资分析" tab shows active visual state

#### Scenario: Switch back to WatchList module
- **WHEN** user clicks "我的自选" tab after viewing "投资分析"
- **THEN** system displays the WatchList content
- **AND** "我的自选" tab shows active visual state

### Requirement: Module tabs position
The top-level module tabs SHALL be displayed at the position where the current "我的自选" title appears (above the content area).

#### Scenario: Tab bar replaces WatchList title
- **WHEN** user views the homepage
- **THEN** the module tab bar appears where the "我的自选" header previously was
- **AND** no duplicate "我的自选" title is displayed

### Requirement: Module tab text styling
The module tab text SHALL be displayed with larger font size (text-base) and semibold weight.

#### Scenario: Tab text appearance
- **WHEN** module tabs are rendered
- **THEN** "我的自选" and "投资分析" use text-base font size and font-semibold class

### Requirement: Module state affects sub-module tabs
The top-level module selection SHALL determine which sub-module tabs are displayed at the bottom.

#### Scenario: WatchList module shows market sub-tabs
- **WHEN** "我的自选" module is selected
- **THEN** bottom tabs show "A股", "美股", "港股" options

#### Scenario: Analysis module shows analysis sub-tabs
- **WHEN** "投资分析" module is selected
- **THEN** bottom tabs show "机构龙虎榜" option

### Requirement: Module state preserved during session
The selected module SHALL be preserved in component state during the user's session.

#### Scenario: Module selection persists during navigation
- **WHEN** user selects "投资分析" module
- **AND** user navigates to a stock detail page
- **AND** user returns to homepage
- **THEN** "投资分析" module remains selected
