## Why

板块资金流向数据能帮助投资者了解资金在不同行业板块间的流动趋势，发现资金轮动规律。目前项目已有个股资金流向（moneyflow_ths），但缺少板块级别的资金流向分析功能。引入Tushare的`moneyflow_ind_dc`接口，结合Sankey图可视化，可以直观展示过去5天资金在热门板块间的流转路径。

## What Changes

1. **新增板块资金流向API** (`moneyflow_ind_dc`)：获取行业板块每日的净流入数据
2. **新增板块资金流向模块**：作为"投资分析"下的新子模块，展示过去5天Top 8板块的资金流向Sankey图
3. **新增Sankey图可视化组件**：垂直布局展示资金流向，使用自定义Canvas实现
4. **修改SubModuleTabs**：支持"资金流向"子模块，默认显示在机构龙虎榜之前

## Capabilities

### New Capabilities

- `sector-money-flow-sankey`: 板块资金流向Sankey图模块
  - 后端API：调用Tushare `moneyflow_ind_dc` 获取板块日级别资金流向
  - 前端组件：垂直Sankey图展示过去5天Top 8板块流向
  - 数据聚合：每日按net_amount排序取Top 8，跨日对齐板块
  - 交互：点击连接线高亮对应板块，底部图例显示5日累计净流入

## Context

### 当前状态
项目已有：
- 个股级别资金流向（`moneyflow_ths` API）
- "投资分析"模块，下辖"机构龙虎榜"子模块
- 现有的SubModuleTabs组件支持切换不同分析子模块

### 待接入数据源
根据用户指引，Tushare提供板块资金流向接口 `moneyflow_ind_dc`：
- **接口文档**: doc_id=344
- **数据粒度**: 行业/板块级别每日资金流向
- **关键字段**: `trade_date`(交易日期), `industry_name`(板块名称), `net_amount`(净流入额)
- **特殊处理**: 仅返回 `content_type == "行业"` 的数据，过滤概念股/区域股

### 可视化目标
垂直Sankey图样式：
- 垂直方向，最新日期在上，最老日期在下
- 每个日期截面内，板块按net_amount从左到右排序（最大在左）
- U型折线连接相邻日期的同一板块，表示资金流转
- 点击高亮功能，底部图例显示5日累计净流入

## Goals / Non-Goals

**Goals:**
- 调用Tushare `moneyflow_ind_dc`获取板块日级别资金流向
- 展示过去5个交易日Top 8净流入板块
- 用垂直Sankey图可视化资金在板块间的流转趋势
- 作为"投资分析"下的新子模块"资金流向"（默认显示）

**Non-Goals:**
- 不实现个股资金流向（已存在）
- 不实现板块轮动预测分析
- 不实现跨市场（港股、美股）板块资金流向
- Sankey图的跨日流量连线为示意性质（无详细板块间流转数据）

## Decisions

### Decision 1: 使用自定义Canvas实现而非ECharts

**选择自定义Canvas**:
- ECharts的垂直Sankey不支持多列日期布局（orient: "vertical"不适配此需求）
- 自定义Canvas可精确控制U型折线的走向和水平通道分配
- 复古黄铜主题配色需要精确控制每条连接线的颜色和透明度

**实现要点**:
- 每条跨日连接线分配独立的水平通道，避免竖线重叠
- 点击检测使用点到线段距离算法（6px阈值）
- 使用ResizeObserver响应容器宽度变化

### Decision 2: 跨日板块对齐策略

由于不同日期的Top 8板块可能不同，Sankey图需要处理板块对齐问题：

**方案：基于并集对齐**
- 取5天所有出现的板块作为Sankey的节点
- 每日的节点位置固定在对应日期的横截面上
- 跨日流量通过相邻日期共同出现的板块连接

### Decision 3: 罗马数字板块去重

Tushare返回的板块名称可能包含罗马数字后缀（如"家电零部件Ⅱ"、"家电零部件Ⅲ"），它们约97%的情况下是同一板块的不同DC编码副本（值完全相同），约2.6%是真实的不同子板块（值差异显著，如"其他电源设备Ⅱ" vs "其他电源设备Ⅲ"）。

**去重策略**:
- 使用正则匹配基础名称：`[IVXⅰⅱⅲⅳⅴⅵⅷⅸⅹⅠ-Ⅿ]+$`
- 当变体值相同或差异小于最大值1%时：合并为基础名称，取单一值
- 当变体值差异大于1%时：保留两个条目，各自使用原始名称
- 这确保每条连接线不会因为重复数据显得浮夸，同时保留真实子板块信息

### Decision 4: 后端数据聚合

**API设计**: `GET /api/stock/sector-money-flow?days=5&top_n=8`

**返回结构**:
```json
{
  "sectors": ["板块A", "板块B", ...],
  "daily_top": {
    "2026-05-24": ["板块A", "板块B", "板块C", "板块D", "板块E", "板块F", "板块G", "板块H"],
    "2026-05-23": ["板块A", "板块C", "板块X", ...],
    ...
  },
  "net_amounts": {
    "2026-05-24": {"板块A": 15.6, "板块B": 12.3, ...},
    ...
  }
}
```

### Decision 5: 前端组件结构

```
SectorMoneyFlowSankey.tsx  // 主组件
├── API调用层 (fetchSectorMoneyFlow)
├── 数据处理层 (对齐、排序、去重)
└── Canvas Sankey渲染层 (自定义实现，非ECharts)
```

## Impact

- **Backend**: 新增 `/api/stock/sector-money-flow` API endpoint，调用Tushare `moneyflow_ind_dc`
- **Frontend**: 新增 `SectorMoneyFlowSankey.tsx` 组件，使用自定义Canvas实现Sankey图
- **SubModuleTabs**: 添加 `"moneyFlow"` 作为新的AnalysisSubModule类型
- **Dependencies**: 无需图表库，使用原生Canvas API

## Risks / Trade-offs

**[Risk] Tushare API限速** → Mitigation: 后端添加缓存层，5分钟有效期内复用数据

**[Risk] 板块名称跨日不一致** → Mitigation: 实现罗马数字后缀去重逻辑，合并相同基础名称的板块

**[Risk] Sankey图跨日流量为估算** → Mitigation: 文档说明为示意性质，不作为精确数据引用
