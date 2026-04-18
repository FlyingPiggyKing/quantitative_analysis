## Why

趋势分析 API `analyze_stock_trend` 已正确输出包含「情绪分析」「技术分析」「趋势判断」的结构化数据，前端 `TrendAnalysisPanel` 组件也已正确渲染。但后台异步分析任务 `task_queue.py` 在保存预测结果时未传递 `extended_analysis` 参数，导致通过异步任务分析的数据丢失了扩展分析部分，用户在股票详情页看到的仍是旧格式。

## What Changes

- 修改 `backend/services/task_queue.py` 的 `_run_analysis` 方法，在调用 `save_prediction` 时传入 `extended_analysis` 参数
- 验证 `backend/api/trend_prediction.py` 的同步批量分析接口已正确保存扩展数据（已确认正常）
- 验证前端 `TrendAnalysisPanel` 组件渲染逻辑正确（已确认正常）

## Capabilities

### Modified Capabilities

- `stock-trend-display`: 修复后台异步分析任务保存扩展数据，确保股票详情页能正确展示结构化的趋势分析（情绪分析、技术分析、趋势判断及操作建议）

## Impact

- **修改文件**: `backend/services/task_queue.py` - 在 `save_prediction` 调用中添加 `extended_analysis` 参数
