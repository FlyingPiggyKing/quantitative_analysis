## 1. Backend API

- [x] 1.1 Add `top_list` method to `AShareService` in `backend/services/akshare_service.py`
- [x] 1.2 Add `GET /api/stock/dragon-tiger-list` endpoint in `backend/api/stock.py`
  - Default 3 trading days, cumulative net_amount aggregation
  - Read-only; does NOT trigger AI analysis

## 2. Frontend Component

- [x] 2.1 Create `DragonTigerList` component in `frontend/src/components/DragonTigerList.tsx`
- [x] 2.2 Add API service function to fetch dragon tiger list data (read-only, no side effects)
- [x] 2.3 Implement Net Buy / Net Sell tab switching
- [x] 2.4 Implement table display with appearance count (上榜次数)

## 3. UI Integration

- [x] 3.1 Add "热门股" section header to `PresetStockList` component
- [x] 3.2 Add `DragonTigerList` to `page.tsx` below `StockMarketTabs`
- [x] 3.3 **Verify**: Dragon Tiger List stocks do NOT appear in Hot Stocks preset list
- [x] 3.4 **Verify**: Dragon Tiger List does NOT trigger trend prediction / AI analysis
