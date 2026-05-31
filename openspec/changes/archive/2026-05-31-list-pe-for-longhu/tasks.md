## 1. Backend — Add valuation fields to dragon tiger list

- [x] 1.1 In `akshare_service.py`, add `get_daily_basic_batch` helper or reuse existing single-symbol method to fetch `pe_ttm` and `total_mv` for all unique ts_codes in the dragon tiger result
- [x] 1.2 Modify `get_dragon_tiger_list()` to join `pe_ttm` and `total_mv_yi` (total_mv / 1e8) onto each DragonTigerItem; handle null/zero valuation data gracefully

## 2. API — Update DragonTigerItem schema

- [x] 2.1 Confirm `DragonTigerItem` dataclass in `backend/api/stock.py` (or wherever the response model is defined) includes `pe_ttm: float | None` and `total_mv_yi: float | None` — No explicit dataclass; API returns raw dicts; pe_ttm and total_mv_yi are already added to the dict by the service

## 3. Frontend — Update DragonTigerList component

- [x] 3.1 Add `pe_ttm: number | null` and `total_mv_yi: number | null` to `DragonTigerItem` TypeScript interface
- [x] 3.2 In `DragonTigerRow`, replace the "收盘价" column with "市值(亿)" column (show `total_mv_yi` formatted to 2 decimals, null as "-")
- [x] 3.3 Add "PE TTM" column after or near 市值, showing `pe_ttm` formatted to 1 decimal (e.g., "25.3"), null as "-"
- [x] 3.4 Update column headers in `DragonTigerTable` from "收盘价" to "市值(亿)" and add "PE TTM" header
