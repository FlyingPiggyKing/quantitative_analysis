## Context

The homepage (`frontend/src/app/page.tsx`) currently provides stock search functionality and displays a watchlist. When a user triggers trend analysis (via `/api/trend-predictions/batch-async`), a progress bar appears showing analysis status. However, there is no explicit button on the homepage for users to start analysis - they must use other means.

Additionally, the current task tracking uses `localStorage` which is browser-local, not user-specific. If multiple users use the same browser, their analysis states could conflict. Each authenticated user should have their own isolated analysis state.

**Existing Infrastructure:**
- Backend endpoint `POST /api/trend-predictions/batch-async` already requires auth and filters watchlist by `user_id`
- Backend endpoint `GET /api/trend-predictions/task/{task_id}` returns task status
- Frontend `AnalysisProgressBar` component displays progress
- Frontend `runBatchAnalysisAsync()` and `getTaskStatus()` functions exist in `trendPrediction.ts`

## Goals / Non-Goals

**Goals:**
- Add a "趋势分析" (Trend Analysis) button on the homepage
- Button triggers batch-async analysis for the authenticated user's watchlist
- Button is disabled while analysis is in progress (shows "分析中..." state)
- Each user's button state reflects their own analysis task status

**Non-Goals:**
- Backend changes are not needed - existing endpoints already support per-user isolation
- Modifying the analysis progress bar UI (it already works correctly)
- Creating new API endpoints

## Decisions

### Decision: Button Location
The "趋势分析" button will be placed in the form area alongside the existing search functionality, as a secondary action button below the search input.

**Rationale:** This is the main interaction area on the homepage. Users already expect to find analysis controls near the search. Placing it here also makes logical sense as both search and analysis relate to stock data.

**Alternatives Considered:**
- Sidebar: Would require layout restructuring
- Watchlist header: Less prominent, not all users scroll to watchlist

### Decision: Task State Storage
The user's active task ID will be stored in `AnalysisTaskContext` which already persists to `localStorage`. Since the app requires login and uses JWT auth, the localStorage task ID represents the logged-in user's browser session.

**Rationale:** The existing infrastructure already handles task ID persistence correctly. The auth layer ensures only the authenticated user can submit tasks.

**Alternatives Considered:**
- Server-side task ownership: Would require significant backend changes to track task-to-user mapping
- SessionStorage: Same behavior as localStorage for single browser sessions

### Decision: Button State Logic
- **Enabled:** No active task ID in localStorage OR task is completed/failed
- **Disabled:** Active task exists AND task status is "pending" or "running"

**Rationale:** Simple boolean logic based on existing task state. The progress bar already handles the case when a task completes.

## Risks / Trade-offs

**[Risk] Browser shared by multiple users**
→ **Mitigation:** Each user must log in separately. The auth token in localStorage identifies the user. Task submissions are authenticated on the backend.

**[Risk] Stale task ID in localStorage**
→ **Mitigation:** The progress bar polls `getTaskStatus()`. If the task no longer exists (server restart, cleanup), the polling will fail gracefully and clear the task ID.

## Open Questions

None at this time. The implementation is straightforward given existing infrastructure.
