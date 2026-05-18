## Context

The Guest View homepage displays A-share, HK, and US stock preset lists under a "热门股" section. The user wants to add a new "机构龙虎榜" (Institutional Trading Ranking) section below it to display Dragon Tiger List data from Tushare.

Current structure in `frontend/src/app/page.tsx`:
- When not logged in: shows `StockMarketTabs` with `ASharePresetList`, `USPresetList`, `HKPresetList`

Target structure:
- "热门股" section (renamed header) with A/HK/US tabs
- "机构龙虎榜" section below with Net Buy / Net Sell tabs

## Goals / Non-Goals

**Goals:**
- Display A-share Dragon Tiger List data in Guest View
- Use Tushare `top_list` API aggregated over recent 3 trading days
- Show top 5 cumulative net buy and top 5 cumulative net sell stocks
- Two-tab UI: "净买入" and "净卖出"
- Display appearance count (上榜次数) to indicate how many days a stock appeared in the list

**Non-Goals:**
- No authentication required (Guest View feature)
- No caching layer (direct Tushare API calls with caching handled at service level)
- Not showing HK/US Dragon Tiger List (Tushare only covers A-shares)

## Decisions

1. **Backend API: `/api/stock/dragon-tiger-list`**
   - Aggregates `top_list` data from last 3 trading days (configurable via `days` param, 1-10)
   - For each stock, sums net_amount across all days to get cumulative net amount
   - Returns two arrays: `net_buy` (top 5 by cumulative net_amount desc) and `net_sell` (top 5 by cumulative net_amount asc)
   - Each entry includes: trade_date (latest date), close (latest), pct_change (latest), reason (latest), appear_count (days appeared)
   - Rationale: Keeps frontend simple, avoids client-side aggregation

2. **Frontend Component: `DragonTigerList`**
   - New component in `frontend/src/components/DragonTigerList.tsx`
   - Uses existing `StockMarketTabs` pattern for buy/sell tab switching
   - Displays data in a simple table matching existing styling
   - Shows appearance count next to stock name: `德明利 (2次)`

3. **Page Integration in `page.tsx`**
   - `DragonTigerList` renders below `StockMarketTabs` (within the guest section)
   - Both components are children of the same parent div

4. **Section Header for "热门股"**
   - Add `font-[var(--font-playfair)] text-xl tracking-[0.18em] text-vt-parchment uppercase` header with brass decoration
   - Changed from "推荐股票" to "热门股"
   - Matches existing page styling conventions

## Risks / Trade-offs

- [Risk] Tushare API rate limits → Mitigation: Service-level caching (already in place for other Tushare calls)
- [Risk] Empty data if no Dragon Tiger List activity → Mitigation: Show "暂无数据" placeholder
- [Trade-off] No real-time updates → Acceptable for this feature (daily institutional data)

## Independence from Hot Stocks

The Dragon Tiger List feature is **completely independent** from the Hot Stocks (热门股) section:
- Dragon Tiger List stocks are **NOT** added to the Hot Stocks preset list
- Dragon Tiger List data fetching **does NOT** trigger AI trend analysis
- Dragon Tiger List **does NOT** affect the Hot Stocks AI analysis queue in any way
- Both features read from the same Tushare data source but are separate code paths

## Open Questions

- None at this time.
