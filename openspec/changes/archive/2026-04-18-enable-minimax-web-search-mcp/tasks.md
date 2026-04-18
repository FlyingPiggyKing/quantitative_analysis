## 1. Create MiniMax MCP Search Tool

- [x] 1.1 Create `backend/services/minimax_mcp_search_tool.py`
- [x] 1.2 Implement MCP stdio communication using subprocess
- [x] 1.3 Implement `minimax_mcp_search` function with query and max_results parameters
- [x] 1.4 Add timeout handling (30 second limit)
- [x] 1.5 Add error handling for MCP server failures
- [x] 1.6 Format output to match Tavily's output format
- [ ] 1.7 Test MiniMax MCP tool standalone with a simple query

## 2. Integrate Fallback Search in Stock Trend Agent

- [x] 2.1 Update `backend/services/stock_trend_agent.py` imports to include `minimax_mcp_search`
- [x] 2.2 Create `search_with_fallback()` helper function that tries Tavily first, MiniMax MCP on failure
- [x] 2.3 Update SYSTEM_PROMPT to document fallback capability
- [x] 2.4 Update `analyze_stock_trend()` to use `search_with_fallback()` instead of direct `tavily_search`
- [ ] 2.5 Test stock trend analysis with fallback when Tavily is unavailable

## 3. Verify and Validate

- [ ] 3.1 Verify both Tavily and MiniMax MCP search work in the agent
- [ ] 3.2 Test fallback behavior by temporarily disabling Tavily
- [ ] 3.3 Ensure existing Tavily-only functionality still works
