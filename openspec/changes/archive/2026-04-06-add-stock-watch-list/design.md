## Context

The stock analyzer currently allows users to search for stocks and view K-line charts with technical indicators. However, users have no way to save stocks for quick access across sessions.

**Current State:**
- Backend: FastAPI with Tushare Pro API for stock data
- Frontend: Next.js with TypeScript, Tailwind CSS
- No persistence layer - all data is fetched live

**Constraints:**
- Single-user application (no user authentication in scope)
- Must use SQLite (built into Python stdlib, no new dependencies)

## Goals / Non-Goals

**Goals:**
- Allow users to add/remove stocks from a watch list
- Display watch list on index page with pagination (10/20/30 rows)
- Persist watch list to SQLite database
- Show "Add to Watch List" / "Remove from Watch List" button on stock detail page

**Non-Goals:**
- User authentication / multi-user watch lists
- Real-time price updates in watch list (prices refresh on page load)
- Drag-and-drop reordering of watch list items

## Decisions

### 1. SQLite Database for Persistence

**Decision:** Use `watchlist.db` SQLite database with a single `watchlist` table.

**Rationale:**
- Built into Python stdlib - no new dependencies
- Zero-configuration, file-based storage
- Sufficient for single-user, < 10,000 rows

**Alternatives considered:**
- PostgreSQL/MySQL: Overkill for single-user, requires separate server
- JSON file: No ACID guarantees, harder to query

### 2. Database Schema

```sql
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Rationale:** Simple schema stores symbol and name (denormalized for display without joins).

### 3. Backend API Design

```
GET    /api/watchlist?page=1&page_size=10   → List stocks with pagination
POST   /api/watchlist                       → Add stock (body: {symbol, name})
DELETE /api/watchlist/{symbol}              → Remove stock
GET    /api/watchlist/{symbol}              → Check if stock is in watchlist
```

**Rationale:** RESTful CRUD pattern, page_size matches UI options (10/20/30).

### 4. Frontend State Management

**Decision:** React `useState` + `useEffect` for fetching watch list, no external state library.

**Rationale:** Simple feature doesn't warrant Redux/Zustand complexity. Server state refetched on page mount.

### 5. Watch List Display Position

**Decision:** Display watch list below the search form on index page.

**Rationale:** Natural flow - user searches, then sees their saved stocks. Alternatives (sidebar) would require layout restructuring.

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  FastAPI    │────▶│  SQLite     │
│  (Next.js)  │◀────│  Backend    │◀────│  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       │ /api/watchlist    │ /api/stock/{symbol}
       │                   │
       └───────────────────┘
              (parallel calls)
```

## API Response Shapes

### GET /api/watchlist?page=1&page_size=10

```json
{
  "items": [
    {"symbol": "000001", "name": "平安银行", "added_at": "2026-04-06T10:00:00"}
  ],
  "total": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3
}
```

### POST /api/watchlist

Request: `{"symbol": "000001", "name": "平安银行"}`
Response: `{"symbol": "000001", "name": "平安银行", "added_at": "2026-04-06T10:00:00"}`

### DELETE /api/watchlist/{symbol}

Response: `{"success": true}`

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Stock name changes in Tushare but stale name in watchlist | On add, fetch latest name from Tushare; accept slight staleness |
| User adds same stock twice | UNIQUE constraint on symbol; API returns 409 Conflict |
| Large watch list slows down page load | Pagination with max 30 rows per page |

## Open Questions

1. **Should we show latest price in watch list?** Current design shows only symbol/name. Adding price requires additional API call per stock. Defer for v2.
