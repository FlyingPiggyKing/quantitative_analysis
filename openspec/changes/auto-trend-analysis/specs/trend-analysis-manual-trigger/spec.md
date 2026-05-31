## ADDED Requirements

### Requirement: Admin-Only Manual Trigger
The system SHALL provide a manual trend-prediction trigger restricted to users with the `system_statistics` permission. The manual trigger SHALL start a run using the same four-batch, one-batch-every-five-hours, sequential, non-blocking flow as the scheduled run.

#### Scenario: Authorized admin triggers a run
- **WHEN** a user with `system_statistics` permission invokes the manual trigger
- **AND** the trigger is currently available
- **THEN** the system SHALL create a new run with trigger type "manual"
- **AND** the system SHALL begin executing the run's first batch using the same batched flow as a scheduled run

#### Scenario: Unauthorized user cannot trigger
- **WHEN** a user without `system_statistics` permission invokes the manual trigger endpoint
- **THEN** the system SHALL return HTTP 403 Forbidden
- **AND** no run SHALL be created

### Requirement: Manual Trigger Available Anytime With Confirmation
An authorized admin SHALL be able to start a manual run at any time, subject only to the one-run-at-a-time rule. When the current moment is outside the normal scheduled-run window (a weekend, a weekday before 17:00, or a day that already ran), the system SHALL require explicit confirmation before starting the run. Within the normal window (a weekday at or after 17:00 with no run yet today) a single confirmation is sufficient.

#### Scenario: Trigger within the normal window
- **WHEN** it is a weekday and the time is at or after 17:00
- **AND** no run exists for the current day
- **THEN** the manual trigger SHALL be enabled
- **AND** starting a run SHALL require a single confirmation

#### Scenario: Off-schedule trigger requires double confirmation
- **WHEN** the current moment is a weekend, a weekday before 17:00, or a day that already ran
- **AND** no run is currently active
- **THEN** the manual trigger SHALL still be enabled
- **AND** the panel SHALL indicate why the moment is off-schedule
- **AND** starting a run SHALL require the admin to confirm twice before it begins

#### Scenario: Trigger reflects availability in its status
- **WHEN** an authorized admin views the trend-analysis admin panel
- **THEN** the panel SHALL indicate whether a run is currently active
- **AND** the trigger control SHALL be disabled only while a run is active

### Requirement: Reject Manual Trigger When A Run Is Active
The system SHALL allow only one run at a time. When a run is already active, a manual trigger SHALL be rejected without creating a new run.

#### Scenario: Manual trigger rejected during an active run
- **WHEN** a run is currently active
- **AND** an authorized admin invokes the manual trigger
- **THEN** the system SHALL reject the request without creating a new run
- **AND** the response SHALL indicate that a run is already in progress

### Requirement: Manual Run Yields To Next Scheduled Run
A manual run SHALL be subject to the same priority rule as any active run: when the next scheduled (auto) run starts, the still-active manual run SHALL be cancelled and its unfinished stocks SHALL NOT be analyzed.

#### Scenario: Scheduled run supersedes an in-progress manual run
- **WHEN** a manual run is still executing its batches
- **AND** the next weekday scheduled run starts at 17:00
- **THEN** the manual run SHALL be cancelled
- **AND** the manual run's remaining batches SHALL NOT execute
