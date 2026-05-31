## Context

The 机构龙虎榜 section shows stocks that appeared on the Dragon Tiger List (top institutional net buys/sells). The current implementation in `akshare_service.py` `get_dragon_tiger_list()` aggregates Tushare `top_list` data per stock and returns: ts_code, name, industry, close, pct_change, net_amount, reason, appear_count.

PE TTM and total market cap (市值) are available via `get_daily_basic(symbol, days=1)` from the existing `stock-valuation-metrics` capability.

## Goals / Non-Goals

**Goals:**
- Show PE TTM and 市值(亿) for each stock in the Dragon Tiger List
- Replace the "收盘价" column with "市值(亿)"
- Add "PE TTM" as a new column

**Non-Goals:**
- Changing AI prediction or any other Dragon Tiger functionality
- Adding PE/PB to the AI analysis context (already exists)

## Decisions

**1. Where to fetch PE TTM and 市值 — join at service layer**

Current flow:
```
get_dragon_tiger_list() → aggregate top_list → return DragonTigerItem[]
```

New flow:
```
get_dragon_tiger_list() → aggregate top_list → collect unique ts_codes
  → batch call get_daily_basic(symbols, days=1) → map pe_ttm, total_mv onto items
  → return DragonTigerItem[] (now with pe_ttm, total_mv_yi)
```

Rationale: Avoids N+1 calls and keeps the join at the service layer rather than in the API endpoint.

**2. Market cap unit — 亿元 (total_mv / 1e8)**

Per project convention in CLAUDE.md: `total_mv` in 元 → `/1e8` 显示为亿. This applies to A-share data from Tushare.

**3. Handling missing valuation data**

If `get_daily_basic` returns an error or null for a symbol, set `pe_ttm: null` and `total_mv_yi: null` — do not fail the whole list.

## Risks / Trade-offs

[Risk] Tushare rate limit on `daily_basic` → Mitigation: batch fetch all symbols in one call with `get_daily_basic_batch` if available, or single call with multiple symbols. Fall back to per-symbol if batch unavailable.

[Risk] `total_mv` may be 0 for stocks under suspension → Mitigation: display null as "-".

[Risk] PE TTM can be negative (loss-making companies) or extremely high → Mitigation: display as-is (numeric string), no special casing needed.

## Open Questions

None — the existing `get_daily_basic` API provides all needed data.
