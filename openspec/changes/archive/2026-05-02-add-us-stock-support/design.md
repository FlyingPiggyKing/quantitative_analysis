## Context

The system currently only supports Chinese A-share stocks via Tushare Pro API. Users want to track US stocks (Google, Microsoft, NVIDIA, Tesla, Coca-Cola) in the same interface. Tushare Pro provides US stock data through `us_daily` and `us_stock_basic` endpoints with data in `SYMBOL.US` format.

**Current State:**
- Backend: `akshare_service.py` uses `_symbol_to_ts_code()` which only handles A-share symbols (6-digit codes with .SH/.SZ suffix)
- Frontend: `WatchList` and `PresetStockList` display only A-share stocks
- Watchlist storage: Stores `symbol` and `name` without market type

## Goals / Non-Goals

**Goals:**
- Enable US stock data fetching (real-time quotes, K-line, valuation) via Tushare Pro
- Add tab-based market switching (A股/美股) in both WatchList and PresetStockList
- Store market type with watchlist items for filtering
- Display preset US stocks (GOOGL, MSFT, NVDA, TSLA, KO) in guest view 美股 tab
- Maintain modular design with clear separation between A-share and US stock logic

**Non-Goals:**
- Supporting other international markets (HK, EU stocks)
- Real-time US stock WebSocket feeds (batch polling is sufficient)
- Changing existing A-share functionality (must remain backward compatible)

## Decisions

### 1. US Stock Symbol Normalization
**Decision:** Create `us_symbol_to_ts_code()` function that appends `.US` suffix.

```python
def us_symbol_to_ts_code(symbol: str) -> str:
    """Convert US stock symbol to Tushare ts_code format."""
    symbol = symbol.strip().upper()
    if symbol.endswith(".US"):
        return symbol
    return f"{symbol}.US"
```

**Rationale:** Keeps US stock handling separate from A-share logic, avoiding complexity in the existing `_symbol_to_ts_code()` function. Alternatives (unified function with market detection) would require more complex logic and risk breaking existing A-share behavior.

### 2. Market Type Storage
**Decision:** Add `market` column to `user_watchlist` table with values `A` (A-share) or `US` (US stock). Default to `A` for backward compatibility.

**Rationale:** Allows filtering watchlist by market type efficiently. Alternative (filtering by symbol pattern) is fragile and doesn't scale.

### 3. Tab UI Component
**Decision:** Create reusable `StockMarketTabs` component that accepts `A股` and `美股` slot content.

**Rationale:** Reuses consistent tab styling across both `WatchList` and `PresetStockList`. Alternatives (duplicate tab logic) would violate DRY principle.

### 4. Preset Stock Configuration
**Decision:** Add separate `US_PRESET_STOCKS` constant in `presetStocks.ts` alongside existing `PRESET_STOCKS`.

```typescript
export const US_PRESET_STOCKS = [
  { symbol: "GOOGL", name: "Google" },
  { symbol: "MSFT", name: "Microsoft" },
  { symbol: "NVDA", name: "NVIDIA" },
  { symbol: "TSLA", name: "Tesla" },
  { symbol: "KO", name: "可口可乐" },
] as const;
```

**Rationale:** Maintains clear separation between market presets. Each market's presets are independently managed.

### 5. Backend US Stock Data Fetching
**Decision:** Add `get_us_stock_info()`, `get_us_kline_data()`, `get_us_realtime_quote()`, `get_us_daily_basic()` methods to `AkshareService`.

**Rationale:** Modular approach keeps US stock logic separate. Each method follows the same pattern as A-share counterparts for consistency.

### 6. Large File Class Refactoring
**Decision:** Split large Python files into focused classes. Current files exceed reasonable size:
- `akshare_service.py` (382 lines) → Split into `AShareService` and `USStockService` classes
- `stock_trend_agent.py` (471 lines) → Split into `AShareTrendAgent` and `USStockTrendAgent` classes
- `trend_prediction_service.py` (371 lines) → Keep as-is or split if it grows further

**Rationale:** Single Responsibility Principle - each class handles one market type. Easier to maintain, test, and understand. New US stock logic won't pollute A-share classes.

```python
# akshare_service.py structure
class AShareService:
    """Handles A-share stock data via Tushare Pro."""
    def get_stock_info(self, symbol: str) -> dict: ...
    def get_kline_data(self, symbol: str, days: int, ...) -> dict: ...

class USStockService:
    """Handles US stock data via Tushare Pro."""
    def get_stock_info(self, symbol: str) -> dict: ...
    def get_kline_data(self, symbol: str, days: int, ...) -> dict: ...

# stock_trend_agent.py structure
class AShareTrendAgent:
    """Analyzes A-share stock trends."""

class USStockTrendAgent:
    """Analyzes US stock trends."""
```

**Migration:** Create new classes first, then update imports in API routes. Old single-class structure can be deprecated but kept for backward compatibility during transition.

## Risks / Trade-offs

- **[Risk] Tushare US stock data availability** → Some US stocks may not have full data coverage. Fallback to error message rather than crashing.
- **[Risk] Mixed A/US batch queries** → Batch endpoints must handle symbols from both markets without mixing them in API calls. [Mitigation] Group symbols by market type before calling respective Tushare APIs.
- **[Risk] AI trend analysis for US stocks** → Agent prompts may need market-specific context (USD currency, NASDAQ/NYSE listing, different trading hours). [Mitigation] Pass market type to agent; prompts are already parameterized.
- **[Risk] Watchlist migration** → Existing watchlist entries lack `market` field. [Mitigation] Default to `A` for legacy entries; data remains valid.

## Open Questions

1. Should US stock valuation metrics (PE, PB) be displayed differently since they're calculated differently for US stocks?
2. Does Tushare provide US stock `daily_basic` data (PE, PB, turnover rate)? If not, US stocks may show "-" for these fields.
