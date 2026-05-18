"""Institutional Trading Analysis Agent for Dragon Tiger List stocks.

Uses DeepAgent pattern with MiniMax model, Tushare data.
"""
import os
import re
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import date

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langsmith import traceable

from backend.services.minimax_mcp_search_tool import minimax_mcp_search
from backend.services.tavily_search_tool import tavily_search
from backend.services.akshare_service import (
    AShareService,
    _is_us_stock_symbol,
    _is_hk_stock_symbol,
    calculate_indicators,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _extract_json_object(content: str) -> Optional[str]:
    """Extract JSON object from content, handling embedded thinking markers."""
    # Strip thinking markers
    cleaned = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)

    # Find the first '{'
    start = cleaned.find('{')
    if start == -1:
        return None

    # Count brackets to find matching closing '}'
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
                return cleaned[start:i+1]

        i += 1

    return None


def _is_valid_prediction(prediction: dict) -> bool:
    """Check if prediction dict has required fields."""
    required_fields = ['trend_direction', 'confidence']
    return all(field in prediction and prediction[field] is not None for field in required_fields)


def _parse_agent_output(content: str, symbol: str, name: str) -> dict | None:
    """Extract and parse JSON from agent output. Returns None if parsing fails."""
    import json

    # Try to extract JSON from content
    json_str = _extract_json_object(content)
    if not json_str:
        # Fallback: try stripping markdown code blocks
        stripped = content.strip()
        if stripped.startswith('```'):
            lines = stripped.split('\n')
            if len(lines) >= 2:
                # Remove first line (```json) and last line (```)
                json_str = '\n'.join(lines[1:-1])
                # If the last line is just ```, remove it
                if json_str.strip().endswith('```'):
                    json_str = json_str.strip()[:-3].strip()

    if not json_str:
        return None

    try:
        prediction = json.loads(json_str)
        if not _is_valid_prediction(prediction):
            logger.warning(f"_is_valid_prediction failed for {symbol}. Fields: {list(prediction.keys())}")
            return None
        return prediction
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error for {symbol}: {e}")
        return None


def get_today_date() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


def load_system_prompt(today_date: str) -> str:
    """Load system prompt from external file and inject today's date."""
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "agent_prompts",
        "institutional_trading_analysis_agent.txt"
    )

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    return prompt_template.format(today_date=today_date)


def _get_model():
    """Initialize the MiniMax ChatOpenAI model."""
    return ChatOpenAI(
        model="MiniMax-M2.7-highspeed",
        openai_api_key=os.environ.get("MINIMAX_API_KEY"),
        openai_api_base="https://api.minimax.chat/v1",
        temperature=0,
        max_tokens=16000,
    )


@tool(parse_docstring=True)
def search_with_fallback(
    query: str,
    max_results: int = 5,
    time_range: str = "month",
) -> str:
    """Search the web with automatic fallback from MiniMax MCP to Tavily.

    Args:
        query: The search query to look up
        max_results: Maximum number of results to return (default: 5)
        time_range: Time range for results - "day", "week", "month", or "year" (default: "month")
    """
    # Try MiniMax MCP first
    try:
        mcp_result = minimax_mcp_search.invoke({
            "query": query,
            "max_results": max_results,
            "time_range": time_range,
        })
        if mcp_result and "error" not in mcp_result.lower() and mcp_result != "No search results found.":
            return mcp_result
    except Exception as e:
        logger.warning(f"MiniMax MCP search failed: {e}")

    # Fallback to Tavily
    try:
        tavily_result = tavily_search.invoke({
            "query": query,
            "max_results": max_results,
            "time_range": time_range,
        })
        if tavily_result and "error" not in tavily_result.lower() and tavily_result != "No search results found.":
            return tavily_result
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")

    return "No search results available from either source."


