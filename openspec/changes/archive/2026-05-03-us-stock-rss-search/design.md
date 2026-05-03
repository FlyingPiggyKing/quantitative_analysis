## Context

Currently, `analyze_stock_trend()` uses `search_with_fallback` which relies on MiniMax MCP (primary) and Tavily (fallback). For US stocks, this approach returns inconsistent results - often Chinese news sources that aren't relevant to US stock analysis.

Yahoo Finance RSS provides authoritative, up-to-date news for US stocks but requires proxy access. The challenge is:
1. RSS provides only titles and short summaries
2. Yahoo Finance article pages are SPA (JavaScript-rendered), cannot be scraped directly
3. MiniMax MCP can search but returns inconsistent source quality

## Goals / Non-Goals

**Goals:**
- Use Yahoo Finance RSS for authoritative US stock news list
- Let Agent intelligently select Top 5 most relevant news
- Use MiniMax search to supplement with additional details
- Zero additional cost (uses existing MiniMax MCP + proxy)

**Non-Goals:**
- Not implementing full article content extraction
- Not changing A-share news search logic
- Not replacing existing Tavily fallback (keep for robustness)

## Decisions

1. **RSS-first for US stocks**: Fetch Yahoo Finance RSS via proxy as primary news source
   - Rationale: Yahoo Finance is authoritative for US stocks, RSS is lightweight and free
   - Proxy required for access from China

2. **Agent-driven selection**: Pass RSS items to Agent for Top 5 selection
   - Rationale: Agent can assess importance and timeliness better than rigid rules
   - Selection based on: relevance to stock, recency, impact potential

3. **MiniMax search for details**: Use selected news titles for focused search
   - Rationale: MiniMax is free and can provide additional context
   - Search query: Use RSS news title directly

4. **Two-phase search for US**: Combine RSS content + MiniMax search results
   - Rationale: RSS gives authoritative list, MiniMax fills in details

## Risks / Trade-offs

- [Risk] Proxy dependency - if proxy fails, RSS fetch fails
  → Mitigation: Fallback to existing MiniMax search if RSS fails

- [Risk] RSS items are short summaries, not full articles
  → Mitigation: MiniMax search provides additional details; summaries sufficient for sentiment analysis

- [Risk] Agent selection adds latency (extra LLM call)
  → Mitigation: Selection is fast; worth cost for relevance improvement
