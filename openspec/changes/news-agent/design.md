## Context

This project is a quantitative analysis platform for China A-Stocks, HK stocks, and US stocks. The current system provides institutional trading analysis, dragon tiger list tracking, sector money flow visualization, and index metrics. However, there is no automated hourly news intelligence - users must manually search for news during trading hours.

The backend uses Python with FastAPI, SQLite database, Tushare for A-share data, and FutuAPI for HK/US data. The frontend is a Next.js application with module tabs for watchlist and analysis views.

## Goals / Non-Goals

**Goals:**
- Automatically collect news every hour during trading hours using Tushare's `tushare_news` API
- Generate AI-powered news summaries with Top 3 news points, market impact, and sector impact
- Store hourly news summaries in SQLite database
- Display 3-hour rolling news summaries in the investment analysis module
- Run news collection in a background thread to avoid blocking user interactions

**Non-Goals:**
- Real-time news streaming (hourly is sufficient for retail investors)
- News from sources other than Tushare (at least for initial implementation)
- Automatic trading based on news (analysis only, no execution)

## Decisions

### 1. Tushare News API for hourly collection

**Decision**: Use Tushare's `tushare_news` API to fetch news at the end of each hour.

**Rationale**:
- Tushare is already an established data provider in this project (see `akshare_service.py`)
- The API provides news with timestamps that can be filtered by hour
- Alternative: scrap financial news websites would be more complex and less reliable

**Alternative considered**: Use MiniMax MCP search or Tavily for news - rejected because these are web search tools, not structured financial news APIs.

### 2. Agent pattern following institutional_trading_analysis_agent

**Decision**: Create `news_analysis_agent.py` following the same structure as `institutional_trading_analysis_agent.py`.

**Rationale**:
- Consistent with existing codebase patterns
- Reuses the same LLM model (MiniMax) and agent creation pattern
- The existing agent has proven to work with retry logic and error handling

**Alternative considered**: Create a simpler function-based approach - rejected because the agent pattern provides better structured output and the ability to use tools.

### 3. Separate thread pool for news tasks

**Decision**: Use a dedicated `ThreadPoolExecutor` with `max_workers=1` for news analysis, separate from the institutional trading analysis pool.

**Rationale**:
- News analysis runs hourly and should not compete with on-demand institutional analysis
- A single worker is sufficient since news collection is a sequential per-hour task
- Using separate pools prevents news tasks from affecting user-initiated analysis

**Alternative considered**: Reuse the institutional analysis task queue - rejected because news analysis has different timing requirements (hourly vs on-demand) and should be independently managed.

### 4. SQLite storage for news summaries

**Decision**: Store hourly news summaries in `hourly_news` table in the existing `trend_predictions.db`.

**Rationale**:
- Follows existing database pattern in the project
- No need for a separate database
- Simple schema: id, hour_timestamp, summary_json, created_at

**Alternative considered**: Create a separate database - rejected for simplicity.

### 5. Frontend display as new sub-module tab

**Decision**: Add "盘面新闻" as a new sub-module tab in the analysis module, alongside "龙虎榜", "资金流向", "指数指标".

**Rationale**:
- Consistent with existing navigation pattern
- Logical grouping with other market analysis features
- "小时资讯" block shows last 3 hours of news summaries with time labels (e.g., "9:00", "10:00")

**Alternative considered**: Add as a separate top-level module - rejected because news is part of market analysis, not a standalone feature.

## Risks / Trade-offs

**[Risk] Tushare API rate limiting**
→ **Mitigation**: The hourly job only makes one API call per hour, which is well within rate limits. If rate limiting occurs, the job will log an error and retry at the next hour.

**[Risk] LLM API failure during news analysis**
→ **Mitigation**: Retry logic (3 attempts) similar to institutional_trading_analysis_agent. If all retries fail, store an error summary in the database.

**[Risk] News outside trading hours**
→ **Mitigation**: The scheduler will still run hourly, but will fetch "recent" news (past 2 hours) to handle edge cases where market news is published outside strict trading hours.

**[Risk] Database growth over time**
→ **Mitigation**: Implement a cleanup routine to delete news older than 7 days on startup.

## Migration Plan

1. **Phase 1 - Backend** (Day 1):
   - Create `backend/services/news_analysis_agent.py`
   - Create `backend/services/agent_prompts/news_analysis_agent.txt`
   - Create `backend/services/news_analysis_task_queue.py`
   - Create `backend/api/hourly_news.py`
   - Add `hourly_news` table migration

2. **Phase 2 - Scheduler** (Day 1):
   - Integrate hourly scheduler in `backend/main.py`
   - Test scheduler runs correctly

3. **Phase 3 - Frontend** (Day 2):
   - Create `frontend/src/components/HourlyNewsPanel.tsx`
   - Create `frontend/src/services/hourlyNews.ts`
   - Update `SubModuleTabs.tsx` to add "盘面新闻" tab
   - Update page.tsx to pass new sub-module content

4. **Phase 4 - Testing** (Day 2):
   - Test end-to-end: verify news is collected, stored, and displayed correctly
   - Test error handling and retries

## Open Questions

1. **Should news collection run during pre-market or after-hours?** - For now, run only during trading hours (9:30-15:00) but fetch "recent" news to capture after-hours significant announcements.

2. **Should we filter news by relevance score?** - Tushare news API may return news with a relevance score. We could filter out low-relevance news to reduce LLM processing. Decision: filter out news with relevance < 0.5 initially.
