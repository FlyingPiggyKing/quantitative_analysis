## 1. Frontend - Remove Auto-Fetch

- [x] 1.1 Remove the auto-fetch useEffect for trend prediction on stock detail page load

## 2. Frontend - Add Force Analysis Button

- [x] 2.1 Add `runForcedSingleAnalysis` function to trendPrediction service that calls `GET /api/trend-predictions/{symbol}?force=true`
- [x] 2.2 Modify Trend Analysis section to always display "立刻分析" button (remove `!trendPrediction && !trendLoading` condition)
- [x] 2.3 Update button click handler to call `runForcedSingleAnalysis` instead of `runBatchAnalysisAsync`
- [x] 2.4 Update button to show loading state and disable during analysis
- [x] 2.5 Remove task ID storage in localStorage (batch queue tracking not needed for single stock)

## 3. Frontend - Update Loading and Error States

- [x] 3.1 Show loading spinner in trend section when analysis is running
- [x] 3.2 Handle and display error message if analysis fails
- [x] 3.3 Update button text to "分析中..." when running
