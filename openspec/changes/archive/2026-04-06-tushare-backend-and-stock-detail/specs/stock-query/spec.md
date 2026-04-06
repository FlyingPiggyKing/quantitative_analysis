## ADDED Requirements

### Requirement: Stock information query
The system SHALL provide stock basic information (name, market, sector) when given a valid 6-digit Chinese stock symbol.

#### Scenario: Query existing stock
- **WHEN** user requests `/api/stock/300750`
- **THEN** system returns JSON with symbol, name, market, and sector fields

#### Scenario: Query non-existent stock
- **WHEN** user requests `/api/stock/999999`
- **THEN** system returns error message indicating stock not found

#### Scenario: Stock symbol normalization
- **WHEN** user provides symbol without exchange suffix (e.g., "300750")
- **THEN** system SHALL automatically append .SZ or .SH based on stock prefix rules
  - 6/9/5 prefix → .SH (Shanghai)
  - 0/1/2/3 prefix → .SZ (Shenzhen)

### Requirement: Real-time quote
The system SHALL provide real-time quote data for a given stock symbol.

#### Scenario: Fetch real-time quote
- **WHEN** user requests `/api/stock/{symbol}/realtime`
- **THEN** system returns current price, volume, bid/ask prices if available
