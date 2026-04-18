## Context

`analyze_stock_trend` 函数已返回包含 `情绪分析`、`技术分析`、`趋势判断` 的结构化数据。前端 `TrendAnalysisPanel` 组件已正确实现渲染逻辑。后台异步任务 `task_queue.py` 在调用 `TrendPredictionService.save_prediction` 时未传递 `extended_analysis` 参数，导致通过异步任务分析的数据扩展部分丢失。

同步批量分析接口 `trend_prediction.py:batch_analyze` 已正确传递 `extended_analysis`，因此同步分析时扩展数据能正确保存和展示。

## Goals / Non-Goals

**Goals:**
- 修复 `task_queue.py` 中的 `save_prediction` 调用，传入 `extended_analysis` 参数
- 确保后台异步分析任务保存的数据与同步分析一致

**Non-Goals:**
- 不修改 `analyze_stock_trend` 的输出格式（已正常）
- 不修改前端 `TrendAnalysisPanel` 组件渲染逻辑（已正常）
- 不修改 `TrendPredictionService` 的数据库逻辑（已正常）

## Decisions

### Decision: 在 task_queue.py 中传递 extended_analysis

**选择**: 在 `_run_analysis` 方法中调用 `save_prediction` 时，从 `prediction` 结果中提取 `extended_analysis` 并传入。

**原因**: 与同步接口 `trend_prediction.py:batch_analyze` 的处理方式保持一致。

**实现方式**:
```python
# 构建 extended_analysis
extended_analysis = None
if prediction.get("情绪分析") or prediction.get("技术分析") or prediction.get("趋势判断"):
    extended_analysis = {
        "情绪分析": prediction.get("情绪分析"),
        "技术分析": prediction.get("技术分析"),
        "趋势判断": prediction.get("趋势判断"),
    }

saved = TrendPredictionService.save_prediction(
    symbol=symbol,
    name=name,
    trend_direction=prediction.get("trend_direction", "neutral"),
    confidence=prediction.get("confidence", 0),
    summary=prediction.get("summary", ""),
    extended_analysis=extended_analysis,  # 新增此参数
)
```

## Risks / Trade-offs

[Risk] 如果 `analyze_stock_trend` 返回的预测结果中缺少 `extended_analysis` 字段 → **Mitigation**: 代码中已有保护逻辑，当字段不存在时 `extended_analysis` 为 `None`，不影响现有功能。
