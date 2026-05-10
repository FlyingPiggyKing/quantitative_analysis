## Context

Phase 6 of ENHANCEMENT_ROADMAP calls for money flow data to feed the multi-factor scoring system (10% weight). The original plan assumed northbound capital flow (北向资金) available at stock level, but research shows:

- `moneyflow_hsgt` (northbound capital) is only available at **aggregate market level**, not per-stock
- Individual stock main force net inflow (主力资金净流入) is available:
  - **A-shares**: Tushare `moneyflow_ths` → `buy_lg_amount` (主力大单净流入), `net_d5_amount` (5日累计)
  - **HK stocks**: Futu `get_capital_flow` → `main_in_flow`
  - **US stocks**: Futu `get_capital_flow` → `main_in_flow`

The PE sparkline (`pe-sparkline` spec) already exists and renders 80×30px SVG sparklines on the watch list. We will reuse this pattern for money flow sparklines.

## Goals / Non-Goals

**Goals:**
- Fetch 30-day main force net inflow history for all supported markets (A-share via Tushare, HK/US via Futu)
- Display money flow sparkline thumbnails (80×30px SVG) adjacent to PE sparklines on watch list and stock detail page
- Color code: red for net inflow, green for net outflow
- Display 5-day cumulative value (主力(5日)) on stock detail page
- Create REST API `/api/stock/{symbol}/moneyflow` that handles symbol routing by market
- Integrate money flow score (10% weight) into `scoring_service.py`

**Non-Goals:**
- Northbound capital flow at stock level (not available per research)
- Aggregate market-level northbound flow display (deferred to future work)
- Full money flow dashboard (deferred — only sparkline thumbnail needed for scoring context)

## Decisions

### 1. API Endpoint Design: Unified `/api/stock/{symbol}/moneyflow`

**Decision**: Single endpoint that auto-detects market from symbol prefix.

**Why**: Keeps API surface minimal. Symbol format already distinguishes markets:
- `SH600000` / `SZ000001` → A-share (Tushare `moneyflow_ths`)
- `HK.00700` → HK stock (Futu `get_capital_flow`)
- `US.AAPL` → US stock (Futu `get_capital_flow`)

**Alternatives considered**:
- Separate endpoints (`/api/ashare/moneyflow`, `/api/hk/moneyflow`, `/api/us/moneyflow`) — adds unnecessary complexity given symbol-based routing already exists elsewhere in codebase

### 2. Tushare API: `moneyflow_ths` vs `moneyflow`

**Decision**: Use `moneyflow_ths` for A-shares (not `moneyflow`).

**Why**: `moneyflow_ths` is specifically for China A-stocks and returns cleaner data:
- `buy_lg_amount`: 主力（大单）净流入 directly
- `net_d5_amount`: 5日主力净流入累计 (useful for scoring)

`moneyflow` is more generic but returns more fields requiring computation to derive main force net.

### 3. Sparkline Rendering: Reuse PE Sparkline Component

**Decision**: Clone the existing PE sparkline React component for money flow.

**Why**: PE sparkline is already implemented and working. Money flow sparkline has identical dimensions and similar rendering pattern. Duplicating with a different data source is faster than abstracting into a shared component.

### 4. Futu `PeriodType.DAY` for 30-Day History

**Decision**: Use `PeriodType.DAY` with explicit date range.

**Why**: `get_capital_flow` returns daily main force flow. User confirmed 24 trading days of data available for the test period (2026-04-01 to 2026-05-10). Using explicit date range is more reliable than trying to use higher-period types.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Futu rate limiting on `get_capital_flow` | Cache results for 15 min; batch requests where possible |
| Tushare points exhaustion | `moneyflow_ths` requires 2000+ points; add error handling + fallback to empty data |
| Different units across data sources (元 vs 万元) | Normalize all values to same unit in API response |
| Missing data for some stocks | Return `{"symbol": s, "data": [], "error": null}` — frontend shows "-" placeholder |

## Bugs Fixed During Implementation

1. **Symbol detection for `HK.` prefix**: `_is_hk_stock_symbol()` did not recognize `HK.00700` format, causing HK stocks to be routed to A-share service. Fixed to check `symbol.startswith("HK.")`.

2. **Symbol detection for `US.` prefix**: `_is_us_stock_symbol()` did not recognize `US.AAPL` format. Fixed to check `symbol.startswith("US.")`.

3. **Futu API parameter name**: `get_capital_flow()` uses `stock_code` not `code` as parameter name.

4. **Futu API return value count**: `get_capital_flow()` returns 2 values `(ret, data)`, not 3 values (was expecting `page_req_key`).

## Open Questions

1. **Data freshness timing**: Tushare `moneyflow_ths` and Futu `get_capital_flow` both update after market close. Should API cache with TTL? (Recommend: yes, 15 min TTL in memory cache)
