## ADDED Requirements

### Requirement: WatchList 表格列布局
WatchList 表格 SHALL 包含以下列（从左到右）：股票代码、股票名称、PE趋势迷你图、市盈率(PE)、市净率(PB)、趋势预测。

#### Scenario: 默认列展示
- **WHEN** 用户访问首页 WatchList 区域
- **THEN** 表格显示：股票代码 | 股票名称 | PE趋势 | 市盈率(PE) | 市净率(PB) | 趋势预测，不包含"添加日期"列

## REMOVED Requirements

### Requirement: 显示添加日期列
**Reason**: 用户反馈添加日期对投资决策无参考价值，移除以简化界面并腾出空间给 PE 趋势图
**Migration**: 无，纯 UI 移除，数据库字段保留不变

#### Scenario: 添加日期不再显示
- **WHEN** 用户查看 WatchList
- **THEN** 表格中不出现"添加日期"列和对应数据
