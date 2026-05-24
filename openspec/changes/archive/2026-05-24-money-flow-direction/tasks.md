# Implementation Tasks

## 1. Backend API Implementation

- [x] 1.1 在 `akshare_service.py` 中添加 `get_sector_moneyflow(days=5, top_n=8)` 方法，调用Tushare `moneyflow_ind_dc` 接口
- [x] 1.2 在 `backend/api/stock.py` 中添加 `/api/stock/sector-money-flow` endpoint，返回聚合后的板块资金流向数据
- [x] 1.3 添加后端缓存逻辑（5分钟TTL）
- [x] 1.4 实现罗马数字后缀去重逻辑（Ⅱ,Ⅲ等变体合并为基础名称）

## 2. Frontend Dependencies

- [x] 2.1 无需安装ECharts，使用原生Canvas API实现Sankey图

## 3. Frontend Data Layer

- [x] 3.1 在 `frontend/src/services/` 中创建 `sectorMoneyFlow.ts`，实现 `fetchSectorMoneyFlow(days, top_n)` API调用

## 4. Sankey Visualization Component

- [x] 4.1 创建 `frontend/src/components/SectorMoneyFlowSankey.tsx` 组件
- [x] 4.2 实现数据处理函数：对齐跨日板块、构建Sankey nodes和links
- [x] 4.3 使用自定义Canvas实现垂直Sankey图渲染（非ECharts）
- [x] 4.4 添加点击高亮交互（点击折线/图例高亮板块）
- [x] 4.5 U型折线使用独立水平通道避免竖线重叠
- [x] 4.6 响应式布局支持（移动端 < 640px）

## 5. SubModuleTabs Integration

- [x] 5.1 在 `SubModuleTabs.tsx` 中添加 `"moneyFlow"` 到 `AnalysisSubModule` 类型
- [x] 5.2 修改 `getDefaultSubModule` 函数支持 `"moneyFlow"`（作为analysis模块的默认子模块）
- [x] 5.3 在 `analysis` 模块分支中添加资金流向Tab渲染逻辑
- [x] 5.4 Tab顺序：资金流向在前（默认），机构龙虎榜在后

## 6. Page Integration

- [x] 6.1 在主页面中（如 `app/page.tsx`）添加资金流向内容渲染
- [x] 6.2 确保 SubModuleTabs 能正确传递 `renderMoneyFlowContent` 回调

## 7. Styling and Polish

- [x] 7.1 确保资金流向Tab样式与"机构龙虎榜"一致（无边框布局）
- [x] 7.2 日期显示在Tab栏右侧
- [x] 7.3 底部图例显示5日累计净流入金额，按金额降序排列

## 8. Verification

- [x] 8.1 运行时验证：Tab切换和数据加载流程正常
- [x] 8.2 运行时验证：点击高亮/弱化交互正常
- [x] 8.3 运行时验证：移动端布局正常
