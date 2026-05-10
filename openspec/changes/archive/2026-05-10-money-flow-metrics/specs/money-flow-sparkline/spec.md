## ADDED Requirements

### Requirement: Money Flow Sparkline 迷你图渲染
WatchList 中每只股票 SHALL 在 PE 迷你图右侧展示一个 Money Flow 趋势迷你图，基于过去 30 天的主力资金净流入数据用 SVG 折线渲染，尺寸为 80×30px。

#### Scenario: 正常数据渲染（净流入）
- **WHEN** 股票存在 30 天内的主力资金净流入数据，且最近5日累计为正（净流入）
- **THEN** 显示一条连续折线 SVG，颜色为红色（#ef4444），无坐标轴和标注
- **AND** 数据点从左到右表示时间从远到近

#### Scenario: 正常数据渲染（净流出）
- **WHEN** 股票存在 30 天内的主力资金净流入数据，且最近5日累计为负（净流出）
- **THEN** 显示一条连续折线 SVG，颜色为绿色（#22c55e），无坐标轴和标注

#### Scenario: 部分数据点为 null
- **WHEN** 历史数据中部分日期的净流入为 null
- **THEN** 跳过 null 点，仅连接有效数据点

#### Scenario: 全部数据为空或无数据
- **WHEN** 净流入历史数组为空或所有值均为 null
- **THEN** 在 Money Flow 迷你图列显示"-"文字占位符，颜色为灰色（#9ca3af）

#### Scenario: 数据加载中
- **WHEN** moneyflow 数据正在加载
- **THEN** Money Flow 迷你图列显示灰色占位（#e5e7eb），不报错
