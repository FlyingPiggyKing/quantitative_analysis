## MODIFIED Requirements

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

#### Scenario: Display trend analysis section on page load
- **WHEN** stock detail page loads
- **THEN** page SHALL display "Trend Analysis" section below the stock header
- **AND** section SHALL show a "立刻分析" (Force Analysis Now) button
- **AND** NO automatic analysis SHALL be triggered on page load

#### Scenario: Display existing prediction if available
- **WHEN** stock has existing prediction data
- **THEN** section SHALL display:
  - Trend prediction: "Up" or "Down" or "Neutral" with appropriate icon
  - Confidence percentage (e.g., "Confidence: 75%")
  - Analysis summary text
  - Last analyzed timestamp (e.g., "Analyzed: 2026-04-07 10:30")
- **AND** the "立刻分析" button SHALL still be visible for re-analysis

#### Scenario: Display empty state with button when no prediction
- **WHEN** no trend prediction exists for the stock
- **THEN** display "No analysis available yet" message
- **AND** provide "立刻分析" button to trigger analysis on demand

#### Scenario: Loading state during analysis
- **WHEN** trend analysis is triggered by user clicking the button
- **THEN** display skeleton loader or spinner in trend section
- **AND** the "立刻分析" button SHALL be disabled and show "分析中..." text
- **AND** do not block other page content from loading

### Requirement: Trend analysis requires authentication
The system SHALL require user authentication before triggering trend analysis.

#### Scenario: Guest user triggers trend analysis
- **WHEN** unauthenticated user clicks "立刻分析" button on stock detail page
- **THEN** system SHALL display login/register prompt
- **AND** analysis SHALL NOT be triggered
- **AND** user SHALL remain on the same page

#### Scenario: Authenticated user triggers trend analysis
- **WHEN** authenticated user clicks "立刻分析" button
- **THEN** system SHALL call analysis API
- **AND** button SHALL show loading state
- **AND** analysis results SHALL be displayed upon completion
