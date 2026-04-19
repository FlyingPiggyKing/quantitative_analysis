## MODIFIED Requirements

### Requirement: Stock Detail Trend Section
The frontend SHALL display trend analysis summary on the stock detail page.

#### Scenario: Display trend analysis section (desktop)
- **WHEN** stock detail page loads on desktop
- **THEN** page SHALL display "Trend Analysis" section below the stock header
- **AND** section SHALL show:
  - Trend prediction: "Up" or "Down" or "Neutral" with appropriate icon
  - Confidence percentage (e.g., "Confidence: 75%")
  - Analysis summary text
  - Last analyzed timestamp (e.g., "Analyzed: 2026-04-07 10:30")

#### Scenario: Display trend analysis section (mobile)
- **WHEN** stock detail page loads on mobile (iPhone 320px-428px)
- **THEN** "Trend Analysis" section SHALL display below stock header
- **AND** section SHALL show trend prediction and confidence prominently
- **AND** analysis summary text SHALL be truncated to 2 lines with "Show more" expansion
- **AND** timestamp SHALL display in smaller text below

#### Scenario: No prediction available
- **WHEN** no trend prediction exists for the stock
- **THEN** display "No analysis available yet" message
- **AND** provide "Run Analysis" button to trigger analysis on demand

#### Scenario: Loading state
- **WHEN** trend data is being fetched
- **THEN** display skeleton loader or spinner in trend section
- **AND** do not block other page content from loading

#### Scenario: Mobile trend section collapse
- **WHEN** user has viewed trend analysis on mobile
- **THEN** section SHALL be collapsible to save vertical space
- **AND** collapsed state SHALL show trend summary only (direction + confidence)

### Requirement: Trend Analysis Panel Mobile Layout
TrendAnalysisPanel SHALL adapt layout for mobile viewport.

#### Scenario: Panel layout on mobile
- **WHEN** TrendAnalysisPanel renders on mobile
- **THEN** sections (Technical Analysis, Fundamental Analysis, Sentiment) SHALL stack vertically
- **AND** each section SHALL be collapsible
- **AND** section headers SHALL be tappable to expand/collapse

#### Scenario: Panel layout on desktop
- **WHEN** TrendAnalysisPanel renders on desktop
- **THEN** sections SHALL display side-by-side or in existing grid layout (unchanged behavior)
