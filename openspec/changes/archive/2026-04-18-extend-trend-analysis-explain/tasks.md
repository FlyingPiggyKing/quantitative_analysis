## 1. Modify Agent System Prompt

- [x] 1.1 Update SYSTEM_PROMPT in `backend/services/stock_trend_agent.py` to output structured JSON with three sections (情绪分析, 技术分析, 趋势判断)
- [x] 1.2 Update the JSON parsing logic in `analyze_stock_trend()` to handle the new structured response
- [x] 1.3 Add fallback logic: if structured JSON parsing fails, fall back to original trend_direction/confidence/summary fields

## 2. Update Backend API Response

- [x] 2.1 Extend `TrendPredictionService` to store and return extended analysis fields
- [x] 2.2 Update `backend/api/trend_prediction.py` to return the full structured response
- [x] 2.3 Ensure backward compatibility: existing API consumers should still get trend_direction, confidence, summary

## 3. Update Frontend Type Definitions

- [x] 3.1 Extend `TrendPrediction` interface in `frontend/src/services/trendPrediction.ts` to include new fields (情绪分析, 技术分析, 趋势判断)
- [x] 3.2 Update frontend components that display trend analysis to render the new structured content

## 4. Testing

- [ ] 4.1 Test agent output parsing with various response formats
- [ ] 4.2 Verify fallback logic works when structured parsing fails
- [ ] 4.3 Test frontend rendering of extended analysis fields
