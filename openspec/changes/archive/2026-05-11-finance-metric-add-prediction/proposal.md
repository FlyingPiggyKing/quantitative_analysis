## Why

财务指标（EPS、ROE、利润率、增长率为等）目前仅在 frontend 的 FinancialIndicatorsPanel 中展示，但并未传递给 LLM agent 用于预测分析。将财务指标纳入预测上下文，可以让 agent 在技术分析中结合基本面数据进行更全面的判断。

## What Changes

1. **扩展 `format_data_context()` 函数**：在构建 A 股数据上下文时，新增财务指标数据块，包含年报和季报信息（报告期、EPS、BPS、ROE、毛利率、净利率、每股收益同比增长、净利润同比增长、营收同比增长、资产负债率、流动比率、总营收、净利润）
2. **扩展 agent prompt 示例**：在技术分析输出示例中新增 `财务指标` 区块，展示财务数据摘要
3. **LLM 输出结构扩展**：技术分析面板新增财务指标摘要区块（仅 A 股生效）

## Capabilities

### New Capabilities

- `a-stock-finance-context`: A 股财务指标上下文传递能力。将财务指标数据（年报/季报）格式化后传入 agent prompt，让 agent 在预测时能够参考基本面数据。

### Modified Capabilities

- `stock-prediction-output`: 现有的股票预测输出结构需扩展，在 `技术分析` 中新增 `财务指标` 摘要区块。

## Impact

- **Backend**: `stock_trend_agent.py` 中的 `format_data_context()` 和 `_build_a_stock_message()` 需要修改
- **Frontend**: `TechnicalAnalysis` TypeScript 接口需扩展，添加 `finance_metrics` 字段
- **仅影响 A 股**：HK/US 股票不受此变更影响
