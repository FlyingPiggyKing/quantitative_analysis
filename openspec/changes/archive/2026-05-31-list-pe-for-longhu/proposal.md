## Why

The 机构龙虎榜 (institutional trading leaderboard) displays stocks that appeared on the Dragon Tiger List. Currently it shows close price but not valuation metrics. Users want to see PE TTM and market cap (市值) directly in the list to quickly assess whether a stock is expensive or cheap relative to its fundamentals.

## What Changes

1. **Backend** — `get_dragon_tiger_list` in `akshare_service.py` to also fetch and join `pe_ttm` and `total_mv` (as 市值 in 亿元) for each stock in the list.
2. **Frontend** — `DragonTigerList.tsx` to replace the 收盘价 column with 市值(亿) and add a PE TTM column.
3. **API** — `DragonTigerItem` TypeScript interface and `DragonTigerData` JSON response to include `pe_ttm` and `total_mv_yi` fields.

## Capabilities

### New Capabilities
- `dragon-tiger-valuation-join`: Join valuation metrics (PE TTM, 市值) into the Dragon Tiger List response so each stock shows its current valuation at a glance.

### Modified Capabilities
- `stock-valuation-metrics` (existing): Already provides `get_daily_basic` data including `pe_ttm` and `total_mv`. This change extends the dragon-tiger-list to use it — no new spec needed, just implementation of an existing capability.

## Impact

- **Backend**: `akshare_service.py` — modify `get_dragon_tiger_list()` to join valuation data
- **API**: `backend/api/stock.py` — no change needed (payload structure changes)
- **Frontend**: `DragonTigerList.tsx` — replace close price column, add PE TTM column; update `DragonTigerItem` interface
- **Tushare dependency**: Already in use; no new API calls required beyond what `get_daily_basic` already does
