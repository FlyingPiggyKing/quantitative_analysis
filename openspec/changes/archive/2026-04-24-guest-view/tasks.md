## 1. Frontend - Public Routes Setup

- [x] 1.1 Verify home page route `/` is accessible without authentication
- [x] 1.2 Verify stock search page is accessible without authentication
- [x] 1.3 Verify stock detail page `/stock/{symbol}` is accessible without authentication
- [x] 1.4 Add preset stocks configuration (601318, 300750, 688981, 601899, 600938)

## 2. Frontend - Guest Action Handling

- [x] 2.1 Add login/register modal component for guest users
- [x] 2.2 Update "Add to Watchlist" button to show auth prompt for guests
- [x] 2.3 Update "Remove" button on watchlist items to show auth prompt for guests
- [x] 2.4 Update "立刻分析" button to show auth prompt for guests
- [x] 2.5 Hide "Add to Watchlist" button on preset stock list (guest view)

## 3. Backend - API Audit

- [x] 3.1 Verify `/api/stock/{symbol}` returns data without authentication
- [x] 3.2 Verify `/api/stock/{symbol}/realtime` returns data without authentication
- [x] 3.3 Verify `/api/stock/search` returns data without authentication
- [x] 3.4 Verify `/api/watchlist` requires authentication
- [x] 3.5 Verify `/api/watchlist/{symbol}` (POST) requires authentication
- [x] 3.6 Verify `/api/trend-predictions/{symbol}` requires authentication

## 4. Integration Testing

- [ ] 4.1 Test guest user can view preset stocks on home page
- [ ] 4.2 Test guest user can search and view stock details
- [ ] 4.3 Test guest user sees login prompt when clicking "Add to Watchlist"
- [ ] 4.4 Test guest user sees login prompt when clicking "立刻分析"
- [ ] 4.5 Test authenticated user can add stock to watchlist
- [ ] 4.6 Test authenticated user can trigger trend analysis
