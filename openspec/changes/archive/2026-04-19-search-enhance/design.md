## Context

Currently the trend analysis news search uses Tavily as primary provider with MiniMax MCP as fallback. User feedback indicates Tavily often returns stale news, and they want MiniMax MCP promoted to primary. Additionally, there's no time range control on MiniMax MCP search.

**Current search chain** (`stock_trend_agent.py:search_with_fallback`):
1. Tavily (primary) with `time_range="week"` default
2. MiniMax MCP (fallback) - no time filtering

## Goals / Non-Goals

**Goals:**
- Prioritize MiniMax MCP search over Tavily
- Add time_range filtering to MiniMax MCP search (default to "month" for recent news)
- Ensure Tavily explicitly uses `time_range="month"` to match MiniMax MCP
- Limit news results to last 30 days

**Non-Goals:**
- Remove Tavily - it remains as fallback
- Change MiniMax MCP server implementation itself - only add time_range parameter

## Decisions

### 1. Swap search priority order

**Decision**: Try MiniMax MCP first, then fallback to Tavily.

**Rationale**: MiniMax MCP tends to return fresher news. Tavily's native time filtering is less reliable per user feedback.

**Alternatives**:
- Keep Tavily primary but filter results post-search by date → Rejected: adds complexity, harder to validate
- Add a third search provider → Out of scope

### 2. Add time_range parameter to MiniMax MCP search

**Decision**: Add optional `time_range` parameter to `minimax_mcp_search()` function.

**Rationale**: MiniMax MCP doesn't natively support time filtering. We can pass date range hints in the query or post-filter results by publication date.

**Implementation approach**: Wrap MiniMax MCP results and filter by `pub_date >= 30 days ago`.

### 3. Tavily explicit time_range="month"

**Decision**: Set Tavily `time_range="month"` explicitly (currently it defaults to "week").

**Rationale**: User wants news from last 30 days. "month" aligns with MiniMax MCP filtering.

## Risks / Trade-offs

[Risk] MiniMax MCP may return fewer results than Tavily
→ Mitigation: Tavily fallback ensures results are still obtained

[Risk] Date filtering may be too aggressive and filter out valid recent news
→ Mitigation: Default to "month" (30 days) which is a reasonable window for stock news

[Risk] MiniMax MCP server startup overhead when used as primary
→ Mitigation: Acceptable trade-off for fresher results; MiniMax MCP has fast startup
