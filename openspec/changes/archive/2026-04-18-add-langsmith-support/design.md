## Context

The stock trend analysis agent (`backend/services/stock_trend_agent.py`) uses DeepAgent with Tavily search to predict stock trends. Currently, there is no visibility into the agent's internal operations - what prompts are sent, what tool calls are made, and how the LLM reasons.

LangSmith (https://docs.langchain.com/langsmith/observability-quickstart) provides tracing for LangChain/LangGraph applications. Since our agent uses LangChain components (ChatOpenAI, tools), LangSmith can automatically trace LLM calls and tool executions.

## Goals / Non-Goals

**Goals:**
- Add LangSmith tracing to `stock_trend_agent.py` via environment variable configuration
- All agent invocations (LLM prompts, tool calls, responses) should appear in LangSmith dashboard
- Project named `stock_analysis` in LangSmith

**Non-Goals:**
- Not modifying agent logic or behavior - purely observability
- Not adding custom spans or metrics beyond automatic LangChain tracing
- Not integrating with other observability backends (Datadog, etc.)

## Decisions

### 1. Environment-based configuration

LangSmith tracing is enabled by setting environment variables:
- `LANGSMITH_TRACING=true`
- `LANGSMITH_ENDPOINT=https://api.smith.langchain.com`
- `LANGSMITH_API_KEY=<key>`
- `LANGSMITH_PROJECT=stock_analysis`

**Rationale**: This follows 12-factor app principles and keeps sensitive keys out of code. The user has provided these exact values.

### 2. Initialize tracing with `langchain.langsmith`

Using `from langchain.langsmith import traceable` decorator or `langchain_core.runnables.base RunnableLambda` to wrap the agent.

**Rationale**: The simplest integration is using LangChain's built-in `@traceable` decorator from `langchain.langsmith`. Since `create_deep_agent` returns a LangChain runnable, we can wrap the `analyze_stock_trend` function to get automatic tracing.

### 3. Add langsmith package dependency

Add `langsmith` to `backend/requirements.txt` (or pyproject.toml).

**Rationale**: LangSmith is a separate package from LangChain. The tracing functionality requires `langsmith>=0.1.0`.

## Risks / Trade-offs

- [Risk] LangSmith API rate limits on free tier → Mitigation: Only trace agent invocations, not background tasks
- [Risk] Additional latency from tracing → Mitigation: Tracing is async and minimal overhead
- [Risk] API key exposure in logs → Mitigation: Use environment variables, not hardcoded values

## Migration Plan

1. Add `langsmith` to `backend/requirements.txt`
2. Add LangSmith env vars to `backend/.env.example`
3. Add LangSmith env vars to `backend/.env` (with user's provided values)
4. Add `@traceable` decorator to `analyze_stock_trend` function
5. Verify traces appear in LangSmith dashboard
