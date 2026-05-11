"""Stock trend analysis agent using DeepAgent with Tavily search."""
import os
import sys
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import date
from dotenv import load_dotenv
from typing import Dict, Any, Literal

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langsmith import traceable

from backend.services.tavily_search_tool import tavily_search
from backend.services.minimax_mcp_search_tool import minimax_mcp_search
from backend.services.akshare_service import AShareService, USStockService, HKStockService, AkshareService, calculate_indicators, _is_us_stock_symbol, _is_hk_stock_symbol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

MAX_RETRIES = 2  # Total 3 attempts (initial + 2 retries)


def _extract_json_object(content: str) -> str | None:
    """Extract the first complete JSON object from content using bracket counting."""
    import re
    import sys

    print(f"[DEBUG] Input content length: {len(content)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Content starts with: {content[:100]}", file=sys.stderr, flush=True)

    # Remove <think>... markers BEFORE extraction to avoid false braces inside thinking
    cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    print(f"[DEBUG] After stripping markers, length: {len(cleaned)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Cleaned starts with: {cleaned[:100]}", file=sys.stderr, flush=True)

    # Find the first '{'
    start = cleaned.find('{')
    if start == -1:
        print(f"[DEBUG] No '{{' found in cleaned content", file=sys.stderr, flush=True)
        return None

    print(f"[DEBUG] Found '{{' at position {start}", file=sys.stderr, flush=True)

    # Count brackets to find the matching closing '}'
    depth = 0
    in_string = False
    escape_next = False
    i = start

    while i < len(cleaned):
        c = cleaned[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if c == '\\':
            escape_next = True
            i += 1
            continue

        if c == '"' and not escape_next:
            in_string = not in_string
            i += 1
            continue

        if in_string:
            i += 1
            continue

        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                result = cleaned[start:i+1]
                print(f"[DEBUG] Found complete JSON at positions {start}-{i}, length {len(result)}", file=sys.stderr, flush=True)
                print(f"[DEBUG] JSON preview: {result[:200]}", file=sys.stderr, flush=True)
                return result

        i += 1

    print(f"[DEBUG] Bracket counting finished without finding closing '}}'. Final depth={depth}, in_string={in_string}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Content around end: {cleaned[max(0,len(cleaned)-100):]}", file=sys.stderr, flush=True)
    return None


def _is_valid_prediction(prediction: dict) -> bool:
    """Check if prediction dict has the required fields from the LLM."""
    # Note: 'symbol', 'name', 'summary' are added by analyze_stock_trend, not the LLM
    # The LLM only guarantees 'trend_direction' and 'confidence'
    required_fields = ['trend_direction', 'confidence']
    return all(field in prediction and prediction[field] is not None for field in required_fields)


def _parse_agent_output(content: str, symbol: str, name: str) -> dict | None:
    """Extract and parse JSON from agent output. Returns None if parsing fails."""
    import json

    # Extract JSON using bracket counting (handles embedded thinking markers)
    json_str = _extract_json_object(content)
    if not json_str:
        return None

    try:
        prediction = json.loads(json_str)
        # Validate required fields
        if not _is_valid_prediction(prediction):
            print(f"[DEBUG] _is_valid_prediction failed. Fields present: {list(prediction.keys())}", file=sys.stderr, flush=True)
            return None
        return prediction
    except json.JSONDecodeError as e:
        print(f"[DEBUG] JSON decode error: {e}", file=sys.stderr, flush=True)
        return None


def get_today_date() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


def fetch_yahoo_finance_rss(symbol: str, proxy_url: str = None) -> list:
    """Fetch Yahoo Finance RSS feed for a given stock symbol.

    Args:
        symbol: Stock symbol (e.g., "EBAY", "GOOGL")
        proxy_url: Optional proxy URL (e.g., "http://127.0.0.1:10887")

    Returns:
        List of dicts with: title, description, link, pubDate
        Returns empty list if fetch fails.
    """
    import xml.etree.ElementTree as ET
    import requests

    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    try:
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)

        if response.status_code != 200:
            logger.warning(f"Yahoo Finance RSS returned status {response.status_code} for {symbol}")
            return []

        # Parse XML
        root = ET.fromstring(response.content)
        items = []

        for item in root.findall(".//item"):
            title = _get_element_text(item, "title")
            description = _get_element_text(item, "description")
            link = _get_element_text(item, "link")
            pub_date = _get_element_text(item, "pubDate")

            if title:
                items.append({
                    "title": title,
                    "description": description or "",
                    "link": link or "",
                    "pubDate": pub_date or ""
                })

        # Sort by date descending (newest first)
        items.sort(key=lambda x: x["pubDate"] or "", reverse=True)
        logger.info(f"Fetched {len(items)} RSS items for {symbol}")
        return items

    except Exception as e:
        logger.warning(f"Failed to fetch Yahoo Finance RSS for {symbol}: {e}")
        return []


