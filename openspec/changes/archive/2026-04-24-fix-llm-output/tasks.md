## 1. Add output validation and retry utilities

- [x] 1.1 Add `_strip_reasoning_markers()` function to remove `<think>...` blocks from LLM output
- [x] 1.2 Add `_is_valid_prediction()` function to check required fields (`symbol`, `name`, `trend_direction`, `confidence`, `summary`)
- [x] 1.3 Add `_parse_agent_output()` function combining marker stripping and JSON parsing

## 2. Implement retry logic in analyze_stock_trend

- [x] 2.1 Wrap the agent invocation in a retry loop (up to 3 attempts total)
- [x] 2.2 On malformed output, log the raw content and retry
- [x] 2.3 When all retries fail, return neutral fallback with `confidence: 0`

## 3. Test the implementation

- [x] 3.1 Verify malformed output (with `<think>` markers) is correctly handled
- [x] 3.2 Verify retry mechanism triggers on parsing failure
- [x] 3.3 Verify fallback response is returned after exhausting retries