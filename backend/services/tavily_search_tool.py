"""Tavily search tool for DeepAgent."""
import os
from typing import Literal
from tavily import TavilyClient
from langchain.tools import tool

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))


@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "finance",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to search for relevant URLs and content.
    Set topic to "finance" for financial news and stock-related searches.

    Args:
        query: The search query to look up
        max_results: Maximum number of results to return (default: 5)
        topic: Search topic category - "general", "news", or "finance" (default: "finance")
    """
    if not os.environ.get("TAVILY_API_KEY"):
        return "Error: TAVILY_API_KEY not configured"

    try:
        results = tavily_client.search(
            query,
            max_results=max_results,
            topic=topic,
            include_raw_content=False,
        )

        # Format results into a readable string
        output = []
        for i, result in enumerate(results.get("results", []), 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")[:300]  # Truncate content

            output.append(f"{i}. {title}")
            output.append(f"   URL: {url}")
            output.append(f"   Content: {content}...")
            output.append("")

        if not output:
            return "No search results found."

        return "\n".join(output)
    except Exception as e:
        return f"Search error: {str(e)}"
