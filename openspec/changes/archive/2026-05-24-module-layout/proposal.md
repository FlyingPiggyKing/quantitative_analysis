## Why

当前首页布局将"我的自选"和"机构龙虎榜"平级展示，两者都是独立模块。用户希望将这两个模块整合为一个更具层次的结构：上层为主模块切换（我的自选 / 投资分析），下层为子模块切换（A股/美股/港股 或 机构龙虎榜）。

## What Changes

1. **新增顶层模块切换 Tab**：在当前"我的自选"标题位置新增主模块 Tab 栏，支持在"我的自选"和"投资分析"之间切换，字体使用 text-base 和 semibold
2. **重构"投资分析"模块**：将"机构龙虎榜"从独立模块降级为"投资分析"的子模块，容器无边框，最大化显示空间
3. **新增底部子模块 Tab**：每个主模块底部有独立的子模块 Tab 栏
   - 我的自选：A股 / 美股 / 港股（现有逻辑保持不变）
   - 投资分析：机构龙虎榜
4. **合并净买入/净卖出显示**：DragonTigerList 不再使用 Tab 切换，而是将净买入和净卖出上下堆叠显示
5. **同时适用于登录用户和访客**：布局调整适用于 `user ? <WatchList> : <PresetStockList>` 两套视图

## Capabilities

### New Capabilities
- `module-layout-tabs`: 顶层模块切换 Tab 组件，支持"我的自选"和"投资分析"两个主模块的切换
- `sub-module-tabs`: 底部子模块 Tab 组件，支持各主模块内的子模块切换

### Modified Capabilities
- `watch-list-display`: 当前 WatchList 内的 `StockMarketTabs` 需要保留，但子模块 tab 从页面顶部移到页面底部，且外层不再包裹顶层模块切换逻辑
- `dragon-tiger-list`: DragonTigerList 内部不再使用净买入/净卖出 Tab 切换，改为上下堆叠的两个 section 显示

## Impact

- 修改 `frontend/src/app/page.tsx` - 重构主页面布局，新增顶层 Tab 和底部 Tab 结构
- 修改 `frontend/src/components/WatchList.tsx` - 移除内部标题和 StockMarketTabs，保留股票表格逻辑
- 修改 `frontend/src/components/DragonTigerList.tsx` - 移除内部 buy/sell tabs，改为上下堆叠显示
- 新增 `frontend/src/components/ModuleTabs.tsx` - 顶层模块切换组件
- 新增 `frontend/src/components/SubModuleTabs.tsx` - 底部子模块 Tab 组件
