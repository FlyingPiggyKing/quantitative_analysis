## ADDED Requirements

### Requirement: LangSmith Tracing for Stock Trend Agent
The backend SHALL send traces to LangSmith for all stock trend analysis agent invocations, capturing LLM prompts, tool executions, and responses.

#### Scenario: LangSmith tracing enabled via environment variables
- **WHEN** environment variables `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` are set
- **THEN** all calls to `analyze_stock_trend()` SHALL produce traces in LangSmith project `stock_analysis`

#### Scenario: Agent LLM calls are traced
- **WHEN** the DeepAgent invokes the LLM (ChatOpenAI/MiniMax)
- **THEN** the prompt, model parameters, and response SHALL appear as a span in LangSmith

#### Scenario: Tool calls are traced
- **WHEN** the agent calls `tavily_search` tool
- **THEN** the search query and results SHALL appear as a child span in LangSmith

#### Scenario: Tracing does not modify agent behavior
- **WHEN** LangSmith tracing is enabled or disabled
- **THEN** the agent SHALL produce identical analysis results
- **AND** tracing SHALL only add observability, not alter functionality

#### Scenario: Configuration via .env file
- **WHEN** `backend/.env` contains LangSmith environment variables
- **THEN** the tracing SHALL be activated when the backend service starts
