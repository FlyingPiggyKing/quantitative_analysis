## Context

WatchList 组件（`frontend/src/components/WatchList.tsx`）当前展示股票代码、名称、添加日期、PE、PB、趋势预测。用户希望在股票名称和PE之间插入一个3个月PE走势迷你图，并移除添加日期列。

后端 `/api/stock/{symbol}/valuation?days=90` 已返回 `history` 数组，包含每个交易日的 `date` 和 `pe` 字段，无需后端改动。

## Goals / Non-Goals

**Goals:**
- 在 WatchList 表格中，股票名称列右侧新增"PE趋势"列，展示过去 90 天的 PE 折线迷你图（SVG sparkline）
- 移除"添加日期"列
- 复用已有的 valuation API，仅取 `history` 字段

**Non-Goals:**
- 不引入第三方图表库（避免包体积增大）；使用纯 SVG 绘制 sparkline
- 不支持交互（hover tooltip 等），仅作静态缩略图
- 不改动后端接口

## Decisions

### 1. 纯 SVG Sparkline，不引入图表库

**决定**：使用内联 SVG 手动绘制折线，无需 recharts / chart.js 等依赖。

**理由**：sparkline 数据简单（单线、无轴标注），引入图表库成本远大于收益。SVG 方案体积为零，渲染性能更好。

### 2. 数据加载时机：与 valuation 请求合并

**决定**：现有代码已在 `fetchWatchlist` 中并行调用每只股票的 valuation API，直接复用该结果的 `history` 字段，无需额外请求。

**理由**：避免额外 N 次网络请求，数据已在手。

### 3. sparkline 宽高

**决定**：固定宽 80px、高 30px，适配表格单元格。

**理由**：列宽紧凑，足以呈现趋势走势，不破坏整体布局。

### 4. 缺失数据处理

PE 值可能为 null（金融股等），sparkline 应跳过 null 点，仅连接有效点。若全部为 null 则显示"-"。

## Risks / Trade-offs

- [风险] 90 天内交易日约 60 个点，部分股票 PE 波动极小，sparkline 可能看起来是直线 → 可接受，属实际数据
- [风险] valuation API 调用已存在，增加 `history` 字段使用不引入新风险

## Migration Plan

纯前端变更，无数据迁移，直接发布即可。