def _get_element_text(element: ET.Element, tag: str) -> str:
    """Get text content from XML element."""
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else ""


def _format_rss_news_for_agent(rss_items: list, name: str, symbol: str) -> str:
    """Format RSS news items for Agent consumption.

    Args:
        rss_items: List of RSS item dicts with title, description, link, pubDate
        name: Stock name
        symbol: Stock symbol

    Returns:
        Formatted string for Agent prompt
    """
    lines = []
    for i, item in enumerate(rss_items, 1):
        title = item.get("title", "")
        description = item.get("description", "")
        pub_date = item.get("pubDate", "")

        # Clean description (remove HTML tags if any)
        import re
        description = re.sub(r'<[^>]+>', '', description)
        description = description.strip() if description else ""

        lines.append(f"新闻 {i}: {title}")
        if description:
            lines.append(f"摘要: {description[:200]}...")
        if pub_date:
            lines.append(f"日期: {pub_date}")
        lines.append("")

    return "\n".join(lines)


@tool(parse_docstring=True)
def search_with_fallback(
    query: str,
    max_results: int = 5,
    time_range: Literal["day", "week", "month", "year"] = "month",
) -> str:
    """Search the web with automatic fallback from MiniMax MCP to Tavily.

    This tool tries MiniMax MCP first (primary), and if it fails or returns no results,
    automatically falls back to Tavily search. Use this for stock news
    and macro environment searches. News results are filtered to the specified time range.

    Args:
        query: The search query to look up
        max_results: Maximum number of results to return (default: 5)
        time_range: Time range for results - "day", "week", "month", or "year" (default: "month")
    """
    # Try MiniMax MCP first (primary search)
    mcp_result = minimax_mcp_search.invoke({
        "query": query,
        "max_results": max_results,
        "time_range": time_range,
    })

    # Check if MiniMax MCP succeeded
    if mcp_result and "error" not in mcp_result.lower() and mcp_result != "No search results found.":
        return mcp_result

    # Fallback to Tavily
    logger.info("MiniMax MCP search failed or returned empty, trying Tavily...")
    tavily_result = tavily_search.invoke({
        "query": query,
        "max_results": max_results,
        "time_range": time_range,
    })

    if tavily_result and "error" not in tavily_result.lower() and tavily_result != "No search results found.":
        return tavily_result

    # Both failed
    return "No search results available from either source."


def _get_model():
    """Initialize the MiniMax ChatOpenAI model."""
    return ChatOpenAI(
        model="MiniMax-M2.7-highspeed",
        openai_api_key=os.environ.get("MINIMAX_API_KEY"),
        openai_api_base="https://api.minimax.chat/v1",
        temperature=0,
    )


