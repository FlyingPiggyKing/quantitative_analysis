## 1. Backend Task Queue Infrastructure

- [x] 1.1 Create `backend/services/task_queue.py` with ThreadPoolExecutor
- [x] 1.2 Implement TaskStatus enum (pending, running, completed, failed)
- [x] 1.3 Create in-memory task registry dict with threading.Lock
- [x] 1.4 Add task submission function `submit_analysis_task(stocks)`
- [x] 1.5 Add task status retrieval function `get_task_status(task_id)`
- [x] 1.6 Implement background worker that executes `analyze_stock_trend` for queued tasks

## 2. New API Endpoints

- [x] 2.1 Add `POST /api/trend-predictions/batch-async` endpoint
- [x] 2.2 Add `GET /api/trend-predictions/task/{task_id}` endpoint
- [x] 2.3 Return immediately from batch-async with task_id (non-blocking)
- [x] 2.4 Wire endpoints to task queue functions

## 3. Frontend Integration

- [x] 3.1 Update frontend service `trendPrediction.ts` to support async batch analysis
- [x] 3.2 Add polling logic to check task status every 2 seconds
- [x] 3.3 Update "运行分析" button handler to use new async endpoint
- [x] 3.4 Show progress indicator while task is running
- [x] 3.5 Display results once task completes

## 4. Testing & Verification

- [x] 4.1 Test that clicking "运行分析" no longer blocks the page
- [x] 4.2 Verify multiple stocks are still analyzed correctly
- [x] 4.3 Test task status polling endpoint
- [x] 4.4 Verify analysis results are stored in database correctly
