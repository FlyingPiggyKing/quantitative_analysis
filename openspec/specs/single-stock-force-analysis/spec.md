## ADDED Requirements

### Requirement: Stock Detail Page On-Demand Analysis
The stock detail page SHALL display a "Force Analysis Now" button in the trend analysis section. Analysis SHALL only occur when the user clicks this button.

#### Scenario: Display force analysis button
- **WHEN** stock detail page loads
- **THEN** a "立刻分析" (Force Analysis Now) button SHALL be visible in the trend analysis section header
- **AND** no automatic trend analysis fetch SHALL occur on page load

#### Scenario: Trigger forced analysis on button click
- **WHEN** user clicks "立刻分析" button
- **THEN** system SHALL call `GET /api/trend-predictions/{symbol}?force=true`
- **AND** button SHALL be disabled and show loading state
- **AND** trend section SHALL display loading indicator

#### Scenario: Display analysis results after completion
- **WHEN** forced analysis completes successfully
- **THEN** trend section SHALL display the new prediction results
- **AND** button SHALL be re-enabled
- **AND** loading indicator SHALL be removed

#### Scenario: Handle analysis error
- **WHEN** forced analysis fails
- **THEN** an error message SHALL be displayed
- **AND** button SHALL be re-enabled
- **AND** previous prediction data (if any) SHALL remain visible

### Requirement: Button Visibility Independent of Existing Data
The force analysis button SHALL be visible regardless of whether existing prediction data exists.

#### Scenario: Button visible with no existing prediction
- **WHEN** stock has no existing prediction data
- **THEN** "立刻分析" button SHALL be visible
- **AND** trend section SHALL display "暂无分析数据" message

#### Scenario: Button visible with existing prediction
- **WHEN** stock already has prediction data
- **THEN** "立刻分析" button SHALL still be visible
- **AND** existing prediction SHALL be displayed
- **AND** user CAN click button to force re-analysis

### Requirement: Clear Separation from Batch Analysis Queue
The stock detail page force analysis SHALL use direct synchronous API call, NOT the batch analysis queue.

#### Scenario: Single stock analysis uses direct endpoint
- **WHEN** user clicks "立刻分析" on stock detail page
- **THEN** system SHALL call single-stock endpoint directly (not batch-async)
- **AND** analysis SHALL complete without affecting home page batch queue state
