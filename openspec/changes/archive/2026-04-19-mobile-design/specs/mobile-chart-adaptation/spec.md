## ADDED Requirements

### Requirement: Chart Height Adaptation
Charts SHALL adapt their height for mobile viewport to remain visible and readable.

#### Scenario: Stock candlestick chart on iPhone
- **WHEN** stock detail page renders on iPhone
- **THEN** candlestick chart height SHALL be approximately 250px
- **AND** chart width SHALL be 100% of container

#### Scenario: Chart in landscape orientation
- **WHEN** device is in landscape orientation on mobile
- **THEN** chart SHALL use full available width
- **AND** height SHALL be proportional to maintain aspect ratio

### Requirement: Indicator Panel Mobile Layout
Indicator panels SHALL stack vertically on mobile instead of 3-column grid.

#### Scenario: Indicator panel on mobile
- **WHEN** indicator panel renders on mobile
- **THEN** indicators SHALL stack vertically (MACD, RSI, MA each full width)
- **AND** each indicator SHALL have collapsible behavior to save vertical space

#### Scenario: Indicator panel on tablet/desktop
- **WHEN** indicator panel renders on tablet or desktop
- **THEN** indicators SHALL display in 3-column grid (existing behavior)

### Requirement: Chart Interactions on Touch
Charts SHALL support basic touch interactions on mobile.

#### Scenario: Chart crosshair on touch
- **WHEN** user taps on candlestick chart on mobile
- **THEN** crosshair SHALL display at tap position
- **AND** tooltip SHALL show price/date info near tap point

#### Scenario: Chart scrolling
- **WHEN** user scrolls vertically on stock detail page
- **THEN** chart SHALL NOT intercept vertical scroll gestures
- **AND** chart data remains accessible via scrolling

### Requirement: PE Trend Sparkline Mobile Display
PE trend sparklines SHALL render appropriately on mobile cards.

#### Scenario: Sparkline on mobile watchlist card
- **WHEN** watchlist renders in card view on mobile
- **THEN** PE sparkline SHALL display at reduced size (~60px wide)
- **AND** sparkline SHALL NOT display axis labels on mobile
