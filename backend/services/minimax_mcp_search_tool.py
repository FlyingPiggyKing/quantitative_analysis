"""MiniMax MCP search tool for DeepAgent - fallback when Tavily is unavailable."""
import os
import json
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

# Load .env before initializing
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Global client instance
_mcp_client: Optional[MultiServerMCPClient] = None


def _get_mcp_client() -> MultiServerMCPClient:
    """Get or create the MCP client singleton."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MultiServerMCPClient({
            "minimax": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["minimax-coding-plan-mcp", "-y"],
                "env": {
                    "MINIMAX_API_KEY": os.environ.get("MINIMAX_API_KEY", ""),
                    "MINIMAX_API_HOST": os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com"),
                }
            }
        })
    return _mcp_client


def _search_sync(query: str, max_results: int = 5) -> str:
    """Synchronous wrapper for MCP search."""
    try:
        client = _get_mcp_client()

        # Get tools synchronously using run_in_executor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            tools_future = executor.submit(asyncio.run, client.get_tools())
            tools = tools_future.result(timeout=60)

        # Find the search tool
        search_tool = None
        for t in tools:
            name = getattr(t, 'name', '') or ''
            if 'search' in name.lower() or 'web' in name.lower():
                search_tool = t
                break

        if not search_tool and tools:
            search_tool = tools[0]

        if not search_tool:
            return "Search error: No search tool found on MCP server"

        # Invoke the tool using ainvoke (async)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result_future = executor.submit(asyncio.run, search_tool.ainvoke({"query": query, "max_results": max_results}))
            result = result_future.result(timeout=60)

        return str(result)

    except concurrent.futures.TimeoutError:
        return "Search error: Timeout communicating with MCP server"
    except Exception as e:
        return f"Search error: {str(e)}"


@tool(parse_docstring=True)
def minimax_mcp_search(
    query: str,
    max_results: int = 5,
) -> str:
    """Search the web using MiniMax MCP server (fallback when Tavily unavailable).

    This tool invokes the MiniMax MCP server via stdio to perform web search.
    Use this as a fallback when Tavily search is unavailable or returns no results.

    Args:
        query: The search query to look up
        max_results: Maximum number of results to return (default: 5)
    """
    if not os.environ.get("MINIMAX_API_KEY"):
        return "Search error: MINIMAX_API_KEY not configured"

    return _search_sync(query, max_results)
