"""MiniMax MCP search tool for DeepAgent - fallback when Tavily is unavailable."""
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

# Configure logging
logger = logging.getLogger(__name__)

# Load .env before initializing
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

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
                    "LANGCHAIN_TRACING": "false",
                    "LANGSMITH_TRACING": "false",
                }
            }
        })
    return _mcp_client


def _search_sync(query: str, max_results: int = 5, time_range: str = "month", retry_count: int = 2) -> str:
    """Synchronous wrapper for MCP search with time range filtering.

    Args:
        query: Search query
        max_results: Maximum results to return
        time_range: Time range filter ("day", "week", "month", "year")
        retry_count: Number of times to retry on failure (default 2)
    """
    last_error = None
    for attempt in range(retry_count + 1):
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

            # Parse and filter results by date
            result_str = str(result)
            filtered_results = _filter_by_time_range(result_str, time_range)
            return filtered_results

        except concurrent.futures.TimeoutError:
            last_error = "Search error: Timeout communicating with MCP server"
            logger.warning(f"MCP timeout on attempt {attempt + 1}, retrying...")
        except Exception as e:
            last_error = f"Search error: {str(e)}"
            logger.warning(f"MCP error on attempt {attempt + 1}: {type(e).__name__}: {e}")
            import traceback
            logger.warning(f"Stack trace: {traceback.format_exc()}")

        # If failed, reset the client so next attempt creates fresh one
        if attempt < retry_count:
            global _mcp_client
            _mcp_client = None
            logger.info("Resetting MCP client for retry...")

    return last_error


def _filter_by_time_range(results: str, time_range: str) -> str:
    """Filter search results by publication date based on time_range.

    Args:
        results: Raw search results string (JSON from MCP or plain text)
        time_range: "day", "week", "month", or "year"

    Returns:
        Filtered results string containing only articles within the time range
    """
    # Calculate cutoff date
    now = datetime.now()
    if time_range == "day":
        cutoff = now - timedelta(days=1)
    elif time_range == "week":
        cutoff = now - timedelta(weeks=1)
    elif time_range == "month":
        cutoff = now - timedelta(days=30)
    elif time_range == "year":
        cutoff = now - timedelta(days=365)
    else:
        cutoff = now - timedelta(days=30)  # default to month

    try:
        # MCP returns Python list notation with single quotes, not JSON
        # Use ast.literal_eval to parse it
        import ast
        data = ast.literal_eval(results)
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
            if isinstance(item, dict) and 'text' in item:
                inner_text = item['text']
                # Parse the inner JSON (which IS proper JSON)
                inner_data = json.loads(inner_text)
                organic = inner_data.get('organic', [])

                # Filter entries by date
                filtered_organic = []
                for entry in organic:
                    date_str = entry.get('date', '')
                    if date_str:
                        try:
                            entry_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                            if entry_date >= cutoff:
                                filtered_organic.append(entry)
                        except ValueError:
                            filtered_organic.append(entry)
                    else:
                        filtered_organic.append(entry)

                # Reconstruct and wrap back
                inner_data['organic'] = filtered_organic
                item['text'] = json.dumps(inner_data, ensure_ascii=False)
                return json.dumps([item], ensure_ascii=False)

        return results

    except Exception as e:
        logger.warning(f"Date filtering error: {e}")
        return results


@tool(parse_docstring=True)
def minimax_mcp_search(
    query: str,
    max_results: int = 5,
    time_range: Literal["day", "week", "month", "year"] = "month",
) -> str:
    """Search the web using MiniMax MCP server (fallback when Tavily unavailable).

    This tool invokes the MiniMax MCP server via stdio to perform web search.
    Use this as a fallback when Tavily search is unavailable or returns no results.
    Results are filtered to the specified time range.

    Args:
        query: The search query to look up
        max_results: Maximum number of results to return (default: 5)
        time_range: Time range for results - "day", "week", "month", or "year" (default: "month")
    """
    if not os.environ.get("MINIMAX_API_KEY"):
        return "Search error: MINIMAX_API_KEY not configured"

    return _search_sync(query, max_results, time_range)