def format_data_context(
    recent_prices: list,
    indicators: dict,
    valuation_data: dict = None,
    money_flow_data: dict = None,
    financial_data: dict = None,
    dragon_tiger_data: dict = None,
) -> str:
    """Format quantitative data as readable text for LLM context."""
    lines = []

    # Note: data is based on 100-day K-line
    lines.append("注: 以下技术指标基于近100日K线数据计算")
    lines.append("")

    # Dragon Tiger List specific data
    if dragon_tiger_data:
        lines.append("【龙虎榜数据】")
        net_amount = dragon_tiger_data.get("net_amount")
        if net_amount is not None:
            sign = "+" if net_amount > 0 else "-"
            lines.append(f"龙虎榜净买卖: {sign}{abs(net_amount/1e8):.2f}亿元")
        reason = dragon_tiger_data.get("reason", "")
        if reason:
            lines.append(f"上榜原因: {reason}")
        appear_count = dragon_tiger_data.get("appear_count", 0)
        if appear_count > 0:
            lines.append(f"近期上榜次数: {appear_count}次")
        lines.append("")

    # Recent price trend
    if recent_prices:
        first = recent_prices[0]
        last = recent_prices[-1]
        change = ((last['close'] - first['close']) / first['close']) * 100
        lines.append(f"近10日走势: 从{first['close']}到{last['close']}, 涨跌幅{change:.2f}%")
        lines.append(f"最新收盘价: {last['close']} CNY, 最高: {last['high']}, 最低: {last['low']}")

        avg_vol = sum(p['volume'] for p in recent_prices) / len(recent_prices)
        last_vol = recent_prices[-1]['volume']
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
        lines.append(f"成交量比: {vol_ratio:.2f} (>1放量, <1缩量)")
        lines.append("")

    # MACD signals
    macd = indicators.get("macd", {})
    if macd:
        dif, dea, hist = macd.get("dif", 0), macd.get("dea", 0), macd.get("hist", 0)
        signal = "金叉(看多)" if dif > dea else "死叉(看空)"
        lines.append(f"MACD: DIF={dif:.4f}, DEA={dea:.4f}, 柱状={hist:.4f}, 信号={signal}")
        lines.append("")

    # RSI signals
    rsi = indicators.get("rsi", {})
    if rsi:
        rsi6 = rsi.get("rsi6", 50)
        zone = "超买区(>80)" if rsi6 > 80 else "超卖区(<20)" if rsi6 < 20 else "正常区间"
        lines.append(f"RSI(6): {rsi6:.2f} - {zone}")
        lines.append("")

    # MA signals
    ma = indicators.get("ma", {})
    if ma and recent_prices:
        price = recent_prices[-1]['close']
        ma5 = ma.get("ma5", 0)
        ma20 = ma.get("ma20", 0)
        above_ma5 = "在5日均线上方" if price > ma5 else "在5日均线下方"
        above_ma20 = "在20日均线上方" if price > ma20 else "在20日均线下方"
        lines.append(f"均线: {above_ma5}, {above_ma20}")
        lines.append("")

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
            display_turnover = turnover_rate  # A-share already in percentage
            lines.append(f"换手率: {display_turnover:.2f}%")
        if total_mv is not None:
            lines.append(f"总市值: {total_mv/10000:.0f}亿元")
        lines.append("")

    # Money flow
    if money_flow_data and "error" not in money_flow_data:
        net_5d = money_flow_data.get("net_5d_total")
        if net_5d is not None and net_5d != 0:
            signal = "净流入偏多" if net_5d > 0 else "净流出偏多"
            lines.append(f"5日主力净流入: {net_5d/10000:.2f}亿元 ({signal})")
        lines.append("")

    # Financial fundamentals
    if financial_data and "error" not in financial_data:
        data = financial_data.get("data", {})
        if data:
            report_label = data.get("report_label", "--")
            ann_date = data.get("ann_date", "--")
            lines.append(f"财务指标 ({report_label}, {ann_date}发布):")

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
            total_revenue_val = data.get("total_revenue")
            total_revenue = f"{total_revenue_val/1e8:.2f}" if total_revenue_val is not None else "--"
            n_income_val = data.get("n_income")
            n_income = f"{n_income_val/1e8:.2f}" if n_income_val is not None else "--"

            lines.append(f"EPS: {eps}, BPS: {bps}, ROE: {roe}%, 毛利率: {gross_margin}%, 净利率: {netprofit_margin}%")
            lines.append(f"每股收益同比增长: {basic_eps_yoy}%, 净利润同比增长: {netprofit_yoy}%")
            lines.append(f"总营收: {total_revenue}亿元, 净利润: {n_income}亿元")
            lines.append("")

    return "\n".join(lines)


