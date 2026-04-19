## 1. Update Search Fallback Chain

- [x] 1.1 Reverse priority in `search_with_fallback` - try MiniMax MCP first, then Tavily fallback
- [x] 1.2 Add `time_range` parameter to `search_with_fallback` and pass it to both providers

## 2. Add Time Range Support to MiniMax MCP Search

- [x] 2.1 Add `time_range` parameter to `minimax_mcp_search()` function
- [x] 2.2 Implement date filtering in `_search_sync()` to filter results by publication date (last 30 days)

## 3. Update Tavily Search Call

- [x] 3.1 Update `search_with_fallback` to pass `time_range="month"` explicitly to Tavily

## 4. Update System Prompt

- [x] 4.1 Update SYSTEM_PROMPT comment to reflect new search priority order
