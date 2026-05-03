## 1. Add market-aware search strategy to US stock prompts

- [x] 1.1 In `analyze_stock_trend()`, when `market == "US"`, modify the search instruction to include Yahoo Finance targeting: append "优先搜索 Yahoo Finance (site:finance.yahoo.com) 关于 {name} ({symbol}) 的新闻"
- [x] 1.2 Ensure A-share (market == "A") prompts remain unchanged

## 2. Verify implementation

- [x] 2.1 Confirm US stock search includes Yahoo Finance site targeting
- [x] 2.2 Confirm A-share search uses existing generic search logic
