## Context

The Index Metrics Panel currently displays two sections:
1. Index list (6 major A-share indices) with PE-TTM metrics
2. Industry section with a single dropdown for 28 申万一级行业

The industry section fetches data from `/api/index/industry/list` which returns only Level-1 industries. There's no support for sub-industry (二级行业) drilling.

**Current Flow:**
1. User selects Level-1 industry from dropdown
2. Frontend calls `/api/index/metrics?ts_code=xxx` and `/api/index/history?ts_code=xxx`
3. Metrics and chart display for the selected Level-1 industry

**Desired Flow:**
1. User selects Level-1 industry from first dropdown
2. Second dropdown populates with sub-industries + "行业汇总"
3. User selects "行业汇总" (default) → shows Level-1 aggregated metrics
4. User selects specific sub-industry → shows sub-industry metrics

## Goals / Non-Goals

**Goals:**
- Two-level cascading dropdown for industry selection
- Level-2 default to "行业汇总" showing Level-1 aggregated metrics
- Smooth transition - no breaking changes to existing index metrics

**Non-Goals:**
- Not adding more than two levels (no three-level hierarchy)
- Not changing how broad index metrics are displayed
- Not modifying the caching behavior

## Decisions

### Decision 1: New Backend Endpoint for Sub-Industry List

**Chosen Approach:** Create `/api/index/industry/subindustry?ts_code=xxx`

**Rationale:** The existing `/api/index/industry/list` returns Level-1 industries. We need a separate endpoint to fetch sub-industries filtered by parent industry code. This keeps concerns separated and allows future expansion if Level-3 is needed.

**Alternatives Considered:**
- Modify existing `/api/index/industry/list` to return hierarchical data with nested children - rejected because it would change the existing API contract
- Return all sub-industries upfront and filter client-side - rejected because there could be many sub-industries, increasing payload size unnecessarily

### Decision 2: Frontend State Management

**Chosen Approach:** Add `selectedSubIndustry` state alongside existing `selectedIndustry`

**Rationale:** Minimal state change - just add a second selection state. The existing flow already fetches metrics based on `selectedIndustry`, we just need to optionally override with `selectedSubIndustry`.

**Implementation:**
```
selectedSubIndustry = null → fetch metrics for selectedIndustry (Level-1)
selectedSubIndustry = "行业汇总" → fetch metrics for selectedIndustry (Level-1)
selectedSubIndustry = "specific_code" → fetch metrics for selectedSubIndustry (Level-2)
```

### Decision 3: UI Layout

**Chosen Approach:** Two dropdowns side by side in the industry section header

**Rationale:** Maintains the existing layout pattern. Level-1 on left, Level-2 on right. Level-2 is disabled/hidden until Level-1 is selected.

## Risks / Trade-offs

**[Risk]** Sub-industry API may be slow
→ **Mitigation:** Cache sub-industry list per Level-1 selection in frontend

**[Risk]** Some Level-1 industries may have no sub-industries
→ **Mitigation:** Show "行业汇总" as only option in Level-2 if API returns empty

**[Risk]** User confusion between Level-1 and Level-2 "行业汇总"
→ **Mitigation:** Clear labels - first dropdown "一级行业", second dropdown "二级行业/行业汇总"
