## 1. Backend - Database Setup

- [x] 1.1 Create `backend/services/watchlist_service.py` with SQLite database initialization
- [x] 1.2 Implement `init_db()` function to create `watchlist` table if not exists

## 2. Backend - Watchlist API Routes

- [x] 2.1 Create `backend/api/watchlist.py` with FastAPI router
- [x] 2.2 Implement `GET /api/watchlist` with pagination (page, page_size)
- [x] 2.3 Implement `POST /api/watchlist` to add stock
- [x] 2.4 Implement `DELETE /api/watchlist/{symbol}` to remove stock
- [x] 2.5 Implement `GET /api/watchlist/{symbol}` to check if stock is watched
- [x] 2.6 Mount watchlist router in `backend/main.py`

## 3. Frontend - Watchlist API Client

- [x] 3.1 Create `frontend/src/services/watchlist.ts` with API client functions
- [x] 3.2 Add `getWatchlist()`, `addToWatchlist()`, `removeFromWatchlist()`, `checkWatchlist()` functions

## 4. Frontend - WatchList Component

- [x] 4.1 Create `frontend/src/components/WatchList.tsx` component
- [x] 4.2 Display watch list table with symbol, name, added date
- [x] 4.3 Add pagination controls (10, 20, 30 rows selector)
- [x] 4.4 Link each row to stock detail page

## 5. Frontend - Index Page Integration

- [x] 5.1 Modify `frontend/src/app/page.tsx` to include WatchList component below search form
- [x] 5.2 Fetch and display watch list on page load

## 6. Frontend - Detail Page Button

- [x] 6.1 Modify `frontend/src/app/stock/[symbol]/page.tsx` to check watchlist status on load
- [x] 6.2 Add "Add to Watch List" / "Remove from Watch List" button in header
- [x] 6.3 Implement button toggle functionality with API calls
