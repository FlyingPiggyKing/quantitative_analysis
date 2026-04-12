## 1. Add imports and helper function

- [x] 1.1 Import `AkshareService` from `backend.services.akshare_service` in `stock_trend_agent.py`
- [x] 1.2 Create `format_data_context(recent_prices: list, indicators: dict) -> str` function that formats:
  - Recent 10-day price trend (start/end price, change %)
  - Latest close/high/low
  - Volume ratio (recent vs average)
  - MACD signals (DIF, DEA, histogram, golden/death cross)
  - RSI(6) value and zone (overbought/oversold/normal)
  - MA position (price vs MA5, MA20)

## 2. Modify analyze_stock_trend()

- [x] 2.1 Add try/except block at start of `analyze_stock_trend()` to fetch K-line data via `AkshareService.get_kline_data(symbol, days=60)`
- [x] 2.2 Calculate indicators via `AkshareService.calculate_indicators(kline_data)` (only if kline_data fetched successfully)
- [x] 2.3 Extract recent 10 days of prices for formatting
- [x] 2.4 Call `format_data_context()` to build technical data string
- [x] 2.5 Prepend technical data context to the user message under "## 技术数据" section
- [x] 2.6 If K-line fetch fails, proceed with original news-only flow and note in summary

## 3. Update system prompt

- [x] 3.1 Update SYSTEM_PROMPT to instruct LLM to:
  - First analyze the provided technical data (MACD, RSI, MA signals)
  - Then search for news via tavily_search
  - Weight technical signals at 40% and news sentiment at 60% when forming prediction
  - Consider whether technical signals confirm or contradict news direction
