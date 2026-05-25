## ADDED Requirements

### Requirement: Search and trend analysis button layout
The homepage SHALL display 查询 and 趋 势 分 析 buttons, with 趋 势 分 析 only visible to authenticated users.

#### Scenario: Logged-out user sees single button
- **WHEN** an unauthenticated user views the homepage search form
- **THEN** only the "查 询" button is displayed
- **AND** it spans the full width of the form

#### Scenario: Logged-in user sees two buttons side by side
- **WHEN** an authenticated user views the homepage search form
- **THEN** "查 询" and "趋 势 分 析" buttons are displayed on the same row
- **AND** each button takes 50% of the available width (flex-1)
- **AND** buttons are separated by a gap-3 gap

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
