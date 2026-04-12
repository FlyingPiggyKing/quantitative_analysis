## Context

The quantitative analysis platform uses Tushare Pro API to fetch stock data. Currently, the watch list shows stock symbols, names, and trend predictions, while the stock detail page displays K-line charts, technical indicators (MACD, RSI, MA), and trend analysis.

Users need quick access to fundamental metrics:
- **PE (市盈率)**: Price-to-Earnings ratio - valuation metric
- **PB (市净率)**: Price-to-Book ratio - valuation metric
- **Turnover Rate (换手率)**: Trading liquidity metric

The Tushare Pro API provides `daily_basic` endpoint that returns these metrics alongside daily trading data.

## Goals / Non-Goals

**Goals:**
- Display current/latest PE and PB on the watch list table
- Display current/latest PE, PB, and turnover rate on the stock detail page header
- Add daily PE and PB line charts below the volume histogram on the detail page
- Create efficient backend API to serve valuation data with caching

**Non-Goals:**
- Real-time streaming of PE/PB (daily data only, no intraday)
- Historical chart for turnover rate (only current value displayed)
- PE/PB comparison across multiple stocks
- Alerts or notifications based on PE/PB thresholds

## Decisions

### 1. Use Tushare `daily_basic` endpoint for valuation data

**Decision**: Fetch PE, PB, turnover rate using `pro.daily_basic()` API.

**Rationale**:
- Returns all three metrics in a single API call
- Daily data aligns with existing K-line data cadence
- Fields: `pe`, `pb`, `turnover_rate` (换手率)

**Alternatives considered**:
- `ts.get_k_data()` + manual calculation: Missing PE/PB, not reliable
- Separate API calls per metric: Inefficient, increases rate limit pressure

### 2. New API endpoint: `GET /api/stock/{symbol}/valuation`

**Decision**: Create dedicated endpoint for valuation data separate from existing kline endpoint.

**Response shape**:
```json
{
  "symbol": "000001",
  "current": {
    "pe": 12.5,
    "pb": 1.2,
    "turnover_rate": 2.5
  },
  "history": [
    {"date": "2026-04-01", "pe": 12.3, "pb": 1.18},
    ...
  ]
}
```

**Rationale**:
- Separates concerns (trading data vs. valuation data)
- Allows independent caching strategies
- Clear contract for frontend consumption

**Alternatives considered**:
- Extend existing `/kline` endpoint: Pollutes clean data separation
- Extend `/indicators` endpoint: Valuation is not a technical indicator

### 3. Extend StockChart component for multi-series display

**Decision**: Reuse existing `lightweight-charts` library and add line series for PE/PB below volume.

**Implementation**:
- Volume histogram remains at bottom (top 20% of chart height)
- PE line series on its own price scale (right side)
- PB line series sharing PE's scale or separate scale
- Each new series in separate `IChartApi` or use `addSeries` with multiple price scales

**Rationale**:
- `lightweight-charts` v5 supports multiple series types
- Consistent look and feel with existing charts
- No new charting library dependencies

**Alternatives considered**:
- Separate smaller charts stacked vertically: More code, less interactive
- Use different library (ECharts, Recharts): Added complexity, inconsistent look

### 4. Cache valuation data for 24 hours

**Decision**: Valuation metrics (daily) don't change within a trading day, so aggressive caching is safe.

**Implementation**:
- Backend: In-memory cache with 24h TTL
- Frontend: React state + localStorage timestamp check

**Rationale**:
- Reduces Tushare API calls (rate limited)
- Improves page load time
- Data accuracy acceptable for daily-trading decisions

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Tushare rate limit** | API calls may fail during heavy usage | Cache aggressively; fallback to cached data with warning |
| **New listings lack PE/PB** | Some stocks show "-" instead of values | Check for null/empty values; display placeholder |
| **PB negative values** | Banks/financial stocks can have negative book value | Handle edge case: show "N/A" for negative PB |
| **Frontend chart complexity** | Multiple series may clutter visualization | Use clear colors, legend, and tooltip |

## Open Questions

1. **Turnover rate chart**: Should turnover rate also be charted (as a line or bar), or just display current value? User said "daily indicators" for PE/PB - clarify if turnover rate should also have a chart.
