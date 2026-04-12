"""Stock trend analysis agent using DeepAgent with Tavily search."""
import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from backend.services.tavily_search_tool import tavily_search
from backend.services.akshare_service import AkshareService

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


SYSTEM_PROMPT = """You are a professional stock analyst agent. Your task is to analyze a given stock and predict its price trend for the next 2 weeks based on BOTH technical data AND recent news.

## Your Process

1. **Analyze the provided technical data**: Review the K-line data, MACD, RSI, and MA signals provided in the message.
   - Price trend direction and magnitude
   - MACD golden/death cross signals
   - RSI zone (overbought >80, oversold <20)
   - Price position relative to moving averages
   - Volume ratio (above 1 = volume expansion)

2. **Search for stock-specific news**: Use the tavily_search tool to search for recent news about the specific stock (symbol and name).
   - Search query format: "[stock name] [stock symbol] recent news"
   - Use topic="finance" for relevant financial news

3. **Search for macro environment**: Use the tavily_search tool to search for macro factors that might affect the stock:
   - Interest rate trends
   - GDP and economic data
   - Industry-specific trends
   - Market sentiment

4. **Combine technical + sentiment analysis**: Weight technical signals (40%) and news sentiment (60%) to form your prediction.
   - If technical signals confirm news direction → higher confidence
   - If technical signals conflict with news direction → lower confidence and note the disagreement

5. **Return prediction**: Provide your final prediction with:
   - trend_direction: "up", "down", or "neutral"
   - confidence: 0-100 percentage based on combined analysis quality
   - summary: Brief explanation of the analysis reasoning

## Important Guidelines

- **Use the provided technical data first**: The technical data is provided under "## 技术数据" section. Analyze it BEFORE searching for news.
- **Weight: 40% technical, 60% news**: Technical signals provide context, but news drives short-term movements.
- **Focus on the LATEST news**: The tavily_search returns news from the current week. Prioritize the most recent articles in your analysis as they are most relevant for 2-week trend prediction
- If you find limited or no news, note this in your summary and provide lower confidence
- Consider both company-specific news and broader market/industry trends
- Provide honest, balanced analysis - don't overstate confidence if evidence is weak

## Response Format

Your final response should be a JSON object with these fields:
{
    "trend_direction": "up" or "down" or "neutral",
    "confidence": 0-100,
    "summary": "Your analysis explanation in Chinese"
}
"""


def format_data_context(recent_prices: list, indicators: dict, valuation_data: dict = None) -> str:
    """Format quantitative data as readable text for LLM context."""
    lines = []

    # Recent price trend
    if recent_prices:
        first = recent_prices[0]
        last = recent_prices[-1]
        change = ((last['close'] - first['close']) / first['close']) * 100
        lines.append(f"近10日走势: 从{first['close']}到{last['close']}, 涨跌幅{change:.2f}%")
        lines.append(f"最新收盘价: {last['close']}, 最高: {last['high']}, 最低: {last['low']}")

        # Volume trend
        avg_vol = sum(p['volume'] for p in recent_prices) / len(recent_prices)
        last_vol = recent_prices[-1]['volume']
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
        lines.append(f"成交量比: {vol_ratio:.2f} (>1放量, <1缩量)")

    # MACD signals
    macd = indicators.get("macd", {})
    if macd:
        dif, dea, hist = macd.get("dif", 0), macd.get("dea", 0), macd.get("hist", 0)
        signal = "金叉(看多)" if dif > dea else "死叉(看空)"
        lines.append(f"MACD: DIF={dif:.4f}, DEA={dea:.4f}, 柱状={hist:.4f}, 信号={signal}")

    # RSI signals
    rsi = indicators.get("rsi", {})
    if rsi:
        rsi6 = rsi.get("rsi6", 50)
        zone = "超买区(>80)" if rsi6 > 80 else "超卖区(<20)" if rsi6 < 20 else "正常区间"
        lines.append(f"RSI(6): {rsi6:.2f} - {zone}")

    # MA signals
    ma = indicators.get("ma", {})
    if ma and recent_prices:
        price = recent_prices[-1]['close']
        ma5 = ma.get("ma5", 0)
        ma20 = ma.get("ma20", 0)
        above_ma5 = "在5日均线上方" if price > ma5 else "在5日均线下方"
        above_ma20 = "在20日均线上方" if price > ma20 else "在20日均线下方"
        lines.append(f"均线: {above_ma5}, {above_ma20}")

    # Valuation metrics
    if valuation_data and "error" not in valuation_data:
        latest = valuation_data.get("latest", {})
        pe_ttm = latest.get("pe_ttm")
        pb = latest.get("pb")
        turnover_rate = latest.get("turnover_rate")
        total_mv = latest.get("total_mv")
        if pe_ttm is not None:
            lines.append(f"PE(TTM): {pe_ttm:.2f}")
        if pb is not None:
            lines.append(f"PB: {pb:.2f}")
        if turnover_rate is not None:
            lines.append(f"换手率: {turnover_rate:.2f}%")
        if total_mv is not None:
            lines.append(f"总市值: {total_mv:.0f}万元")

    return "\n".join(lines)


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

    # Step 1: Fetch K-line data and technical indicators
    kline_data = []
    indicators = {}
    technical_data_note = ""

    try:
        kline_result = AkshareService.get_kline_data(symbol, days=60)
        kline_data = kline_result.get("data", [])

        if kline_data:
            indicators = AkshareService.calculate_indicators(kline_data)
    except Exception as e:
        logger.warning(f"Failed to fetch technical data for {symbol}: {e}")
        technical_data_note = "（技术数据不可用）"

    # Fetch valuation metrics (PE TTM, PB, turnover rate)
    valuation_data = None
    try:
        valuation_result = AkshareService.get_daily_basic(symbol, days=30)
        if "error" not in valuation_result:
            valuation_data = valuation_result
    except Exception as e:
        logger.warning(f"Failed to fetch valuation data for {symbol}: {e}")

    # Step 2: Build data context if we have technical data
    data_context = ""
    if kline_data and indicators and not indicators.get("error"):
        recent_prices = kline_data[-10:] if len(kline_data) >= 10 else kline_data
        data_context = format_data_context(recent_prices, indicators, valuation_data)

    # Step 3: Build user message
    agent = create_stock_trend_agent()
    logger.info(f"Agent created for {symbol}, invoking...")

    if data_context:
        user_message = f"""请分析股票 {name} ({symbol}) 的未来2周趋势。

## 技术数据
{data_context}

请使用 tavily_search 工具搜索最新新闻，然后结合以上技术数据给出预测。
"""
    else:
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
                "summary": f"分析失败：无法获取响应{technical_data_note}",
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
