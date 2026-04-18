## Context

The stock trend analysis agent (`stock_trend_agent.py`) currently uses Tavily as its sole web search provider for gathering news sentiment. Tavily is configured via `TAVILY_API_KEY` and accessed through the `tavily_search` tool.

When Tavily is unavailable (rate limiting, API issues, or missing API key), the agent cannot retrieve recent news, degrading prediction quality. The MiniMax MCP server (`minimax-coding-plan-mcp`) provides an alternative web search via local command execution.

**Current Architecture:**
```
Stock Trend Agent → tavily_search tool → Tavily API
```

**Proposed Architecture:**
```
Stock Trend Agent → search_with_fallback() → Tavily (primary)
                                          → MiniMax MCP (fallback)
```

## Goals / Non-Goals

**Goals:**
- Provide reliable web search for stock trend analysis even when Tavily fails
- Integrate MiniMax MCP as a secondary search tool using LangChain tool interface
- Minimize code changes to existing Tavily integration

**Non-Goals:**
- Replacing Tavily as primary search (MiniMax MCP is fallback only)
- Supporting MiniMax MCP for other use cases beyond search
- Modifying the DeepAgent framework itself

## Decisions

### Decision 1: Stdio MCP Server Integration with LangChain

**Choice:** Create a custom tool wrapper (`minimax_mcp_search`) that invokes the MCP server via subprocess and implements the MCP JSON-RPC protocol over stdio.

**Rationale:** LangChain's built-in `tools.mcp()` supports only HTTP/SSE transport (`serverUrl` parameter). MiniMax MCP uses stdio transport (`command` array). Creating a custom tool wrapper allows integration without modifying LangChain internals.

**Alternatives Considered:**
- **LangChain MCP HTTP wrapper**: Would require wrapping stdio MCP in an HTTP server (adds complexity, latency)
- **Direct HTTP API access**: MiniMax doesn't provide direct REST API for search without MCP

### Decision 2: Fallback Search Strategy

**Choice:** Implement `search_with_fallback()` function that attempts Tavily first, then MiniMax MCP if Tavily returns empty/error.

**Rationale:** Maintains Tavily as primary (better finance-focused results), only uses fallback when needed. Keeps the fallback logic transparent to the agent - the agent just calls a search function.

```python
def search_with_fallback(query: str) -> str:
    """Try Tavily first, fall back to MiniMax MCP on failure."""
    tavily_result = tavily_search(query)
    if tavily_result and "error" not in tavily_result.lower():
        return tavily_result
    # Fallback to MiniMax MCP
    return minimax_mcp_search(query)
```

### Decision 3: MCP Tool Design

**Choice:** `minimax_mcp_search` tool accepts `query` string and returns formatted search results.

**Rationale:** Mirrors `tavily_search` interface for consistent fallback logic. The MCP server's internal tool name (likely `web_search` or similar) is abstracted away.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| MCP stdio communication is synchronous/blocking | Use `subprocess.run()` with timeout; MCP calls won't hang indefinitely |
| MiniMax MCP output format differs from Tavily | Normalize output in wrapper to match Tavily format |
| MCP server startup overhead | MCP server stays running; `uvx` caches packages |
| MiniMax MCP may lack finance-specific search | Falls back only; Tavily remains primary for finance content |

## Technical Approach

**New file:** `backend/services/minimax_mcp_search_tool.py`

```python
@tool(parse_docstring=True)
def minimax_mcp_search(query: str, max_results: int = 5) -> str:
    """Search web using MiniMax MCP server (fallback when Tavily unavailable)."""
    # 1. Set environment (MINIMAX_API_KEY from os.environ)
    # 2. Spawn subprocess: uvx minimax-coding-plan-mcp -y
    # 3. Send JSON-RPC request via stdin for tool call
    # 4. Read JSON-RPC response via stdout
    # 5. Parse and format results
```

**Modified file:** `backend/services/stock_trend_agent.py`
- Update `SYSTEM_PROMPT` to mention fallback capability
- Update `analyze_stock_trend()` to handle search failures gracefully

**Fallback Logic:**
- Tavily returns error → try MiniMax MCP
- Tavily returns empty results → try MiniMax MCP
- MiniMax MCP also fails → return "Insufficient data" with low confidence
