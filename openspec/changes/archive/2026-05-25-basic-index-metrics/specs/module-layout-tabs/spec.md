## MODIFIED Requirements

### Requirement: Analysis module shows index metrics sub-tab
The "投资分析" module SHALL display an additional "指数指标" sub-tab option.

#### Scenario: Index metrics tab appears in analysis module
- **WHEN** "投资分析" module is selected
- **THEN** the sub-module tabs show "资金流向", "机构龙虎榜", and "指数指标" options

#### Scenario: Index metrics tab not visible in watchlist module
- **WHEN** "我的自选" module is selected
- **THEN** "指数指标" tab is NOT displayed
