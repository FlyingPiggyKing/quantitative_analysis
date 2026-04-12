## MODIFIED Requirements

### Requirement: K-line chart visualization (UPDATED)
The frontend SHALL display K-line data as an interactive candlestick chart with additional valuation metric series.

#### Scenario: Display candlestick chart
- **WHEN** stock data is loaded
- **THEN** chart SHALL display candlestick series with up/down colors
- **AND** red candles for price increase, green candles for price decrease

#### Scenario: Display volume histogram
- **WHEN** stock data is loaded
- **THEN** chart SHALL display volume as histogram below candlesticks
- **AND** volume bars colored according to price direction

#### Scenario: Display PE line series
- **WHEN** valuation data is available for the stock
- **THEN** chart SHALL display PE as a line series below volume
- **AND** PE line SHALL use a distinct color (e.g., #fbbf24 yellow)
- **AND** PE series SHALL have its own price scale on the right axis

#### Scenario: Display PB line series
- **WHEN** valuation data is available for the stock
- **THEN** chart SHALL display PB as a line series below PE
- **AND** PB line SHALL use a distinct color (e.g., #8b5cf6 purple)
- **AND** PB series MAY share the price scale with PE or have separate scale

#### Scenario: Chart time scale
- **WHEN** chart is rendered
- **THEN** time scale SHALL fit to data range
- **AND** time labels SHALL be visible
- **AND** all series (volume, PE, PB) SHALL share the same time axis

#### Scenario: Chart legend
- **WHEN** chart is rendered
- **THEN** chart SHALL display a legend identifying PE and PB lines
- **AND** legend SHALL show current values for PE and PB
