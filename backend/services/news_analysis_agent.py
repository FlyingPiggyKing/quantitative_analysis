"""News analysis agent for hourly market news summarization."""
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import date
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from langsmith import traceable

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _extract_json_object(content: str) -> Optional[str]:
    """Extract the first JSON object from agent output."""
    # Try to find JSON object pattern
    pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(0)

    # Fallback: find first '{' and count brackets
    cleaned = content.strip()

    # Try to strip markdown code blocks
    if cleaned.startswith('```'):
        lines = cleaned.split('\n')
        if len(lines) >= 2:
            cleaned = '\n'.join(lines[1:-1])
            if cleaned.strip().endswith('```'):
                cleaned = cleaned.strip()[:-3].strip()

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


def _is_valid_news_analysis(analysis: dict) -> bool:
    """Check if analysis dict has required fields."""
    required_fields = ['top3_news', 'market_impact']
    if not all(field in analysis and analysis[field] is not None for field in required_fields):
        return False
    if not isinstance(analysis.get('top3_news'), list):
        return False
    return True


def _parse_agent_output(content: str) -> dict | None:
    """Extract and parse JSON from agent output. Returns None if parsing fails."""
    json_str = _extract_json_object(content)
    if not json_str:
        stripped = content.strip()
        if stripped.startswith('```'):
            lines = stripped.split('\n')
            if len(lines) >= 2:
                json_str = '\n'.join(lines[1:-1])
                if json_str.strip().endswith('```'):
                    json_str = json_str.strip()[:-3].strip()

    if not json_str:
        return None

    try:
        analysis = json.loads(json_str)
        if not _is_valid_news_analysis(analysis):
            logger.warning(f"_is_valid_news_analysis failed. Fields: {list(analysis.keys())}")
            return None
        return analysis
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error: {e}")
        return None


def get_today_date() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


def load_system_prompt(today_date: str) -> str:
    """Load system prompt from external file and inject today's date."""
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "agent_prompts",
        "news_analysis_agent.txt"
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


@traceable
def create_news_analysis_agent():
    """Create an agent for news analysis."""
    import sys
    print("[NewsAgent] Creating news analysis agent...", flush=True)
    sys.stdout.flush()
    logger.info("[NewsAgent] Creating news analysis agent...")

    try:
        model = _get_model()
        print(f"[NewsAgent] Model created: {type(model)}", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"[NewsAgent] ERROR creating model: {e}", flush=True)
        sys.stdout.flush()
        raise

    today_date = get_today_date()
    print(f"[NewsAgent] Today date: {today_date}", flush=True)
    sys.stdout.flush()

    try:
        system_prompt = load_system_prompt(today_date)
        print(f"[NewsAgent] System prompt loaded, length: {len(system_prompt)} chars", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"[NewsAgent] ERROR loading system prompt: {e}", flush=True)
        sys.stdout.flush()
        raise

    try:
        agent = create_deep_agent(
            model=model,
            system_prompt=system_prompt,
            tools=[],
        )
        print(f"[NewsAgent] DeepAgent created, type: {type(agent)}", flush=True)
        sys.stdout.flush()
        logger.info("[NewsAgent] DeepAgent created successfully")
        return agent
    except Exception as e:
        print(f"[NewsAgent] ERROR creating deep agent: {e}", flush=True)
        sys.stdout.flush()
        raise


def format_news_for_agent(news_list: List[Dict[str, Any]]) -> str:
    """Format news list as readable text for the agent."""
    if not news_list:
        return "No news available for this hour."

    lines = []
    lines.append(f"过去1小时共获取 {len(news_list)} 条新闻:\n")

    for i, news in enumerate(news_list, 1):
        lines.append(f"--- 新闻 {i} ---")
        lines.append(f"时间: {news.get('datetime', 'N/A')}")
        lines.append(f"标题: {news.get('title', 'N/A')}")
        lines.append(f"内容: {news.get('content', 'N/A')[:200]}..." if news.get('content') else "内容: N/A")
        lines.append(f"来源: {news.get('source', 'N/A')}")
        lines.append(f"相关性: {news.get('relevance', 0):.2f}")
        lines.append("")

    return "\n".join(lines)


def _build_user_message(news_list: List[Dict[str, Any]], today_date: str) -> str:
    """Build user message for news analysis."""
    news_text = format_news_for_agent(news_list)

    msg_parts = []
    msg_parts.append(f"请分析以下过去1小时的市场新闻（日期: {today_date}）。\n")
    msg_parts.append("## 新闻列表\n")
    msg_parts.append(news_text)
    msg_parts.append("\n请使用上述新闻列表进行分析，输出结构化的市场影响和板块影响分析。")

    return "\n".join(msg_parts)


@traceable
def analyze_hourly_news(news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze a list of news items and produce structured hourly news summary.

    Args:
        news_list: List of news items with fields: datetime, title, content, source, relevance

    Returns:
        Dictionary containing top3_news, market_impact, and sector_impact
    """
    logger.info(f"Starting news analysis for {len(news_list)} news items")

    # Filter low-relevance news
    filtered_news = [n for n in news_list if n.get('relevance', 0) >= 0.5]
    if filtered_news:
        logger.info(f"Filtered to {len(filtered_news)} high-relevance news items (relevance >= 0.5)")
    else:
        filtered_news = news_list
        logger.info("No high-relevance news found, using all news")

    # Build user message and invoke agent
    agent = create_news_analysis_agent()
    today_date = get_today_date()
    user_message = _build_user_message(filtered_news, today_date)

    logger.info(f"Invoking news analysis agent...")
    logger.info(f"[NewsAgent] User message length: {len(user_message)} chars")

    # Retry logic
    attempt = 0
    last_error_content = None

    while attempt <= MAX_RETRIES:
        try:
            import sys
            print(f"[NewsAgent] Invoking agent, attempt {attempt + 1}...", flush=True)
            sys.stdout.flush()
            logger.info(f"[NewsAgent] Invoking agent, attempt {attempt + 1}...")

            result = agent.invoke({
                "messages": [{"role": "user", "content": user_message}]
            })
            print(f"[NewsAgent] Agent invoke returned, result type: {type(result)}", flush=True)
            sys.stdout.flush()

            messages = result.get("messages", [])
            if not messages:
                logger.warning(f"No messages returned, attempt {attempt + 1}")
                last_error_content = "No messages returned"
                attempt += 1
                continue

            final_msg = messages[-1]
            content = final_msg.content
            logger.info(f"[NewsAgent] Final message content length: {len(content)} chars")
            logger.info(f"[NewsAgent] Final message content preview: {content[:500]}")

            analysis = _parse_agent_output(content)
            logger.info(f"[NewsAgent] Parsed analysis: {analysis}")

            if analysis:
                return {
                    "top3_news": analysis.get("top3_news", []),
                    "market_impact": analysis.get("market_impact", {"direction": "中性", "reason": "无法确定"}),
                    "sector_impact": analysis.get("sector_impact", []),
                }

            logger.warning(f"Failed to parse agent output, attempt {attempt + 1}. Content preview: {content[:500]}")
            last_error_content = content
            attempt += 1

        except Exception as e:
            logger.error(f"Agent invocation error, attempt {attempt + 1}: {e}")
            last_error_content = str(e)
            attempt += 1

    # All retries exhausted
    logger.error(f"All {MAX_RETRIES + 1} attempts failed. Last error: {last_error_content}")
    return {
        "top3_news": [],
        "market_impact": {"direction": "中性", "reason": "分析失败，请稍后重试"},
        "sector_impact": [],
    }
