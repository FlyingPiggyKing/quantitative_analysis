## ADDED Requirements

### Requirement: Progress Bar Display on Watch List
The frontend SHALL display a progress bar at the bottom of the watch list page when a batch trend analysis task is running.

#### Scenario: Show progress bar during active task
- **WHEN** user navigates to watch list page AND an active analysis task exists (status: "running")
- **THEN** system SHALL display a progress bar fixed at the bottom of the page
- **AND** progress bar SHALL show: "Analyzing: X/Y stocks (Z%)" format
- **AND** progress bar SHALL show a visual progress indicator (filled bar)

#### Scenario: Progress bar hidden when no active task
- **WHEN** user navigates to watch list page AND no active analysis task exists
- **THEN** system SHALL NOT display the progress bar

#### Scenario: Progress bar updates on task status change
- **WHEN** a running task's progress updates
- **THEN** progress bar SHALL reflect the new count and percentage within 3 seconds

#### Scenario: Progress bar hides on task completion
- **WHEN** the task status changes to "completed" or "failed"
- **THEN** progress bar SHALL be removed from the page

#### Scenario: User can dismiss progress indicator
- **WHEN** user clicks the dismiss (X) button on the progress bar
- **THEN** progress bar SHALL be hidden for the current session
- **AND** system SHALL still continue processing the task in background

### Requirement: Task Persistence Across Page Refresh
The frontend SHALL persist the active task ID across page refreshes to maintain progress visibility.

#### Scenario: Progress bar shown after page refresh
- **WHEN** user refreshes the watch list page while a task is still running
- **THEN** system SHALL retrieve the active task ID from storage
- **AND** system SHALL display the progress bar with current progress

### Requirement: Progress Bar Visual Style
The frontend SHALL style the progress bar consistently with existing UI patterns.

#### Scenario: Progress bar styling
- **WHEN** progress bar is displayed
- **THEN** it SHALL use a neutral background (#F3F4F6)
- **AND** filled portion SHALL use primary blue (#3B82F6)
- **AND** text SHALL be dark gray (#374151)
- **AND** dismiss button SHALL be gray (#9CA3AF) with hover state
