## 1. Database Schema

- [x] 1.1 Add `hourly_news` table migration to `backend/services/db_migration.py` with fields: id (INTEGER PRIMARY KEY), hour_timestamp (TEXT), summary_json (TEXT), created_at (FLOAT)

## 2. Backend - News Analysis Agent

- [x] 2.1 Create `backend/services/agent_prompts/news_analysis_agent.txt` with system prompt for news analysis
- [x] 2.2 Create `backend/services/news_analysis_agent.py` following institutional_trading_analysis_agent.py pattern:
  - `_get_model()` function
  - `load_system_prompt()` function
  - `create_news_analysis_agent()` function
  - `analyze_hourly_news()` function with news list input and structured output

## 3. Backend - Task Queue & Scheduler

- [x] 3.1 Create `backend/services/news_analysis_task_queue.py`:
  - `NewsAnalysisTask` dataclass
  - `NewsAnalysisTaskQueue` class with `ThreadPoolExecutor(max_workers=1)`
  - `submit_news_analysis_task()` function
  - `get_news_analysis_task_status()` function
- [x] 3.2 Add scheduler integration to `backend/main.py`:
  - Import news task queue
  - Add APScheduler or similar hourly job
  - Job runs news collection at end of each hour
  - Add cleanup of old news on startup

## 4. Backend - API Endpoint

- [x] 4.1 Create `backend/api/hourly_news.py`:
  - `GET /api/hourly_news` endpoint returning last 3 hours of news summaries
  - Response format: JSON array of {hour, top3_news, market_impact, sector_impact, created_at}

## 5. Frontend - Service Layer

- [x] 5.1 Create `frontend/src/services/hourlyNews.ts`:
  - `getHourlyNews()` function calling GET /api/hourly_news
  - Type definitions for hourly news response

## 6. Frontend - Component

- [x] 6.1 Create `frontend/src/components/HourlyNewsPanel.tsx`:
  - Display "小时资讯" block
  - Show 3 hours of news summaries with time labels
  - Display Top 3 news, market impact, sector impact for each hour
  - Handle empty state with "暂无小时资讯数据"

## 7. Frontend - Navigation Integration

- [x] 7.1 Update `frontend/src/components/SubModuleTabs.tsx`:
  - Add `news` to `AnalysisSubModule` type
  - Add "盘面新闻" tab button in analysis module tab bar
  - Add `renderNewsContent` render function prop
- [x] 7.2 Update `frontend/src/app/page.tsx`:
  - Add `HourlyNewsPanel` import
  - Add `news` to `AnalysisSubModuleType`
  - Pass `renderNewsContent` to `SubModuleTabs`
