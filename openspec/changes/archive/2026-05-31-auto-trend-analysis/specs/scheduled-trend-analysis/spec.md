## ADDED Requirements

### Requirement: Daily Weekday Scheduled Run
The system SHALL automatically start one trend-prediction run per trading day at 17:00 local time, Monday through Friday only, covering all stocks in the system watchlist.

The system watchlist is the deduplicated union of every user's `user_watchlist` (by symbol), as provided by the existing admin stock-statistics source.

#### Scenario: Scheduled run starts on a weekday
- **WHEN** the local time reaches 17:00 on a Monday, Tuesday, Wednesday, Thursday, or Friday
- **AND** no run is already active for that day
- **THEN** the system SHALL create a new run record dated for that day with trigger type "auto"
- **AND** the system SHALL begin executing the run's first batch

#### Scenario: No run on weekends
- **WHEN** the local time reaches 17:00 on a Saturday or Sunday
- **THEN** the system SHALL NOT start a trend-prediction run

#### Scenario: Stock set captured at run start
- **WHEN** a run is created
- **THEN** the system SHALL snapshot the current deduplicated watchlist stock list for that run
- **AND** the run's total stock count and batch composition SHALL be based on that snapshot

### Requirement: Four-Batch Sequential Division
The system SHALL divide each run's stocks into exactly 4 batches, with batch size derived from the total stock count divided by 4. Any remainder SHALL be absorbed so that all stocks are covered across the 4 batches.

#### Scenario: Even division
- **WHEN** a run has 48 stocks
- **THEN** the system SHALL create 4 batches of 12 stocks each

#### Scenario: Uneven division
- **WHEN** a run has a stock count not divisible by 4 (e.g., 50)
- **THEN** the system SHALL still create 4 batches
- **AND** the batches SHALL together cover every stock exactly once with no stock dropped

#### Scenario: Fewer stocks than batches
- **WHEN** a run has fewer than 4 stocks
- **THEN** the system SHALL still create up to 4 batches
- **AND** empty batches SHALL be treated as immediately complete

### Requirement: One Batch Every Five Hours
The system SHALL execute one batch at a time, with successive batches starting 5 hours apart, so that the first batch starts at run creation and the 4 batches complete within approximately 20 hours.

#### Scenario: Batch cadence
- **WHEN** a run's batch 1 starts at 17:00
- **THEN** batch 2 SHALL be scheduled to start at 22:00
- **AND** batch 3 SHALL be scheduled to start at 03:00 the next day
- **AND** batch 4 SHALL be scheduled to start at 08:00 the next day

#### Scenario: Only one batch runs in a 5-hour window
- **WHEN** a batch is executing
- **THEN** the system SHALL NOT start the next batch until its scheduled 5-hour mark

### Requirement: Sequential Non-Blocking Execution
The system SHALL execute each batch on a dedicated single-worker queue, analyzing the stocks within a batch one at a time in sequence, so that the run never blocks interactive API requests or other users' queries.

#### Scenario: Stocks analyzed one at a time
- **WHEN** a batch executes
- **THEN** the system SHALL analyze each stock in the batch sequentially, one completing before the next begins
- **AND** each completed stock's prediction SHALL be saved via the existing prediction storage

#### Scenario: Run does not block other requests
- **WHEN** a batch is executing
- **AND** a user issues an interactive stock query or other API request
- **THEN** the user's request SHALL be served without waiting for the run to finish
- **AND** the run SHALL use a dedicated worker separate from interactive request handling

### Requirement: Persisted Run And Batch Progress
The system SHALL persist run and batch progress so it can be reported across requests, including run date, trigger type, total stocks, current batch number (1–4), per-batch progress, and overall status.

#### Scenario: Progress is queryable
- **WHEN** a run is active
- **THEN** the persisted state SHALL expose the run date, the current batch number out of 4, and the count of stocks completed within the current batch out of the batch total

#### Scenario: Status transitions
- **WHEN** a run is created
- **THEN** its status SHALL be one of: pending, running, completed, cancelled, or interrupted
- **AND** the status SHALL become "completed" only after all 4 batches finish

### Requirement: No Catch-Up Or Backfill
The system SHALL NOT automatically run or backfill a missed scheduled run. If the scheduled run does not start at 17:00 (e.g., the backend was not running), the system SHALL NOT start it later on its own.

#### Scenario: Missed scheduled run is not auto-recovered
- **WHEN** the backend was not running at 17:00 on a weekday
- **AND** the backend later starts at 19:00
- **THEN** the system SHALL NOT automatically start that day's trend-prediction run

#### Scenario: Interrupted run is not auto-resumed
- **WHEN** the backend restarts while a run is active
- **THEN** the system SHALL NOT automatically resume the remaining batches of that run
- **AND** the interrupted run's status SHALL be marked "interrupted" on startup

### Requirement: Auto Run Cancels Active Runs
When a new scheduled (auto) run starts, the system SHALL cancel any run that is still active, because a fresh round has begun. Unfinished stocks of the cancelled run SHALL NOT be analyzed.

#### Scenario: Next-day auto run cancels a still-running prior run
- **WHEN** a manual (or prior) run is still active
- **AND** the next weekday scheduled run starts at 17:00
- **THEN** the system SHALL cancel the still-active run before starting the new one
- **AND** the cancelled run's remaining batches SHALL NOT execute