def get_system_prompt(today_date: str, market: str = "A") -> str:
    """Return the system prompt with today's date injected."""
    if market == "A":
        return f"""You are a professional stock analyst agent. Today is {today_date}. Your task is to analyze a given A-share stock and predict its price trend for the next 2 weeks based on BOTH technical data AND recent news.

## A-Share Market Context
- Currency: CNY (人民币)
- Exchanges: Shanghai Stock Exchange (SSE), Shenzhen Stock Exchange (SZSE)
- Trading hours: 9:30 AM - 3:00 PM CST (China Standard Time)

## Your Process

1. **Analyze the provided technical data**: Review the K-line data, MACD, RSI, and MA signals provided in the message.
   - Price trend direction and magnitude
   - MACD golden/death cross signals
   - RSI zone (overbought >80, oversold <20)
   - Price position relative to moving averages
   - Volume ratio (above 1 = volume expansion)
   - Money flow signals (main force net inflow/outflow, 净流入/净流出偏多/持平)

2. **Search for stock-specific news**: Use the search_with_fallback tool to search for recent news about the specific stock (symbol and name).
   - Search query format: "[stock name] [stock symbol] recent news"
   - This will try MiniMax MCP first, then Tavily as fallback
   - Collect up to 5 recent news items from the past month

3. **Search for macro environment**: Use the search_with_fallback tool to search for macro factors that might affect the stock:
   - Interest rate trends
   - GDP and economic data
   - Industry-specific trends
   - Market sentiment

4. **Combine technical + sentiment analysis**: Weight technical signals (40%) and news sentiment (60%) to form your prediction.
   - If technical signals confirm news direction → higher confidence
   - If technical signals conflict with news direction → lower confidence and note the disagreement

5. **Return structured prediction**: Provide your final prediction with structured three-section format

## Important Guidelines

- **Use the provided technical data first**: The technical data is provided under "## 技术数据" section. Analyze it BEFORE searching for news.
- **Weight: 40% technical, 60% news**: Technical signals provide context, but news drives short-term movements.
- **Focus on the LATEST news**: The search_with_fallback returns news from the current week. Prioritize the most recent articles in your analysis as they are most relevant for 2-week trend prediction
- If you find limited or no news, note this in your summary and provide lower confidence
- Consider both company-specific news and broader market/industry trends
- Provide honest, balanced analysis - don't overstate confidence if evidence is weak
- **Operation suggestions are for reference only, not investment advice**

## Response Format

**CRITICAL: You MUST output ONLY a valid JSON object. Do not include any text before or after the JSON.**

Your final response MUST be a valid JSON object with these fields. Here is a complete example:

```json
{{
    "trend_direction": "up",
    "confidence": 78,
    "情绪分析": {{
        "news": [
            {{
                "title": "药明康德发布2024年业绩预告",
                "source": "东方财富网",
                "date": "2024-01-15",
                "summary": "公司预计2024年净利润同比增长15%-20%，受益于全球生物医药研发外包需求持续增长。"
            }},
            {{
                "title": "CXO行业获大行看好",
                "source": "野村证券",
                "date": "2024-01-14",
                "summary": "野村证券发布研报称CXO行业估值具备吸引力，维持药明康德增持评级，目标价108元。"
            }}
        ],
        "summary": "市场情绪整体偏多，机构投资者看好CXO行业前景，公司业绩稳健增长提供支撑。"
    }},
    "技术分析": {{
        "macd": {{"value": "0.35/0.28", "signal": "金叉", "interpretation": "MACD在零轴上方形成金叉，短期多头信号明显"}},
        "rsi": {{"value": "65.5", "zone": "正常", "interpretation": "RSI处于正常区间，未出现超买超卖"}},
        "ma": {{"position": "价格在5日、20日均线上方", "interpretation": "均线多头排列，短期趋势向好"}},
        "volume": {{"ratio": "1.3", "interpretation": "成交量放大，市场参与度提升"}},
        "valuation": {{"pe": "28.5", "pb": "5.2", "turnover": "2.5%", "interpretation": "估值处于历史中枢偏低位置"}},
        "money_flow": {{"net_5d": "6.76亿元", "signal": "净流入偏多", "interpretation": "主力资金持续流入，市场参与度提升"}},
        "finance_metrics": {{"summary": "EPS: 2.35, BPS: 12.80, ROE: 18.4%, 毛利率: 35.2%, 净利率: 15.8%, 每股收益同比增长: +12.5%, 净利润同比增长: +8.3%, 营收同比增长: +5.1%, 资产负债率: 45.2%, 流动比率: 1.8, 总营收: 125.6亿元, 净利润: 19.8亿元", "interpretation": "公司盈利能力良好，ROE维持在18%以上，净利润保持稳定增长，资产负债率适中，流动性充裕，基本面支撑股价"}}
    }},
    "趋势判断": {{
        "forecast": "市场环境\n外围市场整体平稳，美联储降息预期升温，流动性环境有利成长股\n\n技术面分析\nMACD金叉确认，均线多头排列，成交量配合放大，108元一线为近期重要阻力位\n\n短期展望\n预计股价在102-110区间震荡偏强运行，若突破108元可能进一步上探110元",
        "suggestion": "持有",
        "reasoning": "市场环境\n机构看多情绪较高，外资持续流入提供支撑\n\n技术面分析\n技术指标向好，但RSI已接近70，短期可能有回调压力\n\n操作建议\n建议持有为主，逢低可适度加仓，突破108元后考虑加仓"
    }}
}}
```

**Key Requirements:**
1. `forecast` and `reasoning` MUST use exactly 3 paragraphs separated by `\\n\\n`
2. Each paragraph has a title (like "市场环境", "技术面分析", "操作建议") followed by content
3. Use Chinese for all content
4. Output valid JSON only - no markdown code blocks, no explanatory text
5. When financial data (财务指标) is provided in the context, the `技术分析` block MUST include a `finance_metrics` sub-block summarizing key financial indicators (EPS, ROE, margins, growth rates) and their interpretation.
"""

    # HK and US stocks
    return f"""You are a professional stock analyst agent. Today is {today_date}. Your task is to analyze a given stock and predict its price trend for the next 2 weeks based on BOTH technical data AND recent news.

## Market Context
- Currency: USD (美元) for US stocks, HKD (港币) for HK stocks
- Exchanges: NYSE, NASDAQ (US) / SEHK (HK)

## Your Process

1. **Analyze the provided technical data**: Review the K-line data, MACD, RSI, and MA signals provided in the message.
   - Price trend direction and magnitude
   - MACD golden/death cross signals
   - RSI zone (overbought >80, oversold <20)
   - Price position relative to moving averages
   - Volume ratio (above 1 = volume expansion)
   - Money flow signals (main force net inflow/outflow)

2. **Search for stock-specific news**: Use the search_with_fallback tool to search for recent news about the specific stock (symbol and name).
   - Search query format: "[stock name] [stock symbol] recent news"
   - This will try MiniMax MCP first, then Tavily as fallback
   - Collect up to 5 recent news items from the past month

3. **Search for macro environment**: Use the search_with_fallback tool to search for macro factors that might affect the stock:
   - Interest rate trends
   - GDP and economic data
   - Industry-specific trends
   - Market sentiment

4. **Combine technical + sentiment analysis**: Weight technical signals (40%) and news sentiment (60%) to form your prediction.
   - If technical signals confirm news direction → higher confidence
   - If technical signals conflict with news direction → lower confidence and note the disagreement

5. **Return structured prediction**: Provide your final prediction with structured three-section format

## Important Guidelines

- **Use the provided technical data first**: The technical data is provided under "## 技术数据" section. Analyze it BEFORE searching for news.
- **Weight: 40% technical, 60% news**: Technical signals provide context, but news drives short-term movements.
- **Focus on the LATEST news**: The search_with_fallback returns news from the current week. Prioritize the most recent articles in your analysis as they are most relevant for 2-week trend prediction
- If you find limited or no news, note this in your summary and provide lower confidence
- Consider both company-specific news and broader market/industry trends
- Provide honest, balanced analysis - don't overstate confidence if evidence is weak
- **Operation suggestions are for reference only, not investment advice**

## Response Format

**CRITICAL: You MUST output ONLY a valid JSON object. Do not include any text before or after the JSON.**

Your final response MUST be a valid JSON object with these fields. Here is a complete example:

```json
{{
    "trend_direction": "up",
    "confidence": 75,
    "情绪分析": {{
        "news": [
            {{
                "title": "Apple发布强劲Q4财报",
                "source": "Reuters",
                "date": "2024-01-15",
                "summary": "Apple业绩超预期，中国区iPhone销售强劲。"
            }}
        ],
        "summary": "财报超预期，市场情绪偏多。"
    }},
    "技术分析": {{
        "macd": {{"value": "0.35/0.28", "signal": "金叉", "interpretation": "MACD在零轴上方形成金叉，短期多头信号明显"}},
        "rsi": {{"value": "65.5", "zone": "正常", "interpretation": "RSI处于正常区间，未出现超买超卖"}},
        "ma": {{"position": "价格在5日、20日均线上方", "interpretation": "均线多头排列，短期趋势向好"}},
        "volume": {{"ratio": "1.3", "interpretation": "成交量放大，市场参与度提升"}},
        "valuation": {{"pe": "28.5", "pb": "5.2", "turnover": "2.5%", "interpretation": "估值处于历史中枢位置"}},
        "money_flow": {{"net_5d": "6.76亿美元", "signal": "净流入偏多", "interpretation": "主力资金持续流入，市场参与度提升"}}
    }},
    "趋势判断": {{
        "forecast": "市场环境\n美股市场整体平稳，美联储降息预期升温，流动性环境有利成长股\n\n技术面分析\nMACD金叉确认，均线多头排列，180美元一线为近期重要阻力位\n\n短期展望\n预计股价在175-185区间震荡偏强运行，若突破180美元可能进一步上探185美元",
        "suggestion": "持有",
        "reasoning": "市场环境\n机构看多情绪较高，外资持续流入提供支撑\n\n技术面分析\n技术指标向好，但RSI已接近70，短期可能有回调压力\n\n操作建议\n建议持有为主，逢低可适度加仓，突破180美元后考虑加仓"
    }}
}}
```

**Key Requirements:**
1. `forecast` and `reasoning` MUST use exactly 3 paragraphs separated by `\\n\\n`
2. Each paragraph has a title (like "市场环境", "技术面分析", "操作建议") followed by content
3. Use Chinese for all content
4. Output valid JSON only - no markdown code blocks, no explanatory text
5. Do NOT include `finance_metrics` field for HK or US stocks.
"""


