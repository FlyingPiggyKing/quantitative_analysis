## Why

Currently the homepage has no dedicated button for users to trigger trend analysis. Users must rely on background tasks or external mechanisms to start analysis. Additionally, the current task tracking uses browser localStorage which doesn't properly isolate users - if multiple users share a browser, their analysis states conflict. We need a user-specific "趋势分析" button on the homepage that is disabled while analysis is in progress.

## What Changes

1. **Add "趋势分析" button on homepage** - A prominent button in the search/results area that allows users to trigger trend analysis for their watchlist
2. **User-isolated task tracking** - Each user tracks their own analysis task separately; the button reflects the current user's analysis state
3. **Button state management** - Button shows "分析中..." (analyzing) and is disabled while a task is running; returns to enabled when task completes or fails
4. **Integration with existing progress bar** - The analysis progress bar already exists and shows during analysis; button state aligns with it

## Capabilities

### New Capabilities

- `user-trend-analysis-button`: Homepage button that triggers per-user batch trend analysis, with state management for button enabled/disabled during analysis

### Modified Capabilities

- (none - the backend `/api/trend-predictions/batch-async` endpoint already requires auth and filters watchlist by user_id; this change focuses on frontend UX)

## Impact

- **Frontend**: `frontend/src/app/page.tsx` - Add button component and state management
- **Frontend**: `frontend/src/contexts/AnalysisTaskContext.tsx` - May need enhancement for user-specific task tracking
- **Backend**: No changes required - existing `/api/trend-predictions/batch-async` and `/api/trend-predictions/task/{task_id}` endpoints already support per-user isolation via auth token
