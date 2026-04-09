## Why

Currently, when users submit batch trend analysis requests, there is no visual feedback on the watch list page showing the progress of the analysis. Users must poll the task status API or wait without knowing how many stocks have been analyzed. Adding a progress bar to the list page provides real-time feedback and improves the user experience.

## What Changes

- Add a progress bar component to the watch list page bottom section
- Display real-time progress when a batch analysis task is running
- Show task status summary (e.g., "Analyzing: 3/10 stocks")
- Hide progress bar when no active task is running
- Allow dismissal of the progress indicator

## Capabilities

### New Capabilities
- `trend-analysis-progress-display`: Display a progress bar at the bottom of the watch list page showing batch analysis progress. Shows current count, total count, and overall percentage. Includes cancel/dismiss option.

### Modified Capabilities
- `background-analysis-task`: No requirement changes—progress tracking already exists in the spec. This is a frontend display enhancement only.

## Impact

- **Frontend**: New progress bar component on watch list page
- **Backend**: No changes required—existing task status API already returns progress information
- **No new dependencies**: Uses existing `/api/trend-predictions/task/{task_id}` endpoint
