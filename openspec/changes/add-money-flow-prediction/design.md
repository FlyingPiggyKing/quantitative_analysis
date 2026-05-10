## Context

The `stock_trend_agent.py` collects technical data (K-line, MACD, RSI, MA, valuation) and passes it to the AI agent via `format_data_context()`. Money flow data is available via `stock_service.get_moneyflow()` but is only used in `ScoringService.calculate_money_flow_score()` for the composite score — it never reaches the AI agent.

Money flow (主力净流入/净流出) tracks institutional/informed money flows and is a leading indicator for short-term price movements. Omitting it from AI analysis is a significant gap.

## Goals / Non-Goals

**Goals:**
- Pass latest money flow data to the AI agent as part of `format_data_context()`
- Update the system prompt so the agent explicitly analyzes money flow signals in `技术分析`
- Keep backward compatibility — if money flow fetch fails, proceed without it
- Align money flow days parameter with frontend display (30 days)

**Non-Goals:**
- Not changing the scoring service or composite score weights
- Not adding new API endpoints
- Not modifying the database schema

## Decisions

### 1. Where to inject money flow data

**Decision:** Inject money flow data into `format_data_context()` alongside existing technical indicators.

**Rationale:** This keeps the data flow consistent — all technical context flows through one function. Adding a separate `format_money_flow_context()` would fragment the context and make it harder for the agent to correlate money flow with price action.

### 2. How to format money flow for the agent

**Decision:** Append money flow data to the existing valuation/估值 section with market-aware unit conversion.

**Example (A-share):```
估值指标:
PE(TTM): 28.50
PB: 5.20
换手率: 2.50%
总市值: 12,500亿元
5日主力净流入: +7.71亿元 (净流入偏多)
```

**Example (HK):```
估值指标:
PE(TTM): 28.50
PB: 5.20
换手率: 2.50%
总市值: 4,300亿HKD
5日主力净流入: +34.58亿HKD (净流入偏多)
```

**Example (US):```
估值指标:
PE(TTM): 28.50
PB: 5.20
换手率: 2.50%
总市值: 6,200亿美元
5日主力净流入: +15.98亿美元 (净流入偏多)
```

**Unit conversion by market:**

| Market | Money Flow Source | Display Unit |
|--------|-----------------|--------------|
| A-share | Tushare `net_d5_amount` in 万元 | ÷10000 → 亿元 |
| HK | Futu `net_d5_amount` in HKD | ÷1e8 → 亿HKD |
| US | Futu `net_d5_amount` in USD | ÷1e8 → 亿美元 |

**Rationale:** Money flow is fundamentally a market/valuation signal — it tells us about the supply/demand dynamics reflected in price. Placing it alongside PE/PB keeps the data organized by category. The `days=30` parameter aligns with frontend display (frontend uses `days=30` for sparkline; the backend AI context also uses `days=30` to show cumulative 5-day net total).

**A-share data source:** A-share `net_5d_total` uses Tushare's official `net_d5_amount` field (5-day cumulative net inflow, pre-computed by Tushare), not a manual sum.

### 3. System prompt update

**Decision:** Add a money flow bullet under "Analyze the provided technical data" section of `get_system_prompt()`.

**Rationale:** The current prompt lists what to analyze. Adding "money flow signals (主力净流入/净流出)" makes it explicit the agent should interpret this data.

### 4. `技术分析` output format

**Decision:** Add a `money_flow` sub-object to the `技术分析` section in the agent output schema.

**Example:**
```json
"money_flow": {
    "net_5d": "+34.58亿HKD",
    "signal": "净流入偏多",
    "interpretation": "5日累计主力净流入，主要由大额流入贡献，短期资金面偏多"
}
```

**Rationale:** The agent already returns `macd`, `rsi`, `ma`, `volume`, `valuation` sub-objects under `技术分析`. Adding `money_flow` is consistent with the existing structure.

### 5. Frontend rendering

**Decision:** Render money flow data in `TrendAnalysisPanel.tsx` under the `技术分析` section, alongside MACD, RSI, MA, Volume, and Valuation cards.

**Implementation:**
- `TechnicalAnalysis` interface in `trendPrediction.ts` extended with `money_flow` field
- `TrendAnalysisPanel.tsx` renders a money flow card with `net_5d` value, `signal` text (green for inflow, red for outflow), and `interpretation`

**Rationale:** Consistent with existing UI structure — each technical indicator has its own card in the grid layout.

## Risks / Trade-offs

- **[Risk]** Money flow API may fail for some stocks → **Mitigation:** Catch exceptions in `analyze_stock_trend()` and pass `money_flow_context = None`. Agent proceeds with available data.

- **[Risk]** Money flow data quality varies by market (A-share has detailed Tushare data; US/HK may have limited data) → **Mitigation:** For markets without detailed data, provide a simplified "N/A" or "limited data" message rather than failing.

- **[Risk]** Adding more context increases token usage → **Mitigation:** 30-day money flow context is ~6 lines of text. Minimal impact on token budget.

## Migration Plan

1. Modify `format_data_context()` to accept optional `money_flow_data` parameter
2. Fetch money flow in `analyze_stock_trend()` before calling `format_data_context()`. Use `days=30` to match frontend.
3. Apply market-aware unit conversion when formatting money flow (A-share ÷10000, HK/US ÷1e8)
4. Update `get_system_prompt()` to include money flow in the analysis checklist
5. Deploy — no database migration needed
6. Rollback: revert the code changes; AI will work without money flow (current behavior)