def _build_user_message(
    symbol: str,
    name: str,
    today_date: str,
    data_context: str,
    dragon_tiger_info: dict = None,
) -> str:
    """Build user message for institutional trading analysis."""
    msg_parts = []

    msg_parts.append(f"请分析股票 {name} ({symbol}) 的机构交易特征和未来走势（日期: {today_date}）。")

    if dragon_tiger_info:
        msg_parts.append(f"\n【龙虎榜信息】")
        net_amount = dragon_tiger_info.get("net_amount")
        if net_amount is not None:
            sign = "+" if net_amount > 0 else "-"
            msg_parts.append(f"龙虎榜净买卖: {sign}{abs(net_amount/1e8):.2f}亿元")
        reason = dragon_tiger_info.get("reason", "")
        if reason:
            msg_parts.append(f"上榜原因: {reason}")

    if data_context:
        msg_parts.append(f"\n## 技术数据\n{data_context}")

    msg_parts.append("\n请使用 search_with_fallback 工具搜索该股票的最近新闻，然后结合以上数据进行机构交易分析。")

    return "\n".join(msg_parts)


@traceable
def create_institutional_trading_agent():
    """Create an agent for institutional trading analysis."""
    import sys
    print("[Agent] Creating institutional trading agent...", flush=True)
    sys.stdout.flush()
    logger.info("[Agent] Creating institutional trading agent...")

    try:
        model = _get_model()
        print(f"[Agent] Model created: {type(model)}", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"[Agent] ERROR creating model: {e}", flush=True)
        sys.stdout.flush()
        raise

    today_date = get_today_date()
    print(f"[Agent] Today date: {today_date}", flush=True)
    sys.stdout.flush()

    try:
        system_prompt = load_system_prompt(today_date)
        print(f"[Agent] System prompt loaded, length: {len(system_prompt)} chars", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"[Agent] ERROR loading system prompt: {e}", flush=True)
        sys.stdout.flush()
        raise

    try:
        agent = create_deep_agent(
            model=model,
            system_prompt=system_prompt,
            tools=[search_with_fallback],
        )
        print(f"[Agent] DeepAgent created, type: {type(agent)}", flush=True)
        sys.stdout.flush()
        logger.info("[Agent] DeepAgent created successfully")
        return agent
    except Exception as e:
        print(f"[Agent] ERROR creating deep agent: {e}", flush=True)
        sys.stdout.flush()
        raise


def get_dragon_tiger_info(symbol: str) -> dict:
    """Get Dragon Tiger List info for a symbol from recent data."""
    try:
        result = AShareService.get_dragon_tiger_list(days=5)
        if result.get("error"):
            return {}

        # Look for this symbol in net_buy list
        for item in result.get("net_buy", []):
            ts_code = item.get("ts_code", "").replace(".SH", "").replace(".SZ", "")
            if ts_code == symbol:
                return {
                    "net_amount": item.get("net_amount"),
                    "reason": item.get("reason", ""),
                    "appear_count": item.get("appear_count", 0),
                }

        # Look in net_sell list
        for item in result.get("net_sell", []):
            ts_code = item.get("ts_code", "").replace(".SH", "").replace(".SZ", "")
            if ts_code == symbol:
                return {
                    "net_amount": item.get("net_amount"),
                    "reason": item.get("reason", ""),
                    "appear_count": item.get("appear_count", 0),
                }

        return {}
    except Exception as e:
        logger.warning(f"Failed to get dragon tiger info for {symbol}: {e}")
        return {}