def format_data_context(recent_prices: list, indicators: dict, valuation_data: dict = None, market: str = "A", money_flow_data: dict = None, financial_data: dict = None) -> str:
    """Format quantitative data as readable text for LLM context."""
    lines = []
    currency = "USD" if market == "US" else "CNY"

    # Note: data is based on 100-day K-line
    lines.append("注: 以下技术指标基于近100日K线数据计算")
    lines.append("")
    if recent_prices:
        first = recent_prices[0]
        last = recent_prices[-1]
        change = ((last['close'] - first['close']) / first['close']) * 100
        lines.append(f"近10日走势: 从{first['close']}到{last['close']}, 涨跌幅{change:.2f}%")
        lines.append(f"最新收盘价: {last['close']} {currency}, 最高: {last['high']}, 最低: {last['low']}")

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
        if turnover_rate is not None and turnover_rate != 0:
            # HK/US stocks return turnover as decimal fraction (<1), A-shares return as percentage (>=1)
            display_turnover = turnover_rate * 100 if market in ("HK", "US") else turnover_rate
            lines.append(f"换手率: {display_turnover:.2f}%")
        if total_mv is not None:
            if market == "HK":
                # total_mv from Futu is in HKD; convert to 亿HKD
                hkd_yi = total_mv / 1e8
                lines.append(f"总市值: {hkd_yi:.0f}亿HKD")
            elif market == "US":
                # total_mv from Futu is in USD; display as 亿美元
                lines.append(f"总市值: {total_mv / 1e8:.0f}亿美元")
            else:
                # A-share: total_mv from Tushare is in 万元; convert to 亿元
                lines.append(f"总市值: {total_mv/10000:.0f}亿元")

    # Money flow (appended to valuation section)
    if money_flow_data and "error" not in money_flow_data:
        net_5d = money_flow_data.get("net_5d_total")
        if net_5d is not None and net_5d != 0:
            signal = "净流入偏多" if net_5d > 0 else "净流出偏多"
            if market == "HK":
                # main_in_flow from Futu is in HKD; convert to 亿HKD
                lines.append(f"5日主力净流入: {net_5d/1e8:.2f}亿HKD ({signal})")
            elif market == "US":
                # US money flow from Futu is in USD; convert to 亿美元
                lines.append(f"5日主力净流入: {net_5d/1e8:.2f}亿美元 ({signal})")
            else:
                # A-share money flow is in 万元; convert to 亿元
                lines.append(f"5日主力净流入: {net_5d/10000:.2f}亿元 ({signal})")

    # Financial fundamentals for A-share stocks
    if financial_data and "error" not in financial_data:
        data = financial_data.get("data", {})
        if data:
            report_label = data.get("report_label", "--")
            ann_date = data.get("ann_date", "--")
            lines.append(f"财务指标 ({report_label}, {ann_date}发布):")

            # Helper to format value or return --
            def fmt(val, decimal=2):
                if val is None:
                    return "--"
                return f"{val:.{decimal}f}"

            eps = fmt(data.get("eps"))
            bps = fmt(data.get("bps"))
            roe = fmt(data.get("roe"), 1)
            gross_margin = fmt(data.get("gross_margin"), 1)
            netprofit_margin = fmt(data.get("netprofit_margin"), 1)
            basic_eps_yoy = fmt(data.get("basic_eps_yoy"), 1)
            netprofit_yoy = fmt(data.get("netprofit_yoy"), 1)
            tr_yoy = fmt(data.get("tr_yoy"), 1)
            debt_to_assets_val = data.get("debt_to_assets")
            debt_to_assets = f"{debt_to_assets_val:.1f}" if debt_to_assets_val is not None else "--"
            if debt_to_assets.startswith("+"):
                debt_to_assets = debt_to_assets[1:]
            current_ratio = fmt(data.get("current_ratio"), 1)
            # Tushare income table returns in 元, convert to 亿元 (/1e8)
            total_revenue_val = data.get("total_revenue")
            total_revenue = f"{total_revenue_val/1e8:.2f}" if total_revenue_val is not None else "--"
            n_income_val = data.get("n_income")
            n_income = f"{n_income_val/1e8:.2f}" if n_income_val is not None else "--"

            lines.append(f"EPS: {eps}, BPS: {bps}, ROE: {roe}%, 毛利率: {gross_margin}%, 净利率: {netprofit_margin}%")
            lines.append(f"每股收益同比增长: {basic_eps_yoy}%, 净利润同比增长: {netprofit_yoy}%, 营收同比增长: {tr_yoy}%")
            lines.append(f"资产负债率: {debt_to_assets}%, 流动比率: {current_ratio}, 总营收: {total_revenue}亿元, 净利润: {n_income}亿元")

    return "\n".join(lines)


