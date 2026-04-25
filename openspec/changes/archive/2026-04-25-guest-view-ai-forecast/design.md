## Context

The homepage currently displays a preset list of stocks for unauthenticated (guest) users via `PresetStockList` component. This view shows stock info and valuation metrics (PE, PB, turnover rate). For logged-in users, the `WatchList` component additionally displays AI trend predictions in an "AI下周预测" column with color-coded trend direction and confidence percentage.

The backend already exposes predictions via `/api/trend-predictions` as a public endpoint (no authentication required). The frontend already has the necessary types and service functions in `trendPrediction.ts`.

## Goals / Non-Goals

**Goals:**
- Display AI trend predictions in guest view (`PresetStockList`)
- Maintain visual consistency with logged-in view (`WatchList`)
- Reuse existing `TrendIndicator` component pattern
- Handle missing predictions gracefully (show "-" instead of empty)

**Non-Goals:**
- No new backend API changes
- No authentication logic changes
- No new database queries or storage

## Decisions

### Decision: Reuse existing trend prediction service

The frontend `trendPrediction.ts` already exports `getTrendPredictions()` which returns `TrendPrediction[]` containing `symbol`, `trend_direction`, `confidence`. This is the same API used by `WatchList`.

**Rationale:** Avoid duplicating API call logic. The existing service already handles the endpoint correctly.

### Decision: Reuse `TrendIndicator` component pattern

The `WatchList` component uses a local `TrendIndicator` function component to render trend direction with color coding. We will apply the same pattern in `PresetStockList`.

**Rationale:** Consistent UI across guest and logged-in views. Color coding (green/red/gray) provides instant visual feedback on trend direction.

### Decision: Fetch predictions alongside existing data

In `PresetStockList`, add `getTrendPredictions()` call alongside the existing batch info/valuation fetches.

**Rationale:** Parallel fetching maintains current performance. Predictions are independent of valuation data.

## Risks / Trade-offs

[Risk] **Predictions may not exist for all preset stocks**
→ Mitigation: Display "-" when no prediction exists, consistent with `WatchList` behavior

[Risk] **Extra API call on guest homepage**
→ Mitigation: `getTrendPredictions()` returns cached data from backend; no additional analysis triggered

[Risk] **Inconsistent data freshness**
→ Mitigation: Predictions are daily-cached; guest view shows same data as logged-in view
