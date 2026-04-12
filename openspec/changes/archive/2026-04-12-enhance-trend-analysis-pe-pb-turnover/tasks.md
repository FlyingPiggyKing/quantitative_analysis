## 1. Backend: Valuation Data Service

- [x] 1.1 Add `get_daily_basic(symbol, days)` static method to `AkshareService` in `backend/services/akshare_service.py` — fetches PE(TTM), PB, turnover_rate, total_mv, circ_mv from `pro.daily_basic()` with date range, sorts by date, returns `{symbol, data, latest}` or `{symbol, error}`
- [x] 1.2 Add graceful degradation: catch all exceptions and return `{symbol, error}` dict so callers never receive an unhandled exception from `get_daily_basic`

## 2. Backend: API Endpoint

- [x] 2.1 Add `GET /api/stock/{symbol}/valuation` endpoint to `backend/api/stock.py` with `days` query param (default=30, range 1–365), delegating to `AkshareService.get_daily_basic()`

## 3. Backend: LLM Agent Context Integration

- [x] 3.1 In the agent service (file containing `format_data_context`), call `get_daily_basic()` during the data-fetching phase before context assembly
- [x] 3.2 In `format_data_context()`, add a valuation section that appends PE(TTM), PB, turnover rate, and total market cap lines — skip section if `error` key is present in valuation data

## 4. Frontend: Valuation API Client

- [x] 4.1 Add `fetchStockValuation(symbol, days)` function to the frontend API client that calls `/api/stock/{symbol}/valuation`

## 5. Frontend: Valuation Panel on Stock Detail Page

- [x] 5.1 In `frontend/src/app/stock/[symbol]/page.tsx`, fetch valuation data on page load alongside existing data fetches
- [x] 5.2 Add a valuation summary row/card showing PE(TTM), PB, turnover rate (%), and total market cap (万元) — display "N/A" for missing values
- [x] 5.3 Wire the existing `PETrendSparkline` component (already in `frontend/src/components/PETrendSparkline.tsx`) to display PE(TTM) history from the `data` array returned by the valuation endpoint
