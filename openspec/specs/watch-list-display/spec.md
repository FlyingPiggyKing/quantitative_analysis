# watch-list-display Specification

## Purpose
TBD - created by archiving change pe-thumbnail-on-watch-list. Update Purpose after archive.
## Requirements
### Requirement: WatchList 表格列布局
WatchList 表格 SHALL 包含以下列（从左到右）：股票代码、股票名称、PE趋势迷你图、市盈率(PE)、市净率(PB)、趋势预测。

#### Scenario: 默认列展示
- **WHEN** 用户访问首页 WatchList 区域
- **THEN** 表格显示：股票代码 | 股票名称 | PE趋势 | 市盈率(PE) | 市净率(PB) | 趋势预测，不包含"添加日期"列

