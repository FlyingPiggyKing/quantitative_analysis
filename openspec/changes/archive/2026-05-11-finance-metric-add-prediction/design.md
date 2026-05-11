## Context

财务指标（年报/季报数据：EPS、ROE、利润率、增长率等）目前通过 `get_financial_fundamentals()` 获取，并在前端 `FinancialIndicatorsPanel` 组件中展示。但这些数据未被传入 LLM agent 的预测上下文，导致 agent 在做技术分析时无法参考基本面数据。

A 股预测流程中，`format_data_context()` 负责组装技术指标、估值数据、主力资金流向等上下文。当前该函数不包含财务指标数据。

## Goals / Non-Goals

**Goals:**
- 在 A 股 `format_data_context()` 中新增财务指标数据块
- 告知 agent 当前数据为年报还是季报，以及报告发布时间
- 在 LLM 输出的 `技术分析` 区块中新增 `财务指标` 摘要
- 仅影响 A 股，HK/US 股票不受影响

**Non-Goals:**
- 不修改 `get_financial_fundamentals()` 的数据获取逻辑
- 不修改前端 `FinancialIndicatorsPanel` 展示组件
- 不添加新的 API endpoint

## Decisions

### Decision 1: 财务指标上下文格式

**选择：** 在 `format_data_context()` 中新增独立的数据块，包含报告期类型（年报/季报）和关键财务指标。

**理由：** 参照现有 `valuation` 区块（PE/PB/换手率）的格式，财务指标区块应包含报告期标签、EPS、BPS、ROE、各项利润率、同比增长率等核心指标。

**格式示例：**
```
财务指标 (2025年年报, 2026-04-25发布):
EPS: 2.35, BPS: 12.80, ROE: 18.4%, 毛利率: 35.2%, 净利率: 15.8%
每股收益同比增长: 12.5%, 净利润同比增长: 8.3%, 营收同比增长: 5.1%
资产负债率: 45.2%, 流动比率: 1.8, 总营收: 125.6亿元, 净利润: 19.8亿元
```

**单位转换：** Tushare `income` 表返回的 `total_revenue` 和 `n_income` 单位是**元**，需要除以 1e8 转换为**亿元**。

### Decision 2: 报告期类型标注

**选择：** 在数据块标题中标注"年报"或"季报"，并附上公告发布日期。

**理由：** 年报和季报的时效性和完整性不同，agent 需要知道当前财务数据的报告期类型。

### Decision 3: LLM 输出结构扩展

**选择：** 在 `技术分析` 下新增 `财务指标` 字段（可选），包含关键财务数据的摘要和解读。

**理由：** 保持与现有结构（macd, rsi, ma, volume, valuation, money_flow）的一致性，仅对 A 股填充此字段。

### Decision 4: 按市场分离 System Prompt

**选择：** `get_system_prompt()` 返回完全分离的 prompt，A 股和 HK/US 各有一套独立的 prompt 和 example。

**理由：** 避免单一 prompt 混杂 A 股和 HK/US 的示例，导致 LLM 混淆。分离后：
- A 股 prompt：包含 `finance_metrics` 示例，全部中文
- HK/US prompt：不包含 `finance_metrics`，全部中文（用户均为中国用户）

### Decision 5: 前端 TypeScript 接口扩展

**选择：** 在 `TechnicalAnalysis` 接口中新增可选的 `finance_metrics` 字段。

**理由：** 与 `valuation` 和 `money_flow` 字段模式一致，且设置为可选以保证 HK/US 股票的兼容性。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 财务数据可能缺失或过期 | `format_data_context()` 检查 financial_data 是否包含 `error`，如有则跳过财务指标区块 |
| LLM 输出缺少财务指标区块 | prompt example 中提供完整的 `财务指标` 输出示例，确保 LLM 知道如何输出 |
| 前端未更新但后端已输出财务指标 | 使用可选字段，前端按需渲染 |

## Open Questions

- 无
