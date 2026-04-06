## Why

Users need a way to save stocks they're interested in for quick access. Currently, users must remember and manually search for stocks each session. Adding a watch list allows users to track their favorite stocks persistently.

## What Changes

1. **Index page**: Add a watch list section below the stock search box that displays user's saved stocks
2. **Stock detail page**: Add "Add to Watch List" / "Remove from Watch List" toggle button in the header
3. **Database**: Add a watch list table to store user-stock relationships (user ID, stock symbol, added timestamp)
4. **Backend API**: New endpoints for watch list CRUD operations
5. **Pagination controls**: Watch list displays 10, 20, or 30 rows based on user selection

## Capabilities

### New Capabilities
- `stock-watch-list`: Ability to save/remove stocks to a personal watch list, stored persistently in the database. Supports pagination with 10, 20, 30 rows per page.
- `watch-list-display`: Display the watch list on the index page below the search input, showing stock symbol, name, and latest price.

### Modified Capabilities
- (none - this is a new feature)

## Impact

- **Backend**: New SQLite database file (`watchlist.db`), new API routes under `/api/watchlist`
- **Frontend**: Modified `page.tsx` (index) and `stock/[symbol]/page.tsx` (detail page)
- **Dependencies**: SQLite (via Python `sqlite3` stdlib) - no new packages needed
