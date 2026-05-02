# us-stock-presets Specification

## Purpose
Display preset US stocks (Google, Microsoft, NVIDIA, Tesla, Coca-Cola) in the guest view 美股 tab.

## ADDED Requirements

### Requirement: US preset stock list
The system SHALL define preset US stocks in `US_PRESET_STOCKS` constant.

#### Scenario: US preset stocks are defined
- **WHEN** application loads
- **THEN** `US_PRESET_STOCKS` contains: GOOGL (Google), MSFT (Microsoft), NVDA (NVIDIA), TSLA (Tesla), KO (可口可乐)

### Requirement: US preset stocks display in 美股 tab
The system SHALL display US preset stocks when guest user selects "美股" tab.

#### Scenario: Guest selects US preset tab
- **WHEN** guest user clicks "美股" tab on PresetStockList
- **THEN** display shows table/grid of 5 preset US stocks with symbol, name, PE, PB, turnover_rate, AI prediction

#### Scenario: US preset stocks fetch data
- **WHEN** PresetStockList renders US preset stocks
- **THEN** system fetches batch info and valuation for all US preset symbols
- **AND** displays loading state until data arrives

### Requirement: US preset stocks have Chinese names
The system SHALL display Chinese names for US preset stocks where appropriate.

#### Scenario: Display Chinese names for US stocks
- **WHEN** US preset stocks are displayed
- **THEN** Google shows "谷歌", Microsoft shows "微软", NVIDIA shows "英伟达", Tesla shows "特斯拉", Coca-Cola shows "可口可乐"
