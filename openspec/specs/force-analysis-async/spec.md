## ADDED Requirements

### Requirement: Force Analysis Async Execution
The system SHALL execute force analysis requests asynchronously via the background task queue, preventing UI blocking.

#### Scenario: Submit force analysis task
- **WHEN** user clicks "立刻分析" on stock detail page
- **THEN** system SHALL submit analysis job to background task queue
- **AND** system SHALL immediately return `{task_id, status: "pending", created_at}`
- **AND** UI SHALL display loading state

#### Scenario: Poll force analysis task status
- **WHEN** frontend polls GET `/api/trend-predictions/task/{task_id}`
- **THEN** if pending/running, system SHALL return current status and progress
- **AND** if completed, system SHALL return full analysis results
- **AND** if failed, system SHALL return error message

#### Scenario: Display results after async completion
- **WHEN** force analysis task completes successfully
- **THEN** frontend SHALL receive completed status with results
- **AND** UI SHALL display prediction results
- **AND** loading indicator SHALL be removed
- **AND** button SHALL be re-enabled

#### Scenario: Handle async analysis error
- **WHEN** force analysis task fails
- **THEN** frontend SHALL receive failed status with error message
- **AND** error SHALL be displayed to user
- **AND** button SHALL be re-enabled
- **AND** previous prediction data (if any) SHALL remain visible

### Requirement: Non-Blocking UI During Analysis
The system SHALL allow users to interact with other UI elements while force analysis runs.

#### Scenario: Watch list accessible during analysis
- **WHEN** force analysis is in progress
- **THEN** user SHALL be able to refresh watch list
- **AND** user SHALL be able to navigate to other pages
- **AND** user SHALL be able to trigger other analyses
