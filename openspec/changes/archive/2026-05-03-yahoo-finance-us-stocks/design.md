## Context

Currently `search_with_fallback` uses a generic search approach that works for both US and A-share stocks. However, Yahoo Finance provides high-quality, curated analysis articles specifically for US stocks (e.g., `https://finance.yahoo.com/markets/stocks/articles/...`). These articles are more authoritative for US stock analysis than generic web results.

The system already distinguishes between US and A-share markets using the `market` variable in `analyze_stock_trend()`.

## Goals / Non-Goals

**Goals:**
- Prioritize Yahoo Finance news for US stock analysis
- Keep A-share search behavior unchanged
- Seamless fallback if Yahoo Finance search fails

**Non-Goals:**
- Not creating a new search tool - modifying the prompt/strategy
- Not changing the underlying search infrastructure

## Decisions

1. **Market-specific search strategy**: Use `market` variable to determine search approach
   - US market: Construct Yahoo Finance-focused search query
   - A-share: Use existing generic search logic

2. **Yahoo Finance URL pattern search**: Target Yahoo Finance article pages
   - Query format: `[stock name] site:finance.yahoo.com`
   - This filters results to Yahoo Finance articles specifically

3. **Fallback chain for US stocks**:
   - First: Yahoo Finance search via `search_with_fallback`
   - Then: Generic stock news search if Yahoo Finance returns no results

## Risks / Trade-offs

- [Risk] Yahoo Finance articles may be limited to US trading hours
  → Mitigation: Generic fallback ensures some news coverage even if Yahoo Finance is sparse

- [Risk] site: search operator may be too restrictive
  → Mitigation: Fallback to generic search provides broader coverage
