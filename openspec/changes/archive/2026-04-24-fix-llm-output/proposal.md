## Why

The LLM-based stock trend analysis agent occasionally produces malformed JSON output containing internal reasoning markers (e.g., `<think>` blocks) mixed with the actual JSON response. This corrupts the output, causing downstream parsing to fail and resulting in incomplete trend predictions (missing fields like `情绪分析`, `技术分析`, `趋势判断`). This needs to be fixed to ensure reliable stock analysis results.

## What Changes

- Add structured output enforcement for the stock trend analysis agent to prevent internal reasoning from leaking into JSON output
- Implement output validation and retry logic with proper error handling
- Add a fallback mechanism when JSON parsing fails after retries
- Improve the prompt to explicitly instruct the model to output clean JSON without reasoning artifacts

## Capabilities

### New Capabilities

- `structured-output-enforcement`: Mechanism to ensure LLM outputs valid, parseable JSON without internal reasoning artifacts. Includes retry logic and graceful degradation when output remains invalid.

## Impact

- Affects the stock trend analysis agent (DeepAgent) output handling
- No changes to existing specs or API contracts — this is a reliability improvement