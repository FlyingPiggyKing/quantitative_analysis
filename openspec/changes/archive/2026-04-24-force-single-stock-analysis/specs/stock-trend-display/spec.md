## MODIFIED Requirements

### Requirement: Stock Detail Trend Section
The frontend SHALL display trend analysis summary on the stock detail page with user-initiated analysis.

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
