## Why

Users want to see institutional trading activity data for A-shares. The Dragon Tiger List (龙虎榜) shows which stocks have been featured on institutional trading venues, helping investors identify stocks with significant institutional attention. Currently, there is no such section in the Guest View.

## What Changes

- Add a new "机构龙虎榜" (Institutional Trading Ranking) section below the existing "热门股" (Hot Stocks) section in the Guest View
- Rename existing A-share, US, and HK stock blocks within "热门股" to include a section header "热门股"
- Create two tabs within "机构龙虎榜": "净买入" (Net Buy) and "净卖出" (Net Sell)
- Fetch Dragon Tiger List data from Tushare `top_list` API, aggregating from recent 3 trading days
- Display top 5 stocks by cumulative net buy amount and top 5 by cumulative net sell amount
- Show appearance count (上榜次数) to indicate how many days a stock appeared
- Add backend API endpoint to serve Dragon Tiger List data
- Display columns: 日期 (date), 代码 (code), 名称+次数 (name with appear_count), 收盘价 (close), 涨幅 (pct_change), 净买入额/净卖出额 (net_amount cumulative), 上榜原因 (reason)

## Capabilities

### New Capabilities

- `a-share-dragon-tiger-list`: Display A-share Dragon Tiger List data with net buy/sell tabs in Guest View. Data sourced from Tushare `top_list` API aggregated over recent 3 trading days. For each stock, net_amount is summed across all days to get cumulative amount. Each tab shows top 5 stocks ranked by cumulative net amount (positive for buy, negative for sell). Includes appear_count field showing how many days the stock appeared.

### Modified Capabilities

- `stock-market-tabs`: Modify to add section header "热门股" above the A/HK/US stock tabs in PresetStockList. The tabs remain unchanged but now sit under a labeled section.

## Impact

- **Frontend**: New `DragonTigerList` component in `frontend/src/components/` with tab switching between net buy/sell views, displaying appearance count
- **Backend**: New API endpoint `GET /api/stock/dragon-tiger-list` that aggregates Tushare `top_list` data with cumulative net_amount
- **Data Source**: Tushare `top_list` API (requires token, already configured in project)
