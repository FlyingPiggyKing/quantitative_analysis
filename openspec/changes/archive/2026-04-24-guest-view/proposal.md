## Why

Currently, all stock information requires user login to access. This creates friction for first-time visitors who want to explore the platform before committing to registration. By allowing guest access to basic stock information and search, we can improve user acquisition and demonstrate value before requiring account creation.

## What Changes

- Home page displays 5 preset stocks (601318, 300750, 688981, 601899, 600938) without authentication
- Stock search and detail pages are accessible to unauthenticated users
- Adding stocks to watchlist requires authenticated user
- Trend analysis features require authenticated user
- Login/register prompts appear when guests attempt restricted actions

## Capabilities

### New Capabilities
- `public-stock-access`: Allow unauthenticated users to view preset stock list, search stocks, and view stock details without authentication
- `preset-stocks`: Define the 5 default stocks visible to guest users (601318, 300750, 688981, 601899, 600938)

### Modified Capabilities
- `watch-list-display`: Adding stocks to watchlist requires authentication (currently no auth requirement specified)
- `stock-trend-analysis`: Trend analysis trigger requires authentication (currently no auth requirement specified)

## Impact

- Frontend: Update routes to allow public access to home page, stock search, and stock detail pages
- Frontend: Add login/register modal or redirect for authenticated-only actions
- Backend: Review API endpoints to ensure read operations allow guest access
- Backend: Ensure mutation operations (add to watchlist, trigger analysis) require authentication
