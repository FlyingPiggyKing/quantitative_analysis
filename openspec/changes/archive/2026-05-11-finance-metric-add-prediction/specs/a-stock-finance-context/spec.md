## ADDED Requirements

### Requirement: A股财务指标上下文传递
`format_data_context()` 函数 SHALL 在为 A 股构建数据上下文时，包含财务指标数据块。该数据块应包含报告期类型（年报/季报）和关键财务指标。

#### Scenario: A股数据上下文包含财务指标
- **WHEN** `format_data_context()` 为 A 股股票组装数据上下文
- **THEN** 它 SHALL 调用 `get_financial_fundamentals()` 获取财务数据
- **AND** 如果财务数据有效（无 `error` 字段），SHALL 在上下文中新增财务指标区块
- **AND** 区块 SHALL 包含：`report_label`（如"2025年年报"）、`ann_date`（发布日期）、`eps`、`bps`、`roe`、`gross_margin`、`netprofit_margin`、`basic_eps_yoy`、`netprofit_yoy`、`tr_yoy`、`debt_to_assets`、`current_ratio`、`total_revenue`、`n_income`

#### Scenario: 财务数据不可用时跳过财务指标区块
- **WHEN** 财务数据包含 `error` 字段或为 `null`
- **THEN** `format_data_context()` SHALL 跳过财务指标区块
- **AND** agent SHALL 使用现有技术指标数据进行预测

### Requirement: 财务指标区块格式
财务指标区块 SHALL 以文本格式呈现，包含报告期信息和关键财务指标。

#### Scenario: 完整财务指标格式
- **WHEN** 财务数据有效
- **THEN** 上下文中财务指标区块 SHALL 格式如下：
  ```
  财务指标 (<report_label>, <ann_date>发布):
  EPS: <eps>, BPS: <bps>, ROE: <roe>%, 毛利率: <gross_margin>%, 净利率: <netprofit_margin>%
  每股收益同比增长: <basic_eps_yoy>%, 净利润同比增长: <netprofit_yoy>%, 营收同比增长: <tr_yoy>%
  资产负债率: <debt_to_assets>%, 流动比率: <current_ratio>, 总营收: <total_revenue>亿元, 净利润: <n_income>亿元
  ```
- **AND** 数值 SHALL 保留合理小数位（EPS/BPS 保留2位，百分比保留1位）
- **AND** `total_revenue` 和 `n_income` SHALL 从 Tushare 的元转换为亿元（除以 1e8）
- **AND** `debt_to_assets` SHALL 去掉前导 `+` 号（资产负债率是比例，不是增长值）

#### Scenario: 部分字段为null时显示占位符
- **WHEN** 某个财务指标字段为 `null` 或 `None`
- **THEN** 该字段 SHALL 显示为 `--`
- **AND** 其他有效字段 SHALL 正常显示

### Requirement: 仅A股生效
财务指标上下文传递 SHALL 仅对 A 股生效。

#### Scenario: 非A股股票不包含财务指标
- **WHEN** `format_data_context()` 为 HK 或 US 股票组装数据上下文
- **THEN** 它 SHALL NOT 调用 `get_financial_fundamentals()`
- **AND** 上下文中 SHALL NOT 包含财务指标区块
