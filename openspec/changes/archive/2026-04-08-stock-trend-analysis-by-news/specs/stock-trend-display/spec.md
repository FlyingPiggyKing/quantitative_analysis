## ADDED Requirements

### Requirement: Watch List Trend Display
The frontend SHALL display trend indicators for each stock in the watch list.

#### Scenario: Display trend on watch list
- **WHEN** watch list page loads
- **THEN** each stock row SHALL display:
  - Trend direction arrow: green up arrow for "up", red down arrow for "down", gray dash for "neutral"
  - Confidence percentage in parentheses (e.g., "↑ 75%")
- **AND** if no prediction exists, display "-" instead

#### Scenario: Color coding for trends
- **WHEN** trend direction is "up"
- **THEN** display green (#10B981) color for up arrow
- **WHEN** trend direction is "down"
- **THEN** display red (#EF4444) color for down arrow
- **WHEN** trend direction is "neutral"
- **THEN** display gray (#6B7280) color for neutral indicator

### Requirement: Stock Detail Trend Section
The frontend SHALL display trend analysis summary on the stock detail page.

#### Scenario: Display trend analysis section
- **WHEN** stock detail page loads
- **THEN** page SHALL display "Trend Analysis" section below the stock header
- **AND** section SHALL show:
  - Trend prediction: "Up" or "Down" or "Neutral" with appropriate icon
  - Confidence percentage (e.g., "Confidence: 75%")
  - Analysis summary text
  - Last analyzed timestamp (e.g., "Analyzed: 2026-04-07 10:30")

#### Scenario: No prediction available
- **WHEN** no trend prediction exists for the stock
- **THEN** display "No analysis available yet" message
- **AND** provide "Run Analysis" button to trigger analysis on demand

#### Scenario: Loading state
- **WHEN** trend data is being fetched
- **THEN** display skeleton loader or spinner in trend section
- **AND** do not block other page content from loading
