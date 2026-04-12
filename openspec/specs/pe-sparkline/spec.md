# pe-sparkline Specification

## Purpose
TBD - created by archiving change pe-thumbnail-on-watch-list. Update Purpose after archive.
## Requirements
### Requirement: PE Sparkline 迷你图渲染
WatchList 中每只股票 SHALL 在"股票名称"列右侧展示一个 PE 趋势迷你图，基于过去 90 天的 PE 历史数据用 SVG 折线渲染，尺寸为 80×30px。

#### Scenario: 正常数据渲染
- **WHEN** 股票存在 90 天内的 PE 历史数据
- **THEN** 显示一条连续折线 SVG，颜色为蓝色（#60a5fa），无坐标轴和标注

#### Scenario: 部分 PE 值为 null
- **WHEN** 历史数据中部分日期的 PE 为 null
- **THEN** 跳过 null 点，仅连接有效数据点

#### Scenario: 全部 PE 值为 null 或无数据
- **WHEN** 历史数组为空或所有 PE 均为 null
- **THEN** 在 PE 迷你图列显示"-"文字占位符

### Requirement: PE Sparkline 加载状态
在 valuation 数据加载完成前，迷你图列 SHALL 显示骨架占位（灰色短横线或空白）。

#### Scenario: 数据加载中
- **WHEN** watchlist 数据正在加载
- **THEN** PE 迷你图列显示灰色占位，不报错