@traceable
def analyze_institutional_trading(symbol: str, name: str) -> Dict[str, Any]:
    """Analyze institutional trading behavior for a Dragon Tiger List stock.

    Args:
        symbol: Stock symbol (e.g., "300750")
        name: Stock name (e.g., "宁德时代")

    Returns:
        Dictionary containing trend_direction, confidence, summary, and analysis blocks
    """
    logger.info(f"Starting institutional trading analysis for {name} ({symbol})")

    # Get Dragon Tiger List info
    dragon_tiger_info = get_dragon_tiger_info(symbol)

    # Step 1: Fetch K-line data and technical indicators
    kline_data = []
    indicators = {}

    try:
        kline_result = AShareService.get_kline_data(symbol, days=100)
        kline_data = kline_result.get("data", [])

        if kline_data:
            indicators = calculate_indicators(kline_data)
    except Exception as e:
        logger.warning(f"Failed to fetch technical data for {symbol}: {e}")

    # Fetch valuation metrics
    valuation_data = None
    try:
        valuation_result = AShareService.get_daily_basic(symbol, days=30)
        if "error" not in valuation_result:
            valuation_data = valuation_result
    except Exception as e:
        logger.warning(f"Failed to fetch valuation data for {symbol}: {e}")

    # Fetch money flow data
    money_flow_data = None
    try:
        money_flow_result = AShareService.get_moneyflow(symbol, days=30)
        if "error" not in money_flow_result:
            money_flow_data = money_flow_result
    except Exception as e:
        logger.warning(f"Failed to fetch money flow data for {symbol}: {e}")

    # Fetch financial fundamentals
    financial_data = None
    try:
        financial_result = AShareService.get_financial_fundamentals(symbol)
        if "error" not in financial_result:
            financial_data = financial_result
    except Exception as e:
        logger.warning(f"Failed to fetch financial fundamentals for {symbol}: {e}")

    # Step 2: Build data context
    data_context = ""
    if kline_data and indicators and not indicators.get("error"):
        recent_prices = kline_data[-10:] if len(kline_data) >= 10 else kline_data
        data_context = format_data_context(
            recent_prices,
            indicators,
            valuation_data,
            money_flow_data,
            financial_data,
            dragon_tiger_info,
        )

    # Step 3: Build user message and invoke agent
    agent = create_institutional_trading_agent()
    today_date = get_today_date()
    user_message = _build_user_message(symbol, name, today_date, data_context, dragon_tiger_info)

    logger.info(f"Invoking institutional trading agent for {symbol}...")
    logger.info(f"[Agent] User message length: {len(user_message)} chars")
    logger.info(f"[Agent] User message preview: {user_message[:300]}...")

    # Retry logic
    attempt = 0
    last_error_content = None

    while attempt <= MAX_RETRIES:
        try:
            import sys
            print(f"[Agent] Invoking agent, attempt {attempt + 1}...", flush=True)
            sys.stdout.flush()
            logger.info(f"[Agent] Invoking agent, attempt {attempt + 1}...")
            result = agent.invoke({
                "messages": [{"role": "user", "content": user_message}]
            })
            print(f"[Agent] Agent invoke returned, result type: {type(result)}", flush=True)
            sys.stdout.flush()
            logger.info(f"[Agent] Agent invoke returned, result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")

            messages = result.get("messages", [])
            if not messages:
                logger.warning(f"No messages returned for {symbol}, attempt {attempt + 1}")
                last_error_content = "No messages returned"
                attempt += 1
                continue

            final_msg = messages[-1]
            content = final_msg.content
            logger.info(f"[Agent] Final message content length: {len(content)} chars")
            logger.info(f"[Agent] Final message content preview: {content[:500]}")

            prediction = _parse_agent_output(content, symbol, name)
            logger.info(f"[Agent] Parsed prediction: {prediction}")
            if prediction:
                return {
                    "symbol": symbol,
                    "name": name,
                    "trend_direction": prediction.get("trend_direction", "neutral"),
                    "confidence": prediction.get("confidence", 0),
                    "summary": prediction.get("综合判断", {}).get("short_term_outlook", "") or prediction.get("summary", ""),
                    "宏观产业周期": prediction.get("宏观产业周期"),
                    "板块行业景气": prediction.get("板块行业景气"),
                    "公司基本面质变": prediction.get("公司基本面质变"),
                    "资金筹码结构": prediction.get("资金筹码结构"),
                    "技术形态量价": prediction.get("技术形态量价"),
                    "波段操作执行": prediction.get("波段操作执行"),
                    "综合判断": prediction.get("综合判断"),
                }

            logger.warning(f"Failed to parse agent output for {symbol}, attempt {attempt + 1}. Content preview: {content[:500]}")
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
        "机构分析": None,
    }
