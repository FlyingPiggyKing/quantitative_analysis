## Context

The current stock news search in `tavily_search_tool.py` uses the default `max_results=5` but has no time range restriction, potentially returning outdated news. For effective 2-week trend prediction, the DeepAgent needs to focus on the latest news from the current week to capture the most recent market sentiment.

## Goals / Non-Goals

**Goals:**
- Filter Tavily search to return only news from the current week (`time_range="week"`)
- Ensure exactly 5 latest news results per stock search
- Update DeepAgent system prompt to emphasize prioritizing latest news in analysis

**Non-Goals:**
- Changing the Tavily API key or authentication
- Modifying the response structure of the agent
- Adding new endpoints or changing the frontend

## Decisions

### Decision 1: Use Tavily `time_range="week"` parameter
**Choice**: Use `time_range="week"` in Tavily search calls instead of default (no restriction)

**Rationale**: The Tavily Python SDK supports a `time_range` parameter with options: "day", "week", "month", "year". Using "week" ensures we get news from the current 7-day window, which is ideal for short-term trend analysis.

**Alternative considered**: Use `start_date`/`end_date` for custom date range
- Rejected because `time_range="week"` is simpler and automatically adapts to current date

### Decision 2: Keep `max_results=5`
**Choice**: Keep `max_results=5` as specified in the requirements

**Rationale**: The user specifically requested "latest 5 news" - 5 results provides enough information for sentiment analysis without overwhelming the agent with redundant information.

### Decision 3: Update system prompt to prioritize latest news
**Choice**: Modify the SYSTEM_PROMPT in `stock_trend_agent.py` to instruct the agent to focus on latest news

**Rationale**: The agent should understand that latest news carries more weight for short-term prediction. Adding explicit guidance ensures consistent behavior.

## Risks / Trade-offs

- **[Risk] Tavily "week" may include news older than 7 days at edge of week**: The time_range="week" is managed by Tavily's API. Tavily determines what "week" means based on current date.
  - **Mitigation**: Accept this limitation as Tavily's interpretation aligns with our goal

- **[Risk] Fewer relevant results with time restriction**: A stock might have very limited news in the current week
  - **Mitigation**: Accept this as intentional - stale news is less relevant for 2-week prediction. The confidence scoring handles insufficient news appropriately.

## Open Questions

None - all decisions are straightforward based on user requirements and Tavily SDK capabilities.
