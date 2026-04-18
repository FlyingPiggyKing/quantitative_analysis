## Why

Currently, the stock trend analysis relies solely on Tavily for web search. If Tavily is unavailable or rate-limited, the agent cannot gather recent news for sentiment analysis, reducing prediction quality. MiniMax offers an MCP server with web search capabilities that can serve as a fallback, ensuring continuous service availability.

## What Changes

- Add MiniMax MCP web search as secondary/fallback search tool
- Tavily remains primary search; MiniMax MCP activates when Tavily is unavailable
- Both search tools accessible within the stock trend analysis process
- Create a unified search interface that attempts Tavily first, falls back to MiniMax MCP

## Capabilities

### New Capabilities
- `minimax-mcp-search`: MiniMax MCP-based web search tool that wraps the `minimax-coding-plan-mcp` local server. Provides finance-relevant web search when Tavily is unavailable. The MCP server runs as a local subprocess via `uvx`.

### Modified Capabilities
- `stock-trend-analysis-agent`: Update to use a fallback search strategy. When Tavily search fails or returns no results, the agent SHALL attempt MiniMax MCP search as a secondary source. This ensures news retrieval continues even when Tavily is unavailable.

## Impact

- **New file**: `backend/services/minimax_mcp_search_tool.py` - MCP client wrapper for MiniMax search
- **Modified file**: `backend/services/stock_trend_agent.py` - Updated to use fallback search strategy
- **New dependency**: `minimax-coding-plan-mcp` package (installed via `uvx`)
- **Environment variable**: `MINIMAX_API_KEY` already exists; no new secrets needed
