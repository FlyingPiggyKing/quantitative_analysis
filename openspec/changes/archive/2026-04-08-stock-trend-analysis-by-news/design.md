## Context

The stock analyzer currently allows users to search for stocks, view K-line charts, and maintain a watch list. However, users have no way to get AI-powered predictions about stock price trends based on latest news and macro environment.

**Current State:**
- Backend: FastAPI with Tushare Pro API for stock data, SQLite for watch list persistence
- Frontend: Next.js with TypeScript, Tailwind CSS
- Existing DeepAgent test with MiniMax LLM (`test_minimax_agent.py`)

**Constraints:**
- Must use existing DeepAgent framework with MiniMax LLM
- Must use Tavily for web search (finance topic)
- Single-user application (no authentication in scope)
- Daily batch analysis, not real-time

## Goals / Non-Goals

**Goals:**
- Create a stock trend analysis DeepAgent with Tavily search skill
- Run daily analysis for all stocks in watch list
- Store predictions with trend direction, confidence, and summary
- Display trend indicators on watch list and detail pages
- Provide confidence percentage (0-100%)

**Non-Goals:**
- Real-time analysis (once per day is sufficient)
- Multi-user support or authentication
- Trading recommendations or buy/sell signals
- Technical indicator-based predictions (news only)

## Decisions

### 1. Tavily Search as DeepAgent Skill

**Decision:** Create a `tavily_search` skill for DeepAgent that searches with `topic="finance"` for stock-relevant news.

**Rationale:**
- Tavily provides finance-specific search with relevant results
- DeepAgent supports custom skills via `@tool` decorator
- Using `topic="finance"` filters for financial news and market analysis

**Alternatives considered:**
- Generic web search: Less relevant results, no finance topic filter
- Custom HTTP search: More complexity, Tavily already optimized for AI agents

### 2. DeepAgent System Prompt for Stock Analysis

**Decision:** Create a specialized system prompt that instructs the agent to:
1. Search for recent news about the specific stock
2. Search for macro environment factors (interest rates, GDP, industry trends)
3. Analyze sentiment and make a 2-week trend prediction
4. Provide confidence level based on news quality and consistency

**Rationale:**
- Focused prompt produces better predictions than general-purpose agent
- Explicit 2-week horizon matches user requirement
- Confidence level helps users understand prediction reliability

### 3. SQLite Database for Predictions

**Decision:** Use `trend_predictions.db` SQLite database with a `predictions` table.

**Schema:**
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    trend_direction TEXT NOT NULL,  -- 'up', 'down', or 'neutral'
    confidence INTEGER NOT NULL,     -- 0-100 percentage
    summary TEXT NOT NULL,          -- Analysis summary
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, analyzed_at)     -- One prediction per stock per day
);
```

**Rationale:**
- Same pattern as watchlist.db (SQLite, no new dependencies)
- Unique constraint ensures one prediction per stock per day
- Denormalized (symbol, name) for simple queries without joins

### 4. API Design for Trend Predictions

```
GET    /api/trend-predictions              → List all latest predictions
GET    /api/trend-predictions/{symbol}     → Get latest prediction for stock
POST   /api/trend-predictions/analyze      → Trigger analysis for a stock
POST   /api/trend-predictions/batch        → Trigger batch analysis for watchlist
```

**Rationale:**
- RESTful CRUD pattern aligned with existing API conventions
- Separate endpoints for single stock analysis vs batch
- GET endpoints for frontend display

### 5. Frontend Display

**Watch List Enhancement:**
- Add trend column showing arrow (up/down) and confidence %
- Color coding: green for up, red for down, gray for neutral

**Detail Page Enhancement:**
- Add "Trend Analysis" section showing:
  - Current prediction (up/down with confidence)
  - Analysis summary
  - Last analyzed timestamp

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  FastAPI    │────▶│  SQLite     │
│  (Next.js)  │◀────│  Backend    │◀────│  (2 DBs)    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ DeepAgent   │
                    │ + Tavily    │
                    │ + MiniMax   │
                    └─────────────┘
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Tavily API rate limits on batch analysis | Add delay between stocks, process in small batches |
| Prediction accuracy varies by stock | Show confidence level, recommend using as one input |
| News may be sparse for some stocks | Allow "insufficient data" prediction with low confidence |
| MiniMax LLM inference time | Run batch analysis as background job, not synchronous API |

## Open Questions

1. **Should analysis be triggered manually or automatically?** Decision: Manual trigger via API, can be called by a daily cron job.
2. **What if Tavily returns no results?** Return "neutral" with 0% confidence and summary "No recent news found."
3. **Should we cache Tavily results to reduce API calls?** Defer to v2 if rate limits become an issue.
