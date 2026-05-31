## ADDED Requirements

### Requirement: Trend Analysis Progress Panel
The system SHALL display a trend-analysis progress panel within the System Administration module, showing the current run's date, the active batch number out of 4, and progress within that batch.

#### Scenario: Panel shows the active run progress
- **WHEN** an admin user with `system_statistics` permission views the System Administration module
- **AND** a trend-prediction run is active
- **THEN** a trend-analysis progress block SHALL be displayed
- **AND** it SHALL show the run date (e.g., month and day)
- **AND** it SHALL show which batch is running out of 4 (e.g., "第 2/4 批")
- **AND** it SHALL show progress within the current batch (e.g., "7/12")

#### Scenario: Panel shows status when no run is active
- **WHEN** an admin user views the System Administration module
- **AND** no run is active
- **THEN** the panel SHALL indicate the latest run's date and final status, or that there is no run yet

### Requirement: Manual Trigger Button In Admin Module
The system SHALL display a manual "趋势分析" trigger button below the trend-analysis progress panel, visible only to users with `system_statistics` permission. The button SHALL be enabled whenever no run is active, and SHALL be disabled while a run is active (with the reason shown). When the moment is off-schedule, the button stays enabled but starting a run requires double confirmation.

#### Scenario: Admin sees an enabled trigger when idle
- **WHEN** an admin user views the System Administration module
- **AND** no run is currently active
- **THEN** the "趋势分析" trigger button SHALL be shown and enabled

#### Scenario: Trigger button disabled while a run is active
- **WHEN** an admin user views the System Administration module
- **AND** a run is currently active
- **THEN** the "趋势分析" trigger button SHALL be shown disabled
- **AND** the panel SHALL show why it is disabled (a run is in progress)

#### Scenario: Clicking the trigger starts a manual run
- **WHEN** an admin user clicks the enabled "趋势分析" trigger button
- **AND** completes any required confirmation
- **THEN** the system SHALL start a manual run
- **AND** the progress panel SHALL begin reflecting the new run's batch progress

### Requirement: Admin Trend-Run API Endpoints
The system SHALL provide API endpoints, restricted to users with `system_statistics` permission, to read the current trend-run status (including manual-trigger availability) and to start a manual run.

#### Scenario: Authorized user reads run status
- **WHEN** a user with `system_statistics` permission requests the trend-run status endpoint with valid authentication
- **THEN** the response SHALL include the current/last run's date, trigger type, status, current batch number out of 4, per-batch progress, and whether the manual trigger is available

#### Scenario: Authorized user starts a manual run
- **WHEN** a user with `system_statistics` permission calls the manual-trigger endpoint
- **AND** the trigger is available and no run is active
- **THEN** the system SHALL start a manual run and return its run identity and status

#### Scenario: Unauthorized user blocked from trend-run endpoints
- **WHEN** a user without `system_statistics` permission calls the trend-run status or manual-trigger endpoint
- **THEN** the system SHALL return HTTP 403 Forbidden
