## Context

The index page currently exhibits an N+1 query problem. When loading the watchlist or preset stock list:

1. `WatchList.tsx` fetches the watchlist (1 request), then iterates over each stock making individual `/api/stock/{symbol}/valuation` requests (N requests)
2. `PresetStockList.tsx` makes 2 parallel requests per stock (info + valuation), resulting in 2N requests

The logs show loading 4 preset stocks requires 8+ sequential/parallel requests. This causes:
- Slow page loads due to network round-trip overhead
- Excessive Tushare API calls (rate limiting risk)
- Poor user experience

**Current architecture:**
```
Frontend → GET /api/watchlist (1 request)
Frontend → For each stock: GET /api/stock/{symbol}/valuation (N requests)
```

**Target architecture:**
```
Frontend → GET /api/stock/batch/valuation?symbols=600938,601899,... (1 request)
Frontend → GET /api/stock/batch/info?symbols=600938,601899,... (1 request, optional)
```

## Goals / Non-Goals

**Goals:**
- Reduce index page load from N+1 requests to 1-2 batch requests
- Single SQL-like query to fetch all required data
- Maintain backward compatibility with existing single-symbol endpoints
- Minimize changes to existing frontend components

**Non-Goals:**
- Not redesigning the entire data layer
- Not adding a full ORM or query builder
- Not implementing real-time WebSocket updates
- Not adding complex caching layer (can be future enhancement)

## Decisions

### Decision 1: Batch API Endpoint Design

**Chosen approach:** New `/api/stock/batch/valuation` and `/api/stock/batch/info` endpoints accepting comma-separated or JSON array of symbols.

**Alternatives considered:**
- **Query string array**: `?symbols=600938&symbols=601899` - More natural HTTP, but harder to construct on frontend
- **JSON POST body**: More flexible but changes HTTP semantics (GET → POST)
- **Path parameter with multiple symbols**: `GET /api/stock/valuation/batch/{symbols}` - RESTful but URL encoding issues

**Rationale:** Query parameter with comma-separated string is simplest for frontend, maintains GET semantics, and matches existing patterns.

### Decision 2: Backend Batch Implementation

**Chosen approach:** Modify `AkshareService.get_daily_basic()` to accept list of symbols and use Tushare batch query API `daily_basic` with multiple ts_codes.

**Alternatives considered:**
- **Loop existing single-symbol method**: Simple but N API calls still happen (just in backend)
- **Tushare batch API**: Single API call with multiple ts_codes - most efficient

**Rationale:** Tushare's `daily_basic` API accepts `ts_code` parameter that can be comma-separated (e.g., `000001.SZ,600938.SH`). Using this batch capability eliminates N calls to Tushare as well.

### Decision 3: Frontend Changes

**Chosen approach:** Modify both `WatchList.tsx` and `PresetStockList.tsx` to:
1. Fetch stock list (watchlist or preset)
2. Call batch valuation API once with all symbols
3. Map results back to stock items

**Alternatives considered:**
- **Create shared batch fetch utility**: More reusable but adds indirection
- **Modify in each component**: Simpler, less abstraction, matches existing code style

**Rationale:** Given the codebase size, direct modification is simpler. Shared utility can be extracted later if needed.

### Decision 4: Response Format

**Chosen approach:** Return dict with `results` array containing per-stock data, and `errors` array for failed symbols.

```json
{
  "results": [
    {"symbol": "600938", "data": [...], "latest": {...}},
    {"symbol": "601899", "data": [...], "latest": {...}}
  ],
  "errors": []
}
```

**Rationale:** Allows partial success (some stocks fail, others succeed), matches existing single-stock response structure.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Tushare batch API has size limits | Limit batch size to 50 symbols per request |
| Single batch failure affects all | Return partial results with error array |
| Frontend change breaks existing functionality | Maintain single-symbol endpoints unchanged |
| Increased response size | Compression (gzip) handles this; caching future work |

## Open Questions

1. **Should we cache valuation data in database?** Currently every request hits Tushare. Could add SQLite caching with TTL.
2. **What's the maximum batch size?** Need to determine practical limit based on Tushare API constraints.
3. **Should we add loading states?** With batch requests, loading UX may differ - show skeleton vs. progressive loading.
