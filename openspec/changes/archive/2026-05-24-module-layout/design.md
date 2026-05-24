## Context

当前首页 (`page.tsx`) 布局：
- 搜索区域
- `WatchList`（登录用户）或 `StockMarketTabs + PresetStockList`（访客）- 包含 A股/美股/港股子 Tab
- `DragonTigerList`（机构龙虎榜）- 作为独立模块平级展示

用户需求：重组为两层 Tab 结构
- 顶层：我的自选 | 投资分析
- 底层（底部）：我的自选下有 A股/美股/港股；投资分析下有 机构龙虎榜

## Goals / Non-Goals

**Goals:**
- 实现顶层模块切换（我的自选 / 投资分析）
- 实现底部子模块 Tab 切换
- 保持 WatchList 现有逻辑不变
- 同时支持登录用户和访客视图

**Non-Goals:**
- 不修改 WatchList 内部股票表格、分页逻辑
- 不改变 URL 结构（无路由变更）

## Decisions

### 1. 组件结构

**方案 A（推荐）：** 新增两个容器组件
- `ModuleTabs.tsx` - 顶层 Tab 组件，管理主模块切换（我的自选 / 投资分析）
- `SubModuleTabs.tsx` - 底部 Tab 组件，管理子模块切换（A股/美股/港股 或 机构龙虎榜）
- `page.tsx` 变为布局编排组件

**方案 B：** 在 `page.tsx` 内直接实现所有 Tab 逻辑

**选择 A**：符合单一职责，模块化程度高，便于维护和扩展。

### 2. 状态管理

当前 `stockTab` state 在 `page.tsx` 管理 A股/美股/港股 切换。

新增需求：
- `activeModule: "watchlist" | "analysis"` - 顶层模块
- `activeSubModule: "A" | "US" | "HK" | "dragonTiger"` - 底层子模块

状态管理策略：
- `page.tsx` 管理顶层 `activeModule`
- `ModuleTabs` 内部管理子模块状态（`SubModuleTabs`）

### 3. 底部 Tab 渲染位置

**方案 A：** 在 `page.tsx` 的 `ModuleTabs` 内部渲染底部 `SubModuleTabs`

**方案 B：** 各模块内容组件内部渲染自己的底部 Tab

**选择 A：** 统一布局，便于控制子模块切换的视觉一致性。

### 4. 组件文件变更

| 文件 | 变更 |
|------|------|
| `page.tsx` | 重构为布局组件，新增 ModuleTabs 包裹 |
| `WatchList.tsx` | 移除标题和 StockMarketTabs，仅保留表格逻辑 |
| `DragonTigerList.tsx` | 修改：移除内部 buy/sell tabs，改为上下堆叠显示；支持 showHeader 和 onDateChange props |
| `ModuleTabs.tsx` | 新增 - 顶层模块切换组件，tab 文字使用 text-base font-semibold |
| `SubModuleTabs.tsx` | 新增 - 底部子模块切换组件；投资分析容器无边框；机构龙虎榜 tab 文字使用 text-base font-semibold |

### 5. DragonTigerList 显示调整

实际实现中，DragonTigerList 的净买入/净卖出不再使用 Tab 切换，而是上下堆叠显示：
- 上面显示"▲ 净买入"标题，下面是净买入表格
- 下面显示"▼ 净卖出"标题，下面是净卖出表格
- 移除了原有的 buy/sell Tab 切换

### 6. 投资分析容器样式

SubModuleTabs 中投资分析的容器不使用 vt-panel 边框和内边距，最大化显示空间。

## Risks / Trade-offs

[Risk] 子模块 Tab 状态在模块切换时如何处理 → Mitigation：`activeModule` 变化时，重置 `activeSubModule` 为默认值（A股 或 机构龙虎榜）

[Risk] DragonTigerList 日期传递给 SubModuleTabs → Mitigation：使用 render function 模式，通过回调函数传递日期

## Open Questions

1. 投资分析的子模块 Tab 是否需要预留扩展空间（未来可能有其他子模块）？
