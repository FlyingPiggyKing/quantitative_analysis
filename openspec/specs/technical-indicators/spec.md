## ADDED Requirements

### Requirement: MACD calculation
The system SHALL calculate MACD (Moving Average Convergence Divergence) indicator.

#### Scenario: Calculate MACD with default parameters
- **WHEN** user requests `/api/stock/{symbol}/indicators?days=100`
- **THEN** system SHALL calculate MACD(12, 26, 9)
- **AND** return DIF (MACD line), DEA (signal line), and HIST (MACD histogram)

#### Scenario: MACD calculation accuracy
- **WHEN** MACD is calculated
- **THEN** DIF SHALL be EMA(close, 12) - EMA(close, 26)
- **AND** DEA SHALL be EMA(DIF, 9)
- **AND** HIST SHALL be DIF - DEA

### Requirement: RSI calculation
The system SHALL calculate RSI (Relative Strength Index) for multiple periods.

#### Scenario: Calculate RSI with default periods
- **WHEN** user requests indicators
- **THEN** system SHALL calculate RSI(6), RSI(12), and RSI(24)

#### Scenario: RSI interpretation
- **WHEN** RSI value is returned
- **THEN** values above 70 SHALL be highlighted as overbought (red)
- **AND** values below 30 SHALL be highlighted as oversold (green)

### Requirement: Moving Average calculation
The system SHALL calculate Simple Moving Average (SMA) for standard periods.

#### Scenario: Calculate MA for standard periods
- **WHEN** user requests indicators
- **THEN** system SHALL calculate MA5, MA10, MA20, and MA60
- **AND** MA60 may be null if insufficient data (< 60 trading days)

### Requirement: Indicator display panel
The frontend SHALL display technical indicators in a structured panel.

#### Scenario: Display indicator cards
- **WHEN** indicators are loaded
- **THEN** system SHALL display three cards: MACD, RSI, MA
- **AND** each card SHALL show relevant values with 2 decimal precision
