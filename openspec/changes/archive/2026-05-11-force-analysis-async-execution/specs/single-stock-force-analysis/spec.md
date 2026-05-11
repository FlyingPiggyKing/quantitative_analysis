## MODIFIED Requirements

### Requirement: Stock Detail Page On-Demand Analysis
The stock detail page SHALL display a "Force Analysis Now" button in the trend analysis section. Analysis SHALL only occur when the user clicks this button.

#### Scenario: Display force analysis button
- **WHEN** stock detail page loads
- **THEN** a "立刻分析" (Force Analysis Now) button SHALL be visible in the trend analysis section header
- **AND** no automatic trend analysis fetch SHALL occur on page load

#### Scenario: Trigger forced analysis on button click
- **WHEN** user clicks "立刻分析" button
- **THEN** system SHALL submit analysis to background task queue
- **AND** system SHALL return task_id with status "pending"
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

### Requirement: Background Task Queue Execution
The stock detail page force analysis SHALL use the background task queue, NOT synchronous execution.

#### Scenario: Single stock analysis uses background queue
- **WHEN** user clicks "立刻分析" on stock detail page
- **THEN** system SHALL submit analysis job to background task queue
- **AND** analysis SHALL run without blocking the API response
- **AND** results SHALL be retrievable via task status polling
- **AND** home page batch queue state SHALL NOT be affected

### Requirement: Cooldown After Force Analysis
After clicking "立刻分析", a 1-hour cooldown SHALL be applied to prevent repeated analysis.

#### Scenario: Set cooldown on button click
- **WHEN** user clicks "立刻分析" button
- **THEN** frontend SHALL immediately set 1-hour cooldown in localStorage
- **AND** button SHALL be disabled with countdown display
- **AND** if user refreshes page during analysis, cooldown SHALL persist

#### Scenario: Restore cooldown on page reload
- **WHEN** stock detail page loads with active cooldown
- **THEN** button SHALL display remaining time ("剩余 X:XX")
- **AND** button SHALL remain disabled until cooldown expires

#### Scenario: Clear cooldown on rate limit error
- **WHEN** API returns 429 rate limit error
- **THEN** frontend SHALL keep the cooldown already set
- **AND** user SHALL wait for cooldown to expire (backend handles timing)

#### Scenario: Clear cooldown on network error
- **WHEN** API returns network error (non-429)
- **THEN** frontend SHALL clear the cooldown
- **AND** user SHALL be able to retry immediately

#### Scenario: Rate limit enforced on backend
- **WHEN** backend receives force analysis request
- **THEN** system SHALL check `user_analysis_triggers` table for recent trigger
- **AND** if within 1-hour window, SHALL return 429 with retry_after
- **AND** `record_trigger` SHALL only be called on successful analysis completion
