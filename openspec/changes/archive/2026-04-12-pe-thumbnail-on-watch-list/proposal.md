## Why

在自选列表中，用户只能看到当前PE值，无法直观感受PE的历史趋势。添加PE迷你折线图（sparkline），让用户一眼看出估值走势，辅助投资决策。

## What Changes

- **新增** 每只股票的PE趋势迷你图（sparkline），显示过去3个月的PE走势，位于股票名称和市盈率(PE)列之间
- **移除** "添加日期"列（用户反馈该信息无实际参考价值）
- 复用已有的 `/api/stock/{symbol}/valuation?days=90` 接口获取PE历史数据（后端已支持）

## Capabilities

### New Capabilities

- `pe-sparkline`: WatchList 中内嵌的PE趋势迷你折线图组件，基于过去3个月PE数据渲染 SVG sparkline

### Modified Capabilities

- `watch-list-display`: WatchList 表格布局变更——移除添加日期列，在股票名称列后新增PE迷你图列

## Impact

- `frontend/src/components/WatchList.tsx`：新增 sparkline 列、移除日期列
- 无需后端改动，`/api/stock/{symbol}/valuation` 已返回 `history` 数组，使用 `days=90` 即可
