## Why

当前趋势分析输出过于简单，仅返回 `trend_direction`、`confidence` 和 `summary`，用户无法理解决策依据。通过扩展 agent system prompt，输出结构化的三部分分析（情绪分析、技术分析、趋势判断），让用户清晰感知趋势判断的完整逻辑。

## What Changes

- 扩展 `stock_trend_agent.py` 中的 `SYSTEM_PROMPT`，改变输出格式为结构化三部分
- 保持现有预测结论不变（`trend_direction`、`confidence` 不变）
- 新增前端展示逻辑，解析并渲染扩展后的分析内容
- 新增 `specs/trend-analysis-explanation/spec.md` 定义扩展后的结构

## Capabilities

### New Capabilities

- `trend-analysis-explanation`: 结构化趋势分析输出，包含情绪分析、技术分析、趋势判断三部分。情绪分析展示5天市场新闻及摘要；技术分析展示各项数据指标；趋势判断给出未来一周走势分析及操作建议（加仓/减仓/建仓建议）。

### Modified Capabilities

- `stock-trend-analysis-agent`: 修改其 REQUIREMENTS，更新输出结构为包含情绪分析、技术分析、趋势判断的结构化 JSON，而非简单的 summary 文本

## Impact

- **修改文件**: `backend/services/stock_trend_agent.py` (SYSTEM_PROMPT)
- **修改文件**: `backend/services/trend_analysis.py` (前端展示逻辑，若存在)
- **新增文件**: `openspec/specs/trend-analysis-explanation/spec.md`