def create_stock_trend_agent(market: str = "A"):
    """Create a DeepAgent for stock trend analysis with fallback search tools."""
    model = _get_model()

    agent = create_deep_agent(
        model=model,
        system_prompt=get_system_prompt(get_today_date(), market),
        tools=[search_with_fallback],
    )

    return agent


def _build_user_message(market: str, symbol: str, name: str, today_date: str, data_context: str) -> str:
    """Build user message based on market type.

    Args:
        market: "US", "HK", or "A"
        symbol: Stock symbol
        name: Stock name
        today_date: Today's date in YYYY-MM-DD format
        data_context: Formatted technical data string

    Returns:
        User message prompt for the agent
    """
    if market == "US":
        return _build_us_stock_message(symbol, name, today_date, data_context)
    elif market == "HK":
        return _build_hk_stock_message(symbol, name, today_date, data_context)
    else:
        return _build_a_stock_message(symbol, name, today_date, data_context)


def _build_us_stock_message(symbol: str, name: str, today_date: str, data_context: str) -> str:
    """Build user message for US stocks using Yahoo Finance RSS + search fallback."""
    proxy_url = os.environ.get("YF_PROXY")
    rss_items = fetch_yahoo_finance_rss(symbol, proxy_url)

    if rss_items:
        logger.info(f"RSS returned {len(rss_items)} items for {symbol}")
        rss_news_text = _format_rss_news_for_agent(rss_items, name, symbol)

        if data_context:
            return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

