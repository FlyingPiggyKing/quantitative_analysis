## Why

Retail investors lack timely, structured market news intelligence during trading hours. They must manually scan multiple sources to understand what news drove the market in the past hour. A hourly news analysis agent would automatically collect, summarize, and categorize market news impact, saving time and improving decision-making.

## What Changes

1. **New hourly news collection service** - Uses Tushare's `tushare_news` API to fetch news from the past hour at market close
2. **New news analysis agent** - `news_analysis_agent.py` that analyzes hourly news and outputs: Top 3 news points, market impact, sector impact
3. **New agent prompt** - `news_analysis_agent.txt` in `backend/services/agent_prompts/`
4. **New background task queue** - `news_analysis_task_queue.py` running on a scheduled hourly basis in a separate thread
5. **New database storage** - `hourly_news` table storing summarized news with timestamp
6. **New frontend block** - "小时资讯" block in the investment analysis module showing last 3 hours of news summaries
7. **New sub-module tab** - "盘面新闻" sub-module in analysis module

## Capabilities

### New Capabilities
- `hourly-news-analysis`: Hourly automated news collection and AI-powered summarization with market/sector impact analysis
- `hourly-news-display`: Frontend block displaying 3-hour rolling news summaries in the investment analysis module

### Modified Capabilities
- (none)

## Impact

**Backend:**
- New service: `backend/services/news_analysis_agent.py`
- New task queue: `backend/services/news_analysis_task_queue.py`
- New prompt: `backend/services/agent_prompts/news_analysis_agent.txt`
- New API endpoint: `backend/api/hourly_news.py`
- Database: new `hourly_news` table in `trend_predictions.db`
- Scheduler: hourly cron job to trigger news collection

**Frontend:**
- New component: `frontend/src/components/HourlyNewsPanel.tsx`
- Modified `SubModuleTabs.tsx` to add "盘面新闻" sub-module tab
- New service: `frontend/src/services/hourlyNews.ts`

**Dependencies:**
- Tushare Pro API (existing)
- MiniMax LLM API (existing)
- Threading/scheduler infrastructure (existing pattern from institutional_trading_analysis_task_queue.py)
