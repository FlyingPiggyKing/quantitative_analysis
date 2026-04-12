## Context

The `stock_trend_agent.py` currently receives only `symbol` and `name`, searches Tavily for news, and makes predictions purely based on news sentiment. The rich technical data (K-line prices, MACD, RSI, MA) computed in `akshare_service.py` is never passed to the LLM agent. This is the primary gap limiting prediction quality.

**Current flow:**
1. `analyze_stock_trend(symbol, name)` receives symbol/name
2. Creates agent with system prompt (no technical data)
3. Sends user message requesting news search
4. LLM returns prediction based on news alone

**Desired flow:**
1. `analyze_stock_trend(symbol, name)` receives symbol/name
2. Fetches 60 days of K-line data via `AkshareService.get_kline_data()`
3. Computes technical indicators via `AkshareService.calculate_indicators()`
4. Formats recent 10-day prices + indicators as text context
5. Creates agent (system prompt updated to instruct on using technical data)
6. Sends enriched user message with technical data + news request
7. LLM combines technical signals (40%) + news sentiment (60%) for prediction
8. Returns same output format (unchanged)

## Goals / Non-Goals

**Goals:**
- Feed existing K-line and indicator data into the LLM agent context before prediction
- Enable the LLM to make informed decisions combining both technical and sentiment analysis
- Maintain the same output format for backward compatibility

**Non-Goals:**
- No changes to frontend display or API response format
- No new Tushare API calls (uses existing Akshare data only)
- No changes to the DeepAgent framework or tool definitions
- No new database tables or storage changes

## Decisions

### 1. Fetch K-line data inside `analyze_stock_trend()` before agent invocation

**Decision:** Fetch 60 days of K-line data and compute indicators inline at the start of `analyze_stock_trend()`.

**Rationale:** This keeps the change localized to a single function. The K-line data and indicators are fetched fresh for each analysis, ensuring the LLM always sees the latest data. Alternative approaches (pre-fetching, caching) add complexity without benefit for this low-volume use case.

**Alternatives considered:**
- Pre-fetch on a schedule: Adds infrastructure complexity; data may become stale between fetches and analysis
- Cache in module-level variable: Same staleness problem; adds state management complexity

### 2. Format data as human-readable text string, not structured JSON

**Decision:** `format_data_context()` returns a plain text string describing price trend, volume ratio, MACD, RSI, and MA signals in Chinese.

**Rationale:** The LLM benefits from natural language summarization over raw numbers. The formatting includes derived insights (e.g., "金叉(看多)" vs raw DIF/DEA values) to guide the LLM's interpretation. This mirrors how a human analyst would describe the charts.

**Alternatives considered:**
- Pass raw K-line JSON: Would require longer prompts and more tokens; LLM may not extract key signals as reliably
- Pass structured JSON with explicit fields: More token-efficient but less natural for the LLM to reason about; Chinese text signals are more interpretable

### 3. Weight technical signals 40%, news sentiment 60%

**Decision:** Update system prompt to instruct the LLM to weight technical analysis at 40% and news sentiment at 60%.

**Rationale:** News is typically the primary driver for 2-week stock movements, but technical signals provide important confirmation or contradiction. A 60/40 split reflects this hierarchy while ensuring technical signals are properly considered.

**Alternatives considered:**
- Equal 50/50 weighting: Underweights the news-driven nature of short-term movements
- Technical-only: Ignores news entirely, losing the original Tavily-based approach's value
- Dynamic weighting: Would require additional LLM reasoning to assess which signal is stronger; adds complexity

## Risks / Trade-offs

- **[Risk]** Longer prompt with technical data increases token usage and latency → **Mitigation:** Technical context is compact (~10 lines of text); 60-day fetch is fast; overall latency increase is acceptable
- **[Risk]** LLM may over-weight technical data if not properly prompted → **Mitigation:** Explicit 40/60 weighting in system prompt; clear instruction to analyze technical data before news search
- **[Risk]** If K-line data fetch fails, analysis should still proceed with news-only → **Mitigation:** Wrap data fetch in try/except; if fetch fails, proceed with original news-only flow and note in summary

## Open Questions

- Should `format_data_context()` also include Bollinger Bands or other indicators? (Deferred to future enhancement if needed)
- Should technical data be cached for a few minutes to avoid redundant fetches on repeated calls? (Not needed for current usage patterns)