## 技术数据
{data_context}

## Yahoo Finance 最新新闻列表
{rss_news_text}

请根据以上新闻列表，选取最重要的5条新闻（根据与 {name} 的相关性和时效性），然后使用 search_with_fallback 工具分别搜索每条新闻获取更多详情，最后结合技术数据和新闻给出预测。
"""
        else:
            return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

## Yahoo Finance 最新新闻列表
{rss_news_text}

请根据以上新闻列表，选取最重要的5条新闻（根据与 {name} 的相关性和时效性），然后使用 search_with_fallback 工具分别搜索每条新闻获取更多详情，最后给出预测。
"""
    else:
        # RSS failed - fall back to existing search
        logger.warning(f"RSS fetch failed for {symbol}, using fallback search")
        if data_context:
            return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

## 技术数据
{data_context}

请使用 search_with_fallback 工具优先搜索 Yahoo Finance (site:finance.yahoo.com) 关于 {name} ({symbol}) 的新闻，再搜索今天 '{today_date}' 最新新闻，然后结合以上技术数据给出预测。
"""
        else:
            return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

请使用 search_with_fallback 工具优先搜索 Yahoo Finance (site:finance.yahoo.com) 关于 {name} ({symbol}) 的新闻。
"""


def _build_a_stock_message(symbol: str, name: str, today_date: str, data_context: str) -> str:
    """Build user message for A-shares (China) using generic search."""
    if data_context:
        return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

