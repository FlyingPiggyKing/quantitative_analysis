## Why

Currently, money flow data (main force net inflow) is collected via the `/api/stock/{symbol}/moneyflow` endpoint and used in the composite scoring system (10% weight), but it is **not fed to the AI agent** during trend prediction. The AI agent analyzes K-line, MACD, RSI, MA, and valuation data — but lacks the money flow context that captures institutional fund flows, a key leading indicator for short-term price movements.

## What Changes

- Add latest 5-day cumulative money flow data as input to the AI trend prediction agent (using `days=30` lookup window to ensure sufficient history)
- Include money flow signals in the `技术分析` (technical analysis) section of the AI output
- Format money flow data alongside existing technical indicators (MACD, RSI, MA) in the agent prompt
- Apply market-aware unit conversion: A-share uses 万元→亿元, HK uses HKD→亿HKD, US uses USD→亿美元

## Capabilities

### New Capabilities
- `money-flow-analysis-in-agent`: Integrate 5-day cumulative money flow data into the AI agent's technical analysis context. The agent will receive formatted money flow data (main force net inflow/outflow for recent 5 trading days, looked up with `days=30` window) as part of the input, and include money flow signals in its `技术分析` output section. Data is formatted with market-aware units (A-share: 亿元, HK: 亿HKD, US: 亿美元).

### Modified Capabilities
- `stock-trend-prediction-storage`: No change to requirements — this is an implementation-only change
- `technical-indicators`: No change to requirements — money flow is supplementary data, not a traditional technical indicator

## Impact

**Affected code:**
- `backend/services/stock_trend_agent.py`: Update `format_data_context()` to include money flow data; update system prompt to instruct agent to analyze money flow signals
- `backend/services/trend_prediction_service.py`: Fetch and pass money flow data to `analyze_stock_trend()`
- `backend/services/scoring_service.py`: No change — money flow scoring already exists

**New dependency:**
- `moneyflow` data fetch from existing `get_moneyflow()` method — available for A-share (Tushare), US stocks, and HK stocks
