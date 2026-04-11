## 1. Frontend - Add Trend Analysis Button to Homepage

- [x] 1.1 Import `runBatchAnalysisAsync` from `@/services/trendPrediction` in `page.tsx`
- [x] 1.2 Add `isAnalyzing` state derived from `activeTaskId && taskProgress?.status === "pending" || taskProgress?.status === "running"`
- [x] 1.3 Add "趋势分析" button below the search form, above the watchlist
- [x] 1.4 Implement button disabled state styling (opacity-50, cursor-not-allowed)
- [x] 1.5 Implement `handleTrendAnalysis` async function that calls `runBatchAnalysisAsync()`

## 2. Frontend - Button State Management

- [x] 2.1 When `runBatchAnalysisAsync()` succeeds, update `activeTaskId` with returned `task_id`
- [x] 2.2 Button shows "分析中..." (analyzing) when `isAnalyzing` is true
- [x] 2.3 Button shows "趋势分析" when analysis is not running
- [x] 2.4 Verify button disables when task is pending/running and enables when completed/failed

## 3. Integration Testing

- [ ] 3.1 Verify button is disabled after clicking and enabled after analysis completes
- [ ] 3.2 Verify progress bar appears after clicking the button
- [ ] 3.3 Verify user isolation - logout/login with different user shows enabled button
