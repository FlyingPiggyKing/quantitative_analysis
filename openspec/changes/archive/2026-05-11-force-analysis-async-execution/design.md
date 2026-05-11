## Context

Currently, clicking "立刻分析" (Force Analysis Now) on the stock detail page makes a synchronous call that blocks until analysis completes. The UI becomes unresponsive — users cannot refresh the watch list, navigate, or perform other actions.

The system already has a background task queue infrastructure used by "趋势分析" (batch-async endpoint) that handles async execution via thread pool. We should reuse this infrastructure for force analysis.

## Goals / Non-Goals

**Goals:**
- Make force analysis non-blocking so UI remains responsive
- Reuse existing background task queue infrastructure
- Provide feedback to user during analysis (loading state, progress)

**Non-Goals:**
- Not creating new queue infrastructure — reuse existing
- Not changing the analysis algorithm itself
- Not adding real-time WebSocket updates (poll-based is sufficient)

## Decisions

### 1. Create new async endpoint for force analysis

**Decision**: Create `POST /api/trend-predictions/{symbol}/force-async` instead of modifying the existing synchronous `GET /api/trend-predictions/{symbol}?force=true`.

**Rationale**: The existing synchronous endpoint is used by other parts of the system. Creating a separate async endpoint keeps backward compatibility and clearly separates the two execution models.

### 2. Return task_id immediately, frontend polls

**Decision**: When force-async is called, return `{task_id, status: "pending"}` immediately instead of waiting.

**Rationale**: Simple, existing pattern already used by batch-async. Frontend can poll `/api/trend-predictions/task/{task_id}` for status.

### 3. Set cooldown on button click (not after task completion)

**Decision**: Frontend sets 1-hour cooldown in localStorage immediately when user clicks the button.

**Rationale**: If cooldown is only set after task completion, users who refresh the page during analysis would see the button as available even though they're already in the cooldown window on the backend.

**Cooldown error handling**:
- 429 rate limit error → Keep cooldown, show "操作过于频繁"
- Network error → Clear cooldown, allow retry

### 4. Call record_trigger only on successful analysis

**Decision**: Backend calls `record_trigger()` in `_run_single_analysis()` only after analysis completes successfully, not when submitting to queue.

**Rationale**: The original synchronous behavior recorded the trigger after successful analysis. Moving `record_trigger` to task submission would cause incorrect rate limiting if the task fails or is still pending.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Frontend needs to handle async flow | Poll task status and show loading until complete |
| Cooldown mismatch between frontend and backend | Frontend sets cooldown on click; backend validates on submit |
| Task fails but cooldown was set | User waits full cooldown (intentional — prevents abuse) |

## Open Questions

- Rate limiting is enforced on both frontend (localStorage) and backend (DB). Is this redundant? Yes, but frontend-only is insecure; backend-only doesn't persist on page refresh. Keeping both provides best UX with security.

