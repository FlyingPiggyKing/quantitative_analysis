# Implementation Tasks

## 1. Agent Prompt & Backend Foundation

- [x] 1.1 Create `backend/services/agent_prompts/institutional_trading_analysis_agent.txt` with system prompt following 六维双轮选股.md content
- [x] 1.2 Create `backend/services/institutional_trading_analysis_agent.py` based on `stock_trend_agent.py` pattern, with:
  - `get_system_prompt()` function loading from text file
  - `format_data_context()` helper
  - `analyze_institutional_trading()` main function
  - `_build_user_message()` for constructing prompts
  - `_parse_agent_output()` for JSON parsing
  - `_get_model()` for ChatOpenAI initialization
- [x] 1.3 Create `backend/services/institutional_trading_analysis_task_queue.py` with:
  - `InstitutionalTradingAnalysisTaskQueue` class (ThreadPoolExecutor, max_workers=3)
  - `submit_institutional_analysis_task()` function
  - `get_institutional_task_status()` function
  - Task status tracking (PENDING, RUNNING, COMPLETED, FAILED)

## 2. API Routes

- [x] 2.1 Create `backend/api/institutional_trading_analysis.py` with endpoints:
  - `POST /api/institutional-analysis/{symbol}/force-async` - Submit analysis to queue
  - `GET /api/institutional-analysis/task/{task_id}` - Poll task status
- [x] 2.2 Register router in `backend/main.py` with prefix `/api/institutional-analysis`
- [x] 2.3 Reuse `TrendPredictionService` for saving/retrieving analysis results (do not create new service)

## 3. Frontend Service Layer

- [x] 3.1 Create `frontend/src/services/institutionalTradingAnalysis.ts` with:
  - `runInstitutionalAnalysisAsync(symbol)` - Submit to queue
  - `getInstitutionalAnalysisTaskStatus(taskId)` - Poll status
  - Types matching backend API responses

## 4. Frontend Detail Page

- [x] 4.1 Create `frontend/src/app/stock/dragon-tiger/[symbol]/page.tsx` with:
  - Header with stock name, symbol, price, change
  - "← 返回" link
  - "AI 趋 势 分 析" section with 立刻分析 button
  - Loading, error, and results states
  - TrendDirectionBadge component
  - Auth modal integration
- [x] 4.2 Create `frontend/src/components/DragonTigerStockDetail.tsx` (optional shared component if needed)

## 5. DragonTigerList Update

- [x] 5.1 Update `frontend/src/components/DragonTigerList.tsx` to:
  - Change Link href from `/stock/{symbol}` to `/stock/dragon-tiger/{symbol}`
  - Only applies to 6-digit A-share symbols (not HK/US)
- [x] 5.2 Add AI龙虎预测 column to DragonTigerList table:
  - Desktop: Display date in header (right of title), combine code+name into single column, add AI prediction column with prediction icons (▲/▼/◆ + confidence%)
  - Mobile: Show "AI龙虎" label with vt-pred-col-header style, display prediction inline with other data
  - Auto-fetch prediction on component mount, show prediction icon if available, dash if not
  - Prediction icons styled with vt-pred-up/vt-pred-down/vt-pred-flat classes (same as AI下周预测)
- [x] 5.3 DragonTigerList displayed on homepage for both logged-in users (below WatchList) and non-logged-in users

## 6. Verification

- [x] 6.1 Verify backend starts without errors
- [x] 6.2 Verify frontend builds without errors
- [x] 6.3 Test clicking a Dragon Tiger List stock navigates to new detail page
- [x] 6.4 Test "立刻分析" button triggers analysis and displays results
- [x] 6.5 Verify existing `/stock/[symbol]` page still works correctly
