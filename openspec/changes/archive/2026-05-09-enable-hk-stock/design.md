## Context

**Current state**: The system supports US stocks via `FutuQuoteService` (which maps symbols like `AAPL` → `US.AAPL` in Futu codes) and A-shares via Tushare. Both markets share the same REST API endpoints (`/api/stock/{symbol}`), with routing based on symbol pattern (1-5 letters = US, 6 digits = A-share).

**HK stock motivation**: Hong Kong stocks (e.g., Tencent `00700`, Alibaba `9988`) are commonly requested and can be served through the same Futu OpenD connection already running for US stocks. Futu uses `HK.XXXXX` prefix for HK securities.

**Symbol routing challenge**: HK stock codes are 4-5 digits, which partially overlaps with the current US stock detection (1-5 letters, non-digit). We must distinguish HK codes (digits only) from US codes (letters only).

## Goals / Non-Goals

**Goals:**
- Enable HK stock data (info, K-line, realtime quote, valuation metrics) via Futu OpenAPI
- Maintain full parity with US stock functionality (same endpoints, same response shape)
- Zero impact on existing A-share and US stock services
- Use the same `FutuQuoteService` class, extending symbol conversion logic

**Non-Goals:**
- No new API routes — routing happens at service layer by symbol pattern
- No changes to Futu OpenD configuration (HK market is accessible via the same connection)
- No batch multi-market mixing support (batch already routes by symbol pattern per-item)
- No order/trading functionality for HK (only data)

## Decisions

### Decision 1: Symbol detection for HK stocks
**Choice**: Add `_is_hk_stock_symbol(symbol)` that returns `True` for 4-5 digit symbols that are not A-share codes (6 digits).

**Rationale**: US stocks are 1-5 letters (e.g., `AAPL`, `TSLA`). A-shares are exactly 6 digits. HK stocks are 4-5 digits (e.g., `00700`, `9988`). So the routing hierarchy is:
1. If 6 digits → A-share (Tushare)
2. If 4-5 digits → HK stock (Futu)
3. If 1-5 letters → US stock (Futu)

This avoids any ambiguity since no market uses the same symbol format.

### Decision 2: HK symbol conversion functions
**Choice**: Add `_symbol_to_hk_futu_code(symbol)` → `HK.00700` and `_hk_futu_code_to_symbol(futu_code)` → `00700`.

**Rationale**: Mirrors the existing US stock pattern (`_symbol_to_futu_code` → `US.AAPL`). The existing `_symbol_to_futu_code` is US-specific and returns `US.XXX`; HK needs a separate function since the prefix differs.

### Decision 3: Market field in responses
**Choice**: `market: "HK"` for HK stock responses (mirroring `market: "US"` for US stocks).

**Rationale**: Frontend may use the `market` field to display labels or apply formatting. Keeping parity simplifies frontend code.

### Decision 4: Reuse same `FutuQuoteService` methods
**Choice**: No duplication of `get_snapshot`, `get_kline_data`, etc. The existing methods accept any Futu code — we just need to pass the correct code (`HK.00700` instead of `US.AAPL`).

**Rationale**: The underlying Futu API handles any market; only the code prefix differs. Duplicating methods would double maintenance burden.

### Decision 5: `HKStockService` wrapper in `akshare_service.py`
**Choice**: Add `HKStockService` class mirroring `USStockService`, calling the same `FutuQuoteService` methods.

**Rationale**: Maintains the existing service-layer routing pattern. The dispatch functions (`get_stock_info`, `get_kline_data`, etc.) already route by symbol — they just need the HK condition added.

## Risks / Trade-offs

**[Risk] Symbol overlap between HK and US (unlikely)** → A US stock symbol like `BRK.B` has a dot; HK codes are purely numeric. Dot-separated symbols are unambiguously US stocks.

**[Risk] HK stock codes can be 5 digits with leading zeros** → `00700` should be preserved exactly. We must NOT strip leading zeros. The existing `symbol.upper()` in routing must be careful not to drop leading zeros from 4-digit codes like `9988`.

**[Risk] `get_snapshot` for HK stocks may return different field names** → Futu's field names are market-agnostic (`pe_ttm_ratio`, `pb_ratio`, etc.), but we should verify the same fields are returned. [Mitigation: Validate during implementation against a known HK stock like `00700`.]

**[Risk] Batch endpoints mix US and HK** → The existing batch functions iterate per-symbol and route individually, so mixed batches will work correctly. No changes needed.

## Open Questions

1. **Sector data for HK stocks**: Futu snapshot may not provide sector for HK stocks. If `unknown` is returned, is that acceptable? (Same behavior as current US stocks.)
2. **HK stock name encoding**: Futu returns HK stock names in UTF-8. Should we validate display is correct?
