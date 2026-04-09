## Context

The watch list page allows users to submit batch trend analysis requests for multiple stocks. Currently, after submitting a request, users have no visual feedback until the analysis completes. The backend already tracks progress (e.g., "3/10 stocks analyzed") via the task status API.

## Goals / Non-Goals

**Goals:**
- Display analysis progress bar at the bottom of the watch list page
- Show real-time progress: current count, total count, and percentage
- Provide ability to dismiss or cancel the progress indicator
- Auto-hide when no active task is running

**Non-Goals:**
- No changes to backend task queue or API
- No new endpoints required
- Not applicable to individual stock detail pages (only watch list)

## Decisions

### 1. Progress Bar Location
**Decision**: Fixed position at bottom of page, above the footer.

**Rationale**: Doesn't interfere with existing content, always visible regardless of scroll position, standard pattern for global notifications/progress.

### 2. Polling Strategy
**Decision**: Poll `/api/trend-predictions/task/{task_id}` every 3 seconds while task is running.

**Rationale**: Balances real-time feedback with server load. Backend already supports progress in response. Simpler than WebSocket integration.

**Alternative**: WebSocket for real-time push. Rejected—added complexity not warranted for progress updates.

### 3. State Management
**Decision**: Store active task_id in React state/context, check localStorage for any pending task on page load.

**Rationale**: Preserves progress display across page refreshes. Simple key-value approach sufficient.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Progress bar persists after task completion/failure | Ensure component clears state on "completed" or "failed" status |
| Multiple browser tabs with different tasks | Show most recently submitted task only |
| Long-running tasks (hour+) | No timeout changes—backend handles via existing expiration |
