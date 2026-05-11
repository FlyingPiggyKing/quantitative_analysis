## 1. Backend: Add single-stock task submission to task queue

- [x] 1.1 Add `submit_single_analysis_task()` to `backend/services/task_queue.py` — similar to `submit_analysis_task()` but for single stock with symbol/name
- [x] 1.2 Add `POST /api/trend-predictions/{symbol}/force-async` endpoint to route `force=true` requests to task queue
- [x] 1.3 Return `{task_id, status: "pending"}` immediately when submitting to queue
- [x] 1.4 Ensure task stores result in DB on completion (reuse existing `TrendPredictionService.save_prediction`)
- [x] 1.5 Pass `user_id` to `_run_single_analysis()` and call `record_trigger` only on success

## 2. Frontend: Update service to handle async response

- [x] 2.1 Add `runForcedSingleAnalysisAsync()` in `frontend/src/services/trendPrediction.ts` to call new async endpoint
- [x] 2.2 Return task_id response to caller

## 3. Frontend: Update stock detail page to handle async flow

- [x] 3.1 Modify `handleRunAnalysis()` in `frontend/src/app/stock/[symbol]/page.tsx` to use async endpoint and start polling
- [x] 3.2 Update UI to show loading state during polling
- [x] 3.3 Display results when task completes
- [x] 3.4 Handle errors from failed tasks
- [x] 3.5 Set cooldown immediately on button click (not after task completion)
- [x] 3.6 Clear cooldown only on non-429 errors; keep on 429 rate limit
