## Why

We need visibility into how the stock trend analysis agent operates - what queries it makes, how it reasons, and where time is spent. LangSmith provides tracing for LLM applications and can help us debug, optimize, and understand agent behavior in production.

## What Changes

- Add LangSmith tracing configuration to backend via environment variables stored in `.env`
- Integrate LangSmith tracing into the stock trend analysis agent (`backend/services/stock_trend_agent.py`)
- Ensure all agent tool calls (Tavily searches, LLM invocations) are automatically traced
- Create a LangSmith project named `stock_analysis` for all traces

## Capabilities

### New Capabilities

- `langsmith-tracing`: Add LangSmith observability to trace all agent-related calls including LLM prompts, tool executions, and agent reasoning chains

### Modified Capabilities

- `stock-trend-analysis-agent`: No requirement changes - implementation enhancement only to add tracing

## Impact

- **Dependencies**: Adds `langsmith` Python package to backend
- **Configuration**: New environment variables added to `backend/.env` and `backend/.env.example`
- **Code Changes**: Modification to `backend/services/stock_trend_agent.py` to initialize LangSmith tracing
- **External**: Traces visible in LangSmith dashboard at `https://smith.langchain.com`
