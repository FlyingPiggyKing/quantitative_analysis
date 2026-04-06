## Context

This is the initial implementation of a stock analysis platform for Chinese A-shares market. The system provides K-line visualization and technical indicators for manual stock analysis (no quantitative trading).

**Current State:**
- Backend: FastAPI with Tushare Pro API integration
- Frontend: Next.js 15 with TradingView lightweight-charts
- Data Source: Tushare Pro (requires user registration and token)

**Constraints:**
- Tushare Pro has rate limits based on user points (current: 120 points)
- Some API calls limited to 1 per minute (e.g., stock_basic)
- Network access may require proxy configuration

## Goals / Non-Goals

**Goals:**
- Provide stock lookup by 6-digit Chinese stock code
- Display interactive K-line chart with candlestick and volume
- Calculate and display MACD, RSI, Moving Average indicators
- Support daily/weekly/monthly K-line periods
- Configurable via environment variables for sensitive credentials

**Non-Goals:**
- Quantitative trading or automated买卖
- Real-time WebSocket streaming
- Portfolio management
- AI-powered stock analysis (future consideration)
- Multiple data source integration beyond Tushare

## Decisions

### Decision 1: Tushare Pro over AKShare

**Choice**: Tushare Pro API

**Rationale**:
- AKShare depends on eastmoney which blocks Python requests
- Tushare Pro provides stable REST API with Python SDK
- More reliable data source despite rate limits

**Alternatives Considered**:
- AKShare: Connection issues with eastmoney, curl works but not Python
-直接调用东方财富API: More complex authentication

### Decision 2: Backend calculates indicators

**Choice**: Technical indicators calculated in Python backend

**Rationale**:
- Reuse pandas for efficient time-series calculations
- Reduce frontend JavaScript bundle size
- Centralize calculation logic for potential future API exposure

**Alternatives Considered**:
- Frontend calculation: Would duplicate pandas logic in JavaScript
- Separate microservice: Over-architecture for current needs

### Decision 3: Environment variable for token

**Choice**: Tushare token loaded from `.env` file

**Rationale**:
- Keeps sensitive credentials out of version control
- `.gitignore` prevents accidental commits
- Follows 12-factor app methodology

### Decision 4: lightweight-charts for visualization

**Choice**: TradingView lightweight-charts v5

**Rationale**:
- Lightweight, no external dependencies
- Supports candlestick and histogram series
- Time scale and crosshair built-in
- Actively maintained

## Risks / Trade-offs

- **[Risk] Tushare rate limits** → Mitigation: Cache responses, use realtime quotes for quick lookups
- **[Risk] Network proxy requirements** → Mitigation: Document proxy configuration, make it optional
- **[Trade-off] Point system** → Tushare Pro requires points for API access. 120 points limits some endpoints but sufficient for basic functionality

## Open Questions

1. Should we add caching layer (Redis/in-memory) to reduce API calls?
2. What's the strategy for handling Tushare authentication failures gracefully?
3. Future: How to integrate LangChain for AI analysis as originally requested?
