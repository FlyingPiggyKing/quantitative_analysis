## Why

When users click "运行分析" (Run Analysis), the backend processes stock trend analysis synchronously, blocking the FastAPI event loop. This causes the frontend page to hang until all analysis completes (potentially minutes for multiple stocks), creating a poor user experience. The analysis should run in the background so users can continue interacting with the page.

## What Changes

- Convert trend analysis from synchronous blocking execution to background task execution
- Add a task queue with dedicated worker thread for analysis jobs
- Return immediately with a task ID after queuing, allowing frontend to poll for status
- Store analysis results in database upon completion for retrieval
- Update frontend to handle async analysis with progress indication

## Capabilities

### New Capabilities

- `background-analysis-task`: Background task queue for trend analysis jobs
  - Accept analysis requests and return immediately with task ID
  - Process analysis in dedicated worker thread (non-blocking)
  - Support polling task status and retrieving results
  - Handle concurrent analysis requests without blocking

### Modified Capabilities

- `stock-trend-analysis-agent`: No requirement changes — only implementation changes to support async invocation

## Impact

- **Backend**: New task queue module, modifications to `trend_prediction.py` API endpoints
- **Frontend**: Update to handle async analysis with task polling
- **Database**: May need task status table for tracking analysis jobs
- **Dependencies**: Need thread pool or task queue library (e.g., `concurrent.futures`, `celery`, or custom queue)
