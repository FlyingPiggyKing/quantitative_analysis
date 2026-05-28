## Why

The current industry selection in the Index Metrics Panel only supports 申万一级行业 (SW Level-1 industries). Users need to drill down into specific sub-industries (二级行业) to analyze more granular sector performance. Adding a cascading menu improves usability by allowing users to first select a broad industry, then optionally drill down to a specific sub-industry while maintaining the ability to view the aggregated industry-level metrics.

## What Changes

1. **Add two-level cascading industry selector** to replace the current single-level industry dropdown
   - Level 1: Existing 申万一级行业 selection (28 industries)
   - Level 2: Sub-industry selection that dynamically loads based on Level 1 selection
   - Level 2 includes "行业汇总" option (default) that shows Level 1 aggregated metrics
2. **Backend API enhancement**: Add endpoint to fetch sub-industries (二级行业) for a given parent industry code
3. **Default behavior**: When a Level 1 industry is selected, Level 2 defaults to "行业汇总" showing the aggregated metrics

## Capabilities

### New Capabilities

- `industry-cascading-select`: Two-level cascading dropdown for industry/sub-industry selection with aggregation option
  - Level 1 dropdown displays all 申万一级行业
  - Level 2 dropdown displays sub-industries filtered by Level 1 selection + "行业汇总" option
  - "行业汇总" shows the Level 1 industry metrics (aggregated)
  - Selecting a specific sub-industry shows that sub-industry's metrics
  - Level 2 only appears/enables after Level 1 is selected

### Modified Capabilities

- `index-pe-ttm-metrics`: Industry index selection dropdown behavior changes from single-level to two-level cascading
  - The dropdown for industry selection is enhanced to support two levels
  - The requirement "28 申万一级行业 indices" remains valid for Level 1
  - New sub-industry data will come from a new API endpoint

## Impact

- **Frontend**: `IndexMetricsPanel.tsx` - add second dropdown, manage cascading state
- **Backend**: New API endpoint `/api/index/industry/subindustry?ts_code=xxx` to fetch sub-industries
- **Data Flow**: `indexMetrics.ts` - add new interface and fetch function for sub-industry list
