## Why

Clicking "立刻分析" (Force Analysis Now) currently blocks the entire UI because it uses synchronous execution. Users cannot refresh the watch list or interact with other parts of the app while analysis runs. The existing "趋势分析" (Trend Analysis) feature already uses a background task queue — we should apply the same pattern to force analysis for consistency.

## What Changes

- Convert "立刻分析" from synchronous blocking call to asynchronous non-blocking execution
- Use the existing background task queue infrastructure (already used by batch analysis)
- Return task ID immediately instead of waiting for completion
- Frontend polls or receives updates via existing task status mechanism
- UI remains responsive during analysis
- 1-hour cooldown is set immediately on button click (not after task completion)
- Cooldown persists across page refreshes

## Capabilities

### New Capabilities
- `force-analysis-async`: Async execution of force analysis using background task queue (similar to batch analysis pattern)

### Modified Capabilities
- `single-stock-force-analysis`: Change requirement from "direct synchronous API call" to "background task queue execution" — this is a spec-level behavior change

## Impact

- **Frontend**: Must handle async task ID response, poll for status, show loading state until complete
- **Backend**: Route force analysis requests to existing background task queue instead of synchronous execution
- **API**: Response format changes from full results to `{task_id, status: "pending"}`
- No new dependencies — reuses existing background task infrastructure
