## 1. Implement Yahoo Finance RSS fetch

- [x] 1.1 Create `fetch_yahoo_finance_rss(symbol, proxy_url)` function that fetches and parses Yahoo Finance RSS feed
- [x] 1.2 Function should return list of dicts with: title, description, link, pubDate
- [x] 1.3 Handle errors (timeout, proxy error, parse error) and return empty list with warning log

## 2. Modify analyze_stock_trend for US stocks RSS workflow

- [x] 2.1 In `analyze_stock_trend()`, when `market == "US"`, call `fetch_yahoo_finance_rss()` first
- [x] 2.2 If RSS returns items, pass them to Agent with instruction to select Top 5 based on importance and timeliness
- [x] 2.3 If RSS fails or returns empty, fall back to existing `search_with_fallback()` approach

## 3. Implement Agent-driven news selection

- [x] 3.1 Add system prompt instruction for Agent to select Top 5 most relevant news items
- [x] 3.2 Agent should prioritize: stock mentions, recency, significant events (earnings, M&A)
- [x] 3.3 For each selected item, generate a search query string

## 4. Implement focused MiniMax search

- [x] 4.1 For each selected Top 5 news item, call `search_with_fallback()` with the news title as query
- [x] 4.2 Merge RSS items with MiniMax search results
- [x] 4.3 Pass combined news context to final analysis Agent

## 5. Verify and test

- [ ] 5.1 Test RSS fetch with proxy for US stock symbol (e.g., EBAY, GOOGL)
- [ ] 5.2 Test complete workflow with a US stock
- [ ] 5.3 Verify A-share workflow remains unchanged
