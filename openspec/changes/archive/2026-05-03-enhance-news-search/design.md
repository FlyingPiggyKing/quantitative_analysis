## Context

The stock trend analysis agent uses prompts to guide user interactions and news searches. Currently, the prompts use vague temporal references like "最新新闻" without explicit date context. This creates ambiguity when distinguishing between today's breaking news and older weekly news.

The system already has:
- `get_today_date()` utility function returning "YYYY-MM-DD" format
- Tavily search with `time_range="week"` for weekly news
- MiniMax MCP fallback search capability

## Goals / Non-Goals

**Goals:**
- Add explicit date references in user-facing messages for "未来2周趋势" analysis
- Enhance news search instruction to use two-phase search: today's news with date, then week's news

**Non-Goals:**
- Not changing the underlying search infrastructure
- Not adding new search providers
- Not modifying the analysis prediction logic

## Decisions

1. **Two-phase news search instruction**: Change single "搜索最新新闻" to "搜索今天 'YYYY-MM-DD' 最新新闻，再搜索这周的新闻"
   - Rationale: Gives agent explicit temporal boundaries for each search
   - First search focuses on breaking news with exact date
   - Second search captures weekly trend context

2. **User message date append**: Append "（日期: YYYY-MM-DD）" after the "未来2周趋势" message
   - Rationale: Provides clear temporal context to the user about when the analysis is being performed

3. **No hardcoded dates in prompts**: Use template variable `{{today_date}}` that gets populated at runtime
   - Rationale: Prompts remain static; only the injected date value changes

## Risks / Trade-offs

- [Risk] Date format mismatch between injection and search expectations
  → Mitigation: Use consistent `get_today_date()` utility for both user messages and search parameters

- [Risk] Week search may overlap with today's search results
  → Mitigation: Agent instruction should indicate today's search is for breaking news, week's search is for broader context
