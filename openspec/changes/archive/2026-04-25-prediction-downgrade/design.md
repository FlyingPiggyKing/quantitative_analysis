## Context

The `get_prediction` API endpoint (`/api/trend-predictions/{symbol}`) serves AI trend predictions to both authenticated users and guests. When `force=false` (the default, non-authenticated path), it calls `get_today_prediction()` which only returns predictions created on the current calendar day. If no analysis has run today, it raises HTTP 404.

The frontend (`stock/[symbol]/page.tsx`) calls this endpoint via `getTrendPrediction(symbol)` to display the "趋势分析" panel. A 404 result causes `trendPrediction` to be `null`, showing "暂无分析数据" to users even when yesterday's predictions are available and informative.

This design addresses the fallback behavior only — the daily analysis scheduling mechanism (a separate concern) remains unchanged.

## Goals / Non-Goals

**Goals:**
- When no prediction exists for today, return the most recent prediction from the database instead of 404
- Signal to the frontend when returned data is from a previous day (via `is_fallback` field)
- Preserve force-analysis behavior: rate-limiting, authentication requirements, and forced re-analysis semantics remain unchanged

**Non-Goals:**
- Changing when/how daily analysis is triggered (out of scope — separate scheduling concern)
- Modifying the `predictions` database schema
- Changing prediction storage or caching logic

## Decisions

### Decision: Return fallback instead of 404 in `get_prediction`

**Option A (chosen):** When `get_today_prediction` returns `None`, call `get_latest_prediction(symbol)` as fallback. Add `is_fallback: true` to the response. Frontend displays data with a "非今日数据" label.

**Option B:** Change `get_today_prediction` to internally fall back to `get_latest_prediction`. Simpler but hides the staleness signal from callers.

**Option C:** Frontend polling logic falls back to a second endpoint like `/api/trend-predictions/{symbol}/latest`. Extra network request, additional API surface.

**Chosen: Option A** — Explicit `is_fallback` field gives frontend the information it needs to communicate data freshness to users. Single request, clear semantics.

### Decision: No changes to `PredictionResponse` schema — use existing `analyzed_at` field

The `analyzed_at` field in `PredictionResponse` already tells the frontend the exact timestamp. Combined with the new `is_fallback` boolean, callers can format messages like "数据更新于 2026-04-24" or similar.

**Alternative:** Add `data_freshness: "today" | "yesterday" | "stale"`. More opinionated but requires frontend changes to handle enum values.

**Chosen:** Simpler `is_fallback: bool` — minimal schema change, frontend derives freshness from `analyzed_at`.

## Risks / Trade-offs

[Risk] **Stale data shown as current** — Users might mistake yesterday's prediction for today's.
→ Mitigation: Frontend should display `analyzed_at` timestamp or "非今日数据" badge when `is_fallback=true`.

[Risk] **Force analysis not triggered** — Guests never trigger force analysis (requires auth), so they always see fallback. This is acceptable because guests already cannot trigger analysis.
→ Not a concern — intended behavior.

[Risk] **Frequent fallback fallback hits** — If analysis runs infrequently, `get_latest_prediction` might return very old data (e.g., >7 days).
→ Mitigation: Consider adding an `is_stale` threshold (e.g., if fallback data is >7 days old, still return 404). Can be addressed in a follow-up if it becomes an issue.
