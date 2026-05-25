## 1. Backend API - Sub-Industry Endpoint

- [x] 1.1 Add `SW_SUB_INDUSTRY_MAP` mapping Level-1 ts_code to list of sub-industries in `backend/api/index_metrics.py`
- [x] 1.2 Add `/api/index/industry/subindustry` endpoint that accepts `ts_code` query param and returns sub-industries
- [x] 1.3 Verify endpoint works: `curl "http://localhost:8000/api/index/industry/subindustry?ts_code=801010.SI"` (endpoint added, curl test pending server restart)

## 2. Frontend Service - Type and API Function

- [x] 2.1 Add `SubIndustryInfo` interface to `frontend/src/services/indexMetrics.ts`
- [x] 2.2 Add `SubIndustryListResponse` interface
- [x] 2.3 Add `fetchSubIndustryList(ts_code: string)` function
- [x] 2.4 Verify new types compile without errors

## 3. Frontend Component - Cascading Dropdown State

- [x] 3.1 Add `selectedSubIndustry` state (default: `"行业汇总"`)
- [x] 3.2 Add `subIndustries` state to store fetched sub-industries
- [x] 3.3 Add `subIndustryLoading` state for loading indicator
- [x] 3.4 Modify `useEffect` that loads industry data to consider sub-industry selection

## 4. Frontend Component - Second Dropdown UI

- [x] 4.1 Add second dropdown labeled "二级行业/行业汇总" after first dropdown
- [x] 4.2 Second dropdown disabled until Level-1 is selected
- [x] 4.3 Second dropdown options: "行业汇总" (default) + fetched sub-industries
- [x] 4.4 When Level-1 changes, reset Level-2 to "行业汇总" and fetch new sub-industries
- [x] 4.5 When "行业汇总" selected, use Level-1 ts_code for metrics
- [x] 4.6 When specific sub-industry selected, use sub-industry ts_code for metrics

## 5. Verification

- [ ] 5.1 Run frontend dev server and verify both dropdowns render
- [ ] 5.2 Select different Level-1 industries and verify Level-2 options update
- [ ] 5.3 Select "行业汇总" and verify metrics show Level-1 aggregated data
- [ ] 5.4 Select specific sub-industry and verify metrics update to sub-industry data
- [x] 5.5 Verify no TypeScript errors in `indexMetrics.ts` and `IndexMetricsPanel.tsx`
