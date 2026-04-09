"""Stock trend analysis agent using DeepAgent with Tavily search."""
import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from backend.services.tavily_search_tool import tavily_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def _get_model():
    """Initialize the MiniMax ChatOpenAI model."""
    return ChatOpenAI(
        model="MiniMax-M2.7",
        openai_api_key=os.environ.get("MINIMAX_API_KEY"),
        openai_api_base="https://api.minimax.chat/v1",
        temperature=0,
    )


SYSTEM_PROMPT = """You are a professional stock analyst agent. Your task is to analyze a given stock and predict its price trend for the next 2 weeks based on recent news and macro environment.

## Your Process

1. **Search for stock-specific news**: Use the tavily_search tool to search for recent news about the specific stock (symbol and name).
   - Search query format: "[stock name] [stock symbol] recent news"
   - Use topic="finance" for relevant financial news

2. **Search for macro environment**: Use the tavily_search tool to search for macro factors that might affect the stock:
   - Interest rate trends
   - GDP and economic data
   - Industry-specific trends
   - Market sentiment

3. **Analyze and make prediction**: Based on the search results, analyze:
   - Overall sentiment (positive, negative, neutral)
   - Key factors driving the stock
   - Macro environment support or headwinds

4. **Return prediction**: Provide your final prediction with:
   - trend_direction: "up", "down", or "neutral"
   - confidence: 0-100 percentage based on news quality and consistency
   - summary: Brief explanation of the analysis reasoning

## Important Guidelines

- **Focus on the LATEST news**: The tavily_search returns news from the current week. Prioritize the most recent articles in your analysis as they are most relevant for 2-week trend prediction
- If you find limited or no news, note this in your summary and provide lower confidence
- Consider both company-specific news and broader market/industry trends
- Base your prediction primarily on the latest news and macro factors found
- Provide honest, balanced analysis - don't overstate confidence if evidence is weak

## Response Format

Your final response should be a JSON object with these fields:
{
    "trend_direction": "up" or "down" or "neutral",
    "confidence": 0-100,
    "summary": "Your analysis explanation in Chinese"
}
"""


def create_stock_trend_agent():
    """Create a DeepAgent for stock trend analysis with Tavily search tool."""
    model = _get_model()

    agent = create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[tavily_search],
    )

    return agent


def analyze_stock_trend(symbol: str, name: str) -> Dict[str, Any]:
    """Analyze stock trend using DeepAgent with Tavily search.

    Args:
        symbol: Stock symbol (e.g., "000001")
        name: Stock name (e.g., "平安银行")

    Returns:
        Dictionary containing trend_direction, confidence, and summary
    """
    logger.info(f"Starting trend analysis for {name} ({symbol})")
    agent = create_stock_trend_agent()
    logger.info(f"Agent created for {symbol}, invoking...")

    user_message = f"""请分析股票 {name} ({symbol}) 的未来2周趋势。

请使用 tavily_search 工具搜索：
1. 关于 {name} ({symbol}) 的最新新闻
2. 相关的宏观经济和行业信息

然后基于搜索结果，给出你的预测。
"""

    try:
        logger.info(f"Invoking agent for {symbol}...")
        result = agent.invoke({
            "messages": [{"role": "user", "content": user_message}]
        })
        logger.info(f"Agent invocation complete for {symbol}")

        messages = result.get("messages", [])
        if not messages:
            return {
                "symbol": symbol,
                "name": name,
                "trend_direction": "neutral",
                "confidence": 0,
                "summary": "分析失败：无法获取响应",
            }

        # Get the final response
        final_msg = messages[-1]
        content = final_msg.content

        # Try to parse as JSON
        import json
        import re

        # Look for JSON in the response
        json_match = re.search(r'\{[^}]*"trend_direction"[^}]*\}', content, re.DOTALL)
        if json_match:
            try:
                prediction = json.loads(json_match.group())
                return {
                    "symbol": symbol,
                    "name": name,
                    "trend_direction": prediction.get("trend_direction", "neutral"),
                    "confidence": prediction.get("confidence", 0),
                    "summary": prediction.get("summary", content[:500]),
                }
            except json.JSONDecodeError:
                pass

        # If JSON parsing fails, return the content as summary
        return {
            "symbol": symbol,
            "name": name,
            "trend_direction": "neutral",
            "confidence": 0,
            "summary": content[:500] if content else "无法解析分析结果",
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "name": name,
            "trend_direction": "neutral",
            "confidence": 0,
            "summary": f"分析错误: {str(e)}",
        }
