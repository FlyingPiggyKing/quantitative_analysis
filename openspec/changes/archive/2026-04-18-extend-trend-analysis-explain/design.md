## Context

当前 `stock_trend_agent.py` 的 `SYSTEM_PROMPT` 返回结构为：
```json
{
  "trend_direction": "up/down/neutral",
  "confidence": 0-100,
  "summary": "分析说明"
}
```

用户无法感知趋势判断的具体依据。需要扩展输出为结构化三部分，让用户理解"为什么"做出这个判断。

## Goals / Non-Goals

**Goals:**
- 扩展 agent 输出为三部分结构：情绪分析、技术分析、趋势判断
- 情绪分析展示5天市场新闻及摘要
- 技术分析展示各项数据指标
- 趋势判断给出未来一周走势分析及操作建议
- 保持现有预测结论不变（`trend_direction`、`confidence` 不变）

**Non-Goals:**
- 不改变后端 API 响应结构（兼容现有前端）
- 不修改技术指标计算逻辑
- 不修改 Tavily 搜索逻辑

## Decisions

### Decision 1: 修改 SYSTEM_PROMPT 而非创建新 Agent

**选择**: 直接修改现有 `SYSTEM_PROMPT` 输出格式

**理由**: 现有 agent 已具备搜索和推理能力，只需调整输出格式，无需创建新 agent 增加复杂度

**备选**: 创建新 agent 处理扩展输出 → 复杂度增加，不必要

### Decision 2: 输出格式使用嵌套 JSON 而非纯文本

**选择**: JSON 结构化输出
```json
{
  "情绪分析": {
    "news": [...],
    "summary": "..."
  },
  "技术分析": {...},
  "趋势判断": {...},
  "trend_direction": "up",
  "confidence": 75
}
```

**理由**: 前端可解析并渲染各部分内容，结构清晰便于展示

### Decision 3: 情绪分析包含5天新闻

**选择**: Tavily 搜索返回近5天新闻，展示标题、来源、摘要

**理由**: 5天足够反映短期情绪，又不至于过于冗长

### Decision 4: 趋势判断包含操作建议

**选择**: 操作建议包括：加仓、减仓、持有、建仓/观望

**理由**: 用户最关心的实际问题是"我现在该怎么办"

## Risks / Trade-offs

[Risk] Agent 输出格式不稳定可能导致 JSON 解析失败
→ [Mitigation] 增加 fallback 逻辑，解析失败时降级为原有 summary 字段

[Risk] 新闻数量不足时，情绪分析可能显得单薄
→ [Mitigation] 当新闻不足5条时，展示实际数量并标注"数据有限"

[Risk] 操作建议可能误导用户
→ [Mitigation] 明确标注"建议仅供参考"，不作为投资依据
