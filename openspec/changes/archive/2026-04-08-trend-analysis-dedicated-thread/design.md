## Context

The current trend analysis implementation in `backend/api/trend_prediction.py` processes `batch_analyze()` synchronously. When a user clicks "运行分析", the FastAPI endpoint blocks until all stocks are analyzed sequentially (each stock takes several seconds due to API calls and `time.sleep(1)`). This blocks the event loop, freezing the frontend.

The system consists of:
- **Frontend**: React Next.js page calling `POST /api/trend-predictions/batch`
- **Backend API**: FastAPI with `analyze_stock_trend()` in `stock_trend_agent.py`
- **Agent**: DeepAgent invoking Tavily search synchronously

## Goals / Non-Goals

**Goals:**
- Enable non-blocking trend analysis execution
- Return task ID immediately upon queuing
- Support task status polling and result retrieval
- Process multiple analysis requests concurrently without blocking

**Non-Goals:**
- Distributed task queue across multiple servers (single-instance is sufficient)
- Real-time WebSocket progress updates (polling is acceptable)
- Replacing existing analysis logic — only changing execution model

## Decisions

### Decision 1: ThreadPoolExecutor over Celery/Redis

**Choice**: Use `concurrent.futures.ThreadPoolExecutor` for background execution

**Rationale**:
- No additional infrastructure (Redis) needed
- Simple to implement and maintain
- Sufficient for I/O-bound analysis tasks (network calls to Tavily)
- FastAPI supports async route handlers that can submit to thread pool

**Alternatives**:
- **Celery + Redis**: Overkill for single-instance, adds operational complexity
- **asyncio.create_task()**: Still blocks if sync functions are called; ThreadPoolExecutor is cleaner for sync-to-async bridge
- **Background threads manually managed**: More error-prone than ThreadPoolExecutor

### Decision 2: In-Memory Task Status Storage

**Choice**: Use a dict/task registry with task states (pending/running/completed/failed)

**Rationale**:
- Analysis tasks are short-lived and single-server
- Database already exists (`trend_predictions.db`) — could persist tasks there
- Keep it simple: in-memory with optional persistence

**Alternatives**:
- **Database-backed tasks**: More robust but adds complexity; can be added later if needed
- **Celery task store**: Would require Celery setup

### Decision 3: Polling-based Status Retrieval

**Choice**: `GET /api/trend-predictions/task/{task_id}` endpoint for status polling

**Rationale**:
- Simple HTTP polling — frontend already knows how to do this
- No WebSocket infrastructure needed
- Status includes progress (e.g., "3/10 stocks analyzed")

**Alternatives**:
- **WebSocket**: More complex, requires frontend changes; polling is sufficient

### Decision 4: Preserve Existing API Contract

**Choice**: Add new endpoints alongside existing ones, don't break existing `/batch` usage

**Rationale**:
- Existing `/batch` can optionally be updated to queue instead of wait
- Frontend can migrate gradually to new async endpoints
- Backward compatible

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Thread pool exhaustion if many users trigger analysis simultaneously | Limit pool size (e.g., max 5 concurrent tasks), queue excess requests |
| Task results lost if server restarts mid-analysis | On restart, tasks in-progress are lost; acceptable for non-critical analysis |
| Memory usage with many pending tasks | Set reasonable timeout, auto-fail stale tasks |
| DeepAgent thread safety | DeepAgent.invoke() is assumed thread-safe; if not, add locking |
