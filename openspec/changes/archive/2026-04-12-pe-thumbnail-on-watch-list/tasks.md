## 1. 前端改动：WatchList.tsx

- [x] 1.1 扩展 `ValuationData` 接口，新增 `pe_history: Array<{ date: string; pe: number | null }>` 字段
- [x] 1.2 修改 valuation 抓取逻辑，将 API 返回的 `history` 数组存入 `valMap[item.symbol].pe_history`（`days=90`）
- [x] 1.3 从 table header 中移除"添加日期"列（`<th>添加日期</th>` 及对应 `formatDate` 调用）
- [x] 1.4 在表头"股票名称"列后、"市盈率(PE)"列前插入新列"PE趋势"
- [x] 1.5 在每行数据中，股票名称与 PE 值之间插入 `<PE trendIndicator>` 组件

## 2. 前端新增：Sparkline 组件

- [x] 2.1 在 `frontend/src/components/` 下新建 `PETrendSparkline.tsx` 组件
- [x] 2.2 组件接收 `peHistory: Array<{ date: string; pe: number | null }>` 作为 props
- [x] 2.3 过滤 null 值，若无有效数据则返回"-"占位
- [x] 2.4 渲染内联 SVG（宽 80px、高 30px），计算 min/max 归一化 Y 轴，折线颜色 #60a5fa
- [x] 2.5 处理加载中状态（接收 `loading?: boolean` prop，返回灰色占位 SVG）
