## 1. Create ModuleTabs Component

- [x] 1.1 Create `frontend/src/components/ModuleTabs.tsx` component with "我的自选" and "投资分析" tab options
- [x] 1.2 Implement active state management for module selection
- [x] 1.3 Add styling consistent with existing tab design

## 2. Create SubModuleTabs Component

- [x] 2.1 Create `frontend/src/components/SubModuleTabs.tsx` component
- [x] 2.2 Support market tabs (A股/美股/港股) for WatchList module
- [x] 2.3 Support 机构龙虎榜 tab for Analysis module
- [x] 2.4 Add styling consistent with existing StockMarketTabs

## 3. Refactor page.tsx Layout

- [x] 3.1 Update `frontend/src/app/page.tsx` to use ModuleTabs as top-level wrapper
- [x] 3.2 Add state for activeModule ("watchlist" | "analysis")
- [x] 3.3 Integrate SubModuleTabs at the bottom of each module
- [x] 3.4 Handle module/sub-module state coordination (reset sub-module on parent change)

## 4. Refactor WatchList Component

- [x] 4.1 Remove "我的自选" title from WatchList (now in ModuleTabs)
- [x] 4.2 Remove StockMarketTabs from WatchList (moved to page.tsx level)
- [x] 4.3 WatchList retains only the stock table and pagination logic
- [x] 4.4 Export MarketWatchlist component for reuse if needed

## 5. Update Guest View (PresetStockList)

- [x] 5.1 Apply same module/sub-module structure to guest view
- [x] 5.2 Ensure StockMarketTabs + PresetStockList work within the new layout
- [x] 5.3 Verify guest can switch between 投资分析 (机构龙虎榜) and preset lists

## 6. Testing and Verification

- [x] 6.1 Test top-level module switching between "我的自选" and "投资分析"
- [x] 6.2 Test bottom sub-module tabs in WatchList (A股/美股/港股)
- [x] 6.3 Test bottom sub-module tab in Investment Analysis (机构龙虎榜)
- [x] 6.4 Verify sub-module resets to default when switching top-level modules
- [x] 6.5 Test as authenticated user (with WatchList)
- [x] 6.6 Test as guest user (with PresetStockList)

## 7. Post-Implementation Refinements

- [x] 7.1 Remove redundant tab layer in 投资分析 (merged 净买入/净卖出 into stacked sections)
- [x] 7.2 Remove border from 机构龙虎榜 container to maximize display space
- [x] 7.3 Increase font size and weight for module tabs ("我的自选", "投资分析", "机构龙虎榜")
