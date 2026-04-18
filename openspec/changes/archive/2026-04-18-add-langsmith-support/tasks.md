## 1. Configuration

- [x] 1.1 Add `langsmith` package to `backend/requirements.txt`
- [x] 1.2 Add LangSmith environment variables to `backend/.env.example`
- [x] 1.3 Add LangSmith environment variables to `backend/.env` with user-provided values:
  - `LANGSMITH_TRACING=true`
  - `LANGSMITH_ENDPOINT=https://api.smith.langchain.com`
  - `LANGSMITH_API_KEY=<your-langsmith-api-key>`
  - `LANGSMITH_PROJECT=stock_analysis`

## 2. Code Integration

- [x] 2.1 Import `traceable` from `langchain.langsmith` in `backend/services/stock_trend_agent.py`
- [x] 2.2 Apply `@traceable` decorator to `analyze_stock_trend` function
- [x] 2.3 Ensure `load_dotenv()` is called before tracing initialization

## 3. Verification

- [ ] 3.1 Run a test analysis to verify traces appear in LangSmith dashboard
- [ ] 3.2 Confirm LLM prompts, tool calls, and responses are visible in trace