## 技术数据
{data_context}

请使用 search_with_fallback 工具搜索今天 '{today_date}' 最新新闻，再搜索这周的新闻，然后结合以上技术数据给出预测。
"""
    else:
        return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

请使用 search_with_fallback 工具搜索今天 '{today_date}' 最新新闻，再搜索这周的新闻。
"""


def _build_hk_stock_message(symbol: str, name: str, today_date: str, data_context: str) -> str:
    """Build user message for HK stocks.

    Currently uses same logic as A-shares. TODO: Add HK-specific news sources.
    """
    if data_context:
        return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

## 技术数据
{data_context}

请使用 search_with_fallback 工具搜索今天 '{today_date}' 最新新闻，再搜索这周的新闻，然后结合以上技术数据给出预测。
"""
    else:
        return f"""请分析股票 {name} ({symbol}) 的未来2周趋势（日期: {today_date}）。

请使用 search_with_fallback 工具搜索今天 '{today_date}' 最新新闻，再搜索这周的新闻。
"""


@traceable
def analyze_stock_trend(symbol: str, name: str) -> Dict[str, Any]:
    """Analyze stock trend using DeepAgent with fallback search.

    Uses Tavily as primary search with MiniMax MCP as fallback when
    Tavily is unavailable. Automatically routes to USStockService for US stocks.

    Args:
        symbol: Stock symbol (e.g., "000001" for A-share, "GOOGL" for US)
        name: Stock name (e.g., "平安银行" or "Google")

    Returns:
        Dictionary containing trend_direction, confidence, and summary
    """
    # Determine market and select appropriate service
    is_us = _is_us_stock_symbol(symbol)
    is_hk = _is_hk_stock_symbol(symbol)
    market = "US" if is_us else ("HK" if is_hk else "A")

    if is_us:
        stock_service = USStockService
        logger.info(f"Starting US stock trend analysis for {name} ({symbol})")
    elif is_hk:
        stock_service = HKStockService
        logger.info(f"Starting HK stock trend analysis for {name} ({symbol})")
    else:
        stock_service = AShareService
        logger.info(f"Starting A-share trend analysis for {name} ({symbol})")

    # Step 1: Fetch K-line data and technical indicators
    kline_data = []
    indicators = {}

    try:
        kline_result = stock_service.get_kline_data(symbol, days=100)
        kline_data = kline_result.get("data", [])

        if kline_data:
            indicators = calculate_indicators(kline_data)
    except Exception as e:
        logger.warning(f"Failed to fetch technical data for {symbol}: {e}")

    # Fetch valuation metrics (PE TTM, PB, turnover rate)
    valuation_data = None
    try:
        valuation_result = stock_service.get_daily_basic(symbol, days=30)
        if "error" not in valuation_result:
            valuation_data = valuation_result
    except Exception as e:
        logger.warning(f"Failed to fetch valuation data for {symbol}: {e}")

    # Fetch money flow data (5-day main force net inflow)
    money_flow_data = None
    try:
        money_flow_result = stock_service.get_moneyflow(symbol, days=30)
        if "error" not in money_flow_result:
            money_flow_data = money_flow_result
    except Exception as e:
        logger.warning(f"Failed to fetch money flow data for {symbol}: {e}")

    # Fetch financial fundamentals for A-share stocks
    financial_data = None
    if market == "A":
        try:
            financial_result = AShareService.get_financial_fundamentals(symbol)
            if "error" not in financial_result:
                financial_data = financial_result
        except Exception as e:
            logger.warning(f"Failed to fetch financial fundamentals for {symbol}: {e}")

    # Step 2: Build data context if we have technical data
    data_context = ""
    if kline_data and indicators and not indicators.get("error"):
        recent_prices = kline_data[-10:] if len(kline_data) >= 10 else kline_data
        data_context = format_data_context(recent_prices, indicators, valuation_data, market, money_flow_data, financial_data)

    # Step 3: Build user message based on market
    agent = create_stock_trend_agent(market)
    logger.info(f"Agent created for {symbol}, invoking...")

    today_date = get_today_date()
    user_message = _build_user_message(market, symbol, name, today_date, data_context)

    # Step 3: Invoke agent with retry logic
    attempt = 0
    last_error_content = None

    while attempt <= MAX_RETRIES:
        try:
            logger.info(f"Invoking agent for {symbol} (attempt {attempt + 1}/{MAX_RETRIES + 1})...")
            result = agent.invoke({
                "messages": [{"role": "user", "content": user_message}]
            })
            logger.info(f"Agent invocation complete for {symbol}")

            messages = result.get("messages", [])
            if not messages:
                logger.warning(f"No messages returned for {symbol}, attempt {attempt + 1}")
                last_error_content = "No messages returned"
                attempt += 1
                continue

            final_msg = messages[-1]
            content = final_msg.content

            # Try to parse with marker stripping and validation
            prediction = _parse_agent_output(content, symbol, name)
            if prediction:
                # Return the full structured response with backward-compatible fields
                return {
                    "symbol": symbol,
                    "name": name,
                    "trend_direction": prediction.get("trend_direction", "neutral"),
                    "confidence": prediction.get("confidence", 0),
                    "summary": prediction.get("趋势判断", {}).get("forecast", "") or prediction.get("summary", ""),
                    "情绪分析": prediction.get("情绪分析"),
                    "技术分析": prediction.get("技术分析"),
                    "趋势判断": prediction.get("趋势判断"),
                }

            # Parsing failed, log and retry
            logger.warning(f"Failed to parse agent output for {symbol}, attempt {attempt + 1}. Content preview: {content[:200]}")
            last_error_content = content
            attempt += 1

        except Exception as e:
            logger.error(f"Agent invocation error for {symbol}, attempt {attempt + 1}: {e}")
            last_error_content = str(e)
            attempt += 1

    # All retries exhausted
    logger.error(f"All {MAX_RETRIES + 1} attempts failed for {symbol}. Last error: {last_error_content}")
    return {
        "symbol": symbol,
        "name": name,
        "trend_direction": "neutral",
        "confidence": 0,
        "summary": "Analysis could not produce valid output after retries. Please try again later.",
        "情绪分析": None,
        "技术分析": None,
        "趋势判断": None,
    }
