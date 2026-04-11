## ADDED Requirements

### Requirement: Trend Analysis Button on Homepage
The system SHALL provide a "趋势分析" (Trend Analysis) button on the homepage that allows authenticated users to trigger batch trend analysis for their watchlist.

#### Scenario: User clicks Trend Analysis button
- **WHEN** authenticated user clicks the "趋势分析" button
- **THEN** system SHALL call `POST /api/trend-predictions/batch-async`
- **AND** system SHALL store returned `task_id` in localStorage
- **AND** system SHALL disable the button and show "分析中..."
- **AND** system SHALL display the analysis progress bar

#### Scenario: Button disabled during active analysis
- **WHEN** user has an active analysis task (pending or running)
- **THEN** the "趋势分析" button SHALL be disabled
- **AND** button text SHALL show "分析中..."
- **AND** user SHALL NOT be able to submit another analysis request

#### Scenario: Button re-enabled after analysis completes
- **WHEN** the active task status changes to "completed" or "failed"
- **THEN** system SHALL clear the task ID from localStorage
- **AND** the "趋势分析" button SHALL become enabled
- **AND** button text SHALL return to "趋势分析"

#### Scenario: Unauthenticated user cannot see button
- **WHEN** user is not authenticated (no valid session)
- **THEN** the homepage SHALL redirect to login page
- **AND** the "趋势分析" button SHALL NOT be visible

### Requirement: Per-User Analysis Isolation
The system SHALL ensure each authenticated user's analysis is tracked separately.

#### Scenario: User's task ID stored per-browser-session
- **WHEN** user submits an analysis task
- **THEN** the task ID SHALL be stored in localStorage under key `active_analysis_task_id`
- **AND** subsequent page loads SHALL restore the task ID from localStorage
- **AND** polling SHALL resume for that user's active task

#### Scenario: Multiple users on same browser
- **WHEN** User A logs in and starts analysis
- **AND** User A logs out
- **AND** User B logs in on the same browser
- **THEN** User B's localStorage SHALL be empty of User A's task ID
- **AND** User B SHALL see an enabled "趋势分析" button
