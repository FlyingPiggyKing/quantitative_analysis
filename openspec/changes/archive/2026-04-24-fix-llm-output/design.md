## Context

The stock trend analysis agent (DeepAgent) uses a LLM to generate JSON output containing trend predictions. When the LLM includes internal reasoning markers (`<think>`, ``) in the output, the JSON becomes unparseable and the result is incomplete — missing fields like `情绪分析`, `技术分析`, `趋势判断`.

The issue occurs because:
1. The system prompt instructs the model to "think step by step" internally
2. Without strict formatting constraints, some models emit reasoning artifacts into the output text
3. No validation exists to detect malformed output before it reaches downstream parsing

## Goals / Non-Goals

**Goals:**
- Ensure the agent outputs valid, parseable JSON matching the expected schema
- Detect and retry when output is malformed (contains reasoning markers or is unparseable)
- Provide a graceful fallback (return neutral trend with explanation) when retries are exhausted
- Keep the solution simple and maintainable

**Non-Goals:**
- Modify the LLM model or API endpoint configuration
- Change the output schema or contract
- Implement streaming output handling
- Add persistent caching of responses

## Decisions

### 1. Where to enforce output structure?

**Decision:** Handle in the calling code that invokes the DeepAgent (the tool/API layer), not inside the agent's system prompt.

**Rationale:** The agent is designed to be used as a reasoning engine; injecting stricter output formatting in the prompt could reduce its analytical quality. Validation at the call site is cleaner and doesn't affect the agent's behavior.

### 2. Retry strategy on malformed output

**Decision:** Retry up to 2 times (3 total attempts) with the same input, then fall back to a neutral response.

**Rationale:** Most malformed outputs are transient (model "hallucinating" formatting under load). Two retries cover the common case without excessive latency. Falling back to neutral avoids blocking the entire analysis pipeline indefinitely.

### 3. Output validation approach

**Decision:** After each LLM response, attempt to:
1. Strip `<think>...` blocks using regex (to avoid false braces inside thinking blocks)
2. Extract the JSON object using bracket-counting (handles nested JSON properly, unlike simple regex)
3. Parse and validate required fields (`trend_direction`, `confidence` — the LLM guarantees these)

**Note:** `symbol` and `name` are added by the caller, not the LLM. `summary` may be at top level OR inside `趋势判断.forecast` — the caller handles this.

**Alternative considered:** Use simple regex `\{.*\}` to extract JSON. Rejected — greedy matching fails when thinking markers contain braces inside string values.

### 4. Fallback behavior

**Decision:** When all retries fail, return:
```json
{
  "symbol": "<input_symbol>",
  "name": "<input_name>",
  "trend_direction": "neutral",
  "confidence": 0,
  "summary": "Analysis could not produce valid output after retries. Please try again later."
}
```

**Rationale:** Neutral with 0 confidence clearly signals failure without misleading the user. The error is logged for debugging.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Retry adds latency (up to 2 extra LLM calls) | Limit to 2 retries; only retry on detected malformations, not on every call |
| Regex stripping might corrupt legitimate content | Only strip known reasoning markers; if stripped content fails to parse, treat as failure |
| Fallback to neutral might mask underlying issues | Log each failure with raw output for debugging; consider alerting on high failure rates |

## Open Questions

1. Should we track retry success/failure rates to alert on degraded model quality?
2. Do we want a config flag to disable retries in testing/debugging mode?