## 1. Backend - Tavily Search Skill for DeepAgent

- [x] 1.1 Create `backend/services/tavily_search_tool.py` with Tavily search function using `@tool` decorator
- [x] 1.2 Create `backend/services/stock_trend_agent.py` with DeepAgent system prompt for stock analysis
- [x] 1.3 Define system prompt that instructs agent to search Tavily for stock news and macro environment
- [x] 1.4 Implement `analyze_stock_trend(symbol, name)` function that invokes the agent and returns prediction

## 2. Backend - Trend Prediction Storage

- [x] 2.1 Create `backend/services/trend_prediction_service.py` with SQLite database initialization
- [x] 2.2 Implement `init_db()` function to create `predictions` table if not exists
- [x] 2.3 Implement `save_prediction()` with upsert behavior (one prediction per symbol per day)
- [x] 2.4 Implement `get_latest_prediction(symbol)` to retrieve latest prediction
- [x] 2.5 Implement `get_all_latest_predictions()` to retrieve all latest predictions

## 3. Backend - Trend Prediction API Routes

- [x] 3.1 Create `backend/api/trend_prediction.py` with FastAPI router
- [x] 3.2 Implement `GET /api/trend-predictions` endpoint
- [x] 3.3 Implement `GET /api/trend-predictions/{symbol}` endpoint
- [x] 3.4 Implement `POST /api/trend-predictions/batch` endpoint to analyze all watchlist stocks
- [x] 3.5 Mount trend_prediction router in `backend/main.py`

## 4. Frontend - Trend Display API Client

- [x] 4.1 Create `frontend/src/services/trendPrediction.ts` with API client functions
- [x] 4.2 Add `getTrendPredictions()`, `getTrendPrediction(symbol)`, `runBatchAnalysis()` functions

## 5. Frontend - WatchList Component Enhancement

- [x] 5.1 Modify `frontend/src/components/WatchList.tsx` to fetch and display trend predictions
- [x] 5.2 Add trend column with up/down/neutral arrow and confidence percentage
- [x] 5.3 Apply color coding: green for up, red for down, gray for neutral

## 6. Frontend - Stock Detail Page Enhancement

- [x] 6.1 Modify `frontend/src/app/stock/[symbol]/page.tsx` to display Trend Analysis section
- [x] 6.2 Show trend direction with icon, confidence percentage, summary, and timestamp
- [x] 6.3 Handle "no prediction available" state with "Run Analysis" button
