## Context

The "立刻分析" (Force Analysis Now) button on the stock detail page triggers trend analysis via `GET /api/trend-predictions/{symbol}?force=true`. Currently there is no rate limiting - a user can click the button repeatedly, causing unnecessary API calls, increased LLM costs, and potential abuse.

The requirement is: **one click per hour per user per stock**.

Current state:
- Backend: `TrendPredictionService` stores predictions in SQLite, keyed by symbol and date
- Backend: No user association in predictions table
- Frontend: Button triggers `runForcedSingleAnalysis()` in `trendPrediction.ts`
- Frontend: Button disabled only while `analysisRunning` is true (during the request)

## Goals / Non-Goals

**Goals:**
- Enforce 1 click per hour per user per stock rate limit on the "立刻分析" button
- Backend rejects requests within cooldown period with HTTP 429
- Frontend shows remaining cooldown time and disables button during cooldown
- User-specific tracking (requires authentication)

**Non-Goals:**
- Not a general-purpose rate limiting framework
- Does not limit batch analysis endpoint `/api/trend-predictions/batch-async`
- Does not track rate limits across multiple stocks simultaneously

## Decisions

### Decision 1: Storage for rate limit tracking

**Chosen:** New SQLite table `user_analysis_triggers` with columns:
- `user_id`: text (from auth)
- `symbol`: text
- `triggered_at`: timestamp

**Alternatives considered:**
- Redis: Would add external dependency; current app uses SQLite
- In-memory dict: Would lose state on restart; less reliable

### Decision 2: Where to enforce rate limit

**Chosen:** Backend at the API endpoint level (`GET /api/trend-predictions/{symbol}` with `force=true`)

**Rationale:**
- Single source of truth - frontend can be bypassed
- Consistent enforcement across all clients (web, mobile, etc.)
- Returns 429 status for clear error handling

### Decision 3: Cooldown window

**Chosen:** 1-hour sliding window (1 hour since last trigger, not fixed window)

**Rationale:**
- Simpler implementation: just check `triggered_at >= now() - 1 hour`
- User-friendly: allows re-trigger exactly 1 hour later

### Decision 4: Frontend cooldown tracking

**Chosen:** Store cooldown end time in localStorage, compute remaining time on mount

**Rationale:**
- Cooldown persists across page refreshes
- No backend state needed for UI display
- If user clears localStorage, backend still enforces limit

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Multiple browser tabs could show inconsistent cooldown state | Backend is authoritative; frontend is display-only |
| User clears localStorage but backend limit still applies | Backend enforces limit; button will be re-disabled after API call fails |
| Clock skew between frontend and backend | Backend is source of truth; frontend syncs from API responses |

## Open Questions

- Should the cooldown apply to the non-force endpoint too? **No** - only `force=true` triggers analysis
- Should we notify user before cooldown expires? **Not in scope for v1**
