## ADDED Requirements

### Requirement: Background Analysis Task Queue
The system SHALL provide a background task queue for trend analysis jobs, allowing analysis to run without blocking the API response.

#### Scenario: Queue analysis task
- **WHEN** client sends POST request to `/api/trend-predictions/batch-async`
- **THEN** system SHALL immediately return a task ID with status "pending"
- **AND** system SHALL queue the analysis job for background execution
- **AND** response SHALL include `task_id`, `status`, and `created_at`

#### Scenario: Execute analysis in background thread
- **WHEN** a pending task is picked up for execution
- **THEN** system SHALL process analysis in a dedicated thread pool
- **AND** system SHALL update task status to "running"
- **AND** system SHALL update task progress (e.g., "3/10 stocks analyzed")

#### Scenario: Poll task status
- **WHEN** client sends GET request to `/api/trend-predictions/task/{task_id}`
- **THEN** system SHALL return current status: "pending", "running", "completed", or "failed"
- **AND** if running, SHALL include progress information
- **AND** if completed, SHALL include analysis results
- **AND** if failed, SHALL include error message

#### Scenario: Task completion with results
- **WHEN** background analysis completes successfully
- **THEN** system SHALL store results in database
- **AND** system SHALL update task status to "completed"
- **AND** subsequent GET on task_id SHALL return full analysis results

#### Scenario: Task failure handling
- **WHEN** background analysis encounters an error
- **THEN** system SHALL set task status to "failed"
- **AND** system SHALL store error message in task record
- **AND** GET on task_id SHALL return the error for debugging

### Requirement: Concurrent Task Handling
The system SHALL handle multiple concurrent analysis requests without blocking.

#### Scenario: Multiple simultaneous requests
- **WHEN** multiple clients submit batch analysis requests simultaneously
- **THEN** system SHALL queue each request separately
- **AND** system SHALL process them according to thread pool capacity
- **AND** no request SHALL block another

### Requirement: Task Expiration
The system SHALL expire stale tasks to prevent memory buildup.

#### Scenario: Task cleanup after completion
- **WHEN** a task has been completed or failed for more than 24 hours
- **THEN** system SHALL remove the task from memory
- **AND** results SHALL remain in database for retrieval via existing endpoints
