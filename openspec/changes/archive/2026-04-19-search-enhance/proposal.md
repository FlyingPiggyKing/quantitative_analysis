## Why

The current trend analysis news search uses Tavily as the primary source with MiniMax MCP as fallback. Users report that Tavily often returns stale news articles, and we want to prioritize fresher results. Additionally, MiniMax MCP should be promoted to primary search provider.

## What Changes

- **Swap search priority**: Use MiniMax MCP as the primary search provider, with Tavily as fallback
- **Add time range control**: Implement a `time_range` parameter for MiniMax MCP search (default to `"month"` for recent news)
- **Tavily improvement**: Set Tavily `time_range` to `"month"` explicitly to filter for recent news
- **Result freshness validation**: Ensure news results are from the last 30 days

## Capabilities

### New Capabilities
- `search-fallback-chain`: Reorders the search fallback chain to prioritize MiniMax MCP over Tavily

### Modified Capabilities
- `minimax-mcp-search`: Add time_range parameter support (MiniMax MCP currently lacks date filtering)
- `stock-trend-analysis-agent`: Update the `search_with_fallback` logic to use new priority order and pass time_range to both providers

## Impact

- **Backend**: `stock_trend_agent.py` - reorder fallback logic, add time_range to MiniMax calls
- **Backend**: `minimax_mcp_search_tool.py` - add optional time_range parameter
- **Backend**: `tavily_search_tool.py` - explicit time_range="month" in agent calls
