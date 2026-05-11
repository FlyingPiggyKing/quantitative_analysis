## 1. Fetch Money Flow Data in analyze_stock_trend()

- [x] 1.1 Add money flow fetch call (5 days) after technical data fetch in `analyze_stock_trend()`
- [x] 1.2 Wrap money flow fetch in try/except to ensure graceful degradation
- [x] 1.3 Pass money flow data to `format_data_context()`

## 2. Format Money Flow in Valuation Section

- [x] 2.1 Update `format_data_context()` signature to accept optional `money_flow_data` parameter
- [x] 2.2 Append 5-day cumulative money flow line to the existing valuation section (after PE, PB, 换手率, 总市值)

## 3. Update System Prompt for Money Flow Analysis

- [x] 3.1 Add money flow signals (主力净流入/净流出) to the "Analyze the provided technical data" checklist in `get_system_prompt()`

## 4. Validate AI Agent Output Parsing

- [x] 4.1 Verify `_parse_agent_output()` handles missing `money_flow` in `技术分析` gracefully
- [x] 4.2 Test end-to-end: run `analyze_stock_trend()` for a stock and verify money flow appears in `技术分析` when returned by agent

## 5. Frontend Rendering

- [x] 5.1 Add `money_flow` field to `TechnicalAnalysis` interface in `trendPrediction.ts`
- [x] 5.2 Add money flow card to `TrendAnalysisPanel.tsx` under `技术分析` section
- [x] 5.3 Verify `money_flow` renders with net_5d value, signal text (green for inflow, red for outflow), and interpretation
