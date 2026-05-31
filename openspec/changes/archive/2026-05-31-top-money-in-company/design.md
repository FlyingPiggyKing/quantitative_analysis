## Context

The 资金流向 sub-module renders `SectorMoneyFlowSankey`, a canvas Sankey chart built from `GET /api/stock/sector-money-flow`. That endpoint calls Tushare `moneyflow_ind_dc` (东方财富 / "DC" industry classification) and returns `daily_top` (top-N sector names per date) plus `net_amounts`. Clicking a flow line sets `highlightedSector` and shows a "已选中: 白酒" block (lines 423–432). The selection currently only highlights the chart.

We want to drill into a selected sector: for each trading day that sector appears in the chart, show the top 5 member companies by main-force net inflow that day. The user's intended data path (per the request) is SW2021:

1. `index_classify(level=..., src='SW2021')` → resolve sector name to an `index_code` (e.g. `801102.SI`).
2. `index_member(index_code=...)` → member `ts_code` list.
3. `moneyflow(trade_date=..., fields='ts_code,buy_elg_amount,sell_elg_amount,buy_lg_amount,sell_lg_amount,net_mf_amount')` → all A-shares for the day, filtered to members.
4. Rank members by `(buy_elg - sell_elg) + (buy_lg - sell_lg)` → top N.
5. `stock_basic(fields='ts_code,name')` → resolve codes to company names.

Existing reusable infrastructure: `backend/api/index_metrics.py` already holds SW Level-1/Level-2 code maps and a Tushare token accessor; `backend/services/akshare_service.py` already has the `_sector_mf_cache` pattern (module-level dict + timestamp + TTL) and `_symbol_to_ts_code`.

Constraints: Tushare is rate-limited (the codebase already guards against "每分钟"/"权限" errors). `moneyflow` returns one row per stock per day for ~5000 stocks; we fetch the whole day once and filter. Per the project CLAUDE.md, per-stock money-flow amounts are in **万元** → divide by `10000` to display 亿元 (distinct from `moneyflow_ind_dc`'s `net_amount` which is in 元 / `1e8`).

## Goals / Non-Goals

**Goals:**
- On sector selection, show top 5 member companies by main-force net inflow for each chart date the sector appears in.
- Resolve the chart's DC sector name to an SW2021 industry index and its members.
- Reuse existing cache patterns and the SW infrastructure in `index_metrics.py`; stay within Tushare rate limits via caching.
- Degrade gracefully when a sector name cannot be mapped to SW2021 or money-flow data is unavailable.

**Non-Goals:**
- No change to the Sankey chart rendering, the `sector-money-flow` endpoint, or its DC data source.
- No persistent database; in-memory caching only (matching the existing module).
- No support for HK/US markets (this is A-share `moneyflow` only).
- No new industry-classification UI; this reuses the existing chart selection.

## Decisions

### Decision 1: New dedicated endpoint, driven by sector name + the chart's dates
`GET /api/stock/sector-top-stocks?sector=<name>&dates=<comma-separated YYYY-MM-DD>&top_n=5`.

The frontend already knows exactly which dates a sector appears in (`daily_top`). Passing those dates avoids re-deriving trading days on the backend and keeps the response aligned to what the chart shows. Response shape:
```json
{
  "sector": "白酒",
  "index_code": "801125.SI",
  "matched_name": "白酒Ⅱ",
  "by_date": {
    "2026-05-29": [{"ts_code":"600519.SH","name":"贵州茅台","net_inflow":12.3,"pe_ttm":30.5,"total_mv_yi":12930.7}, ...],
    "2026-05-27": [ ... ]
  },
  "error": null
}
```
`net_inflow` is in 亿元. `total_mv_yi` is 市值 in 亿元 (≥10000亿 displayed as 万亿, e.g. `1.29万亿`). `by_date` keys are only the requested dates that returned data.

*Alternative considered:* extend `sector-money-flow` to embed per-stock data for every sector. Rejected — wasteful (most sectors never get clicked) and would balloon that payload and its Tushare calls.

### Decision 2: DC → SW2021 name resolution via `index_classify`, with normalization + best-effort matching
The chart sector name comes from the DC taxonomy; member lookup needs an SW2021 `index_code`. Resolution:
1. Cache the full `index_classify(src='SW2021')` table (L1+L2+L3) once per day.
2. Normalize names by stripping trailing roman-numeral variants (`Ⅱ/Ⅲ`, reusing the regex already in `_fetch_sector_moneyflow`) and whitespace.
3. Match the clicked name against the SW table: exact normalized match first; if none, prefer an L2 match whose normalized name equals the clicked name; then fall back to substring containment. Prefer the most specific (deepest level) unambiguous match.
4. If no match, return `error` and an empty `by_date` so the UI can show "无法匹配到申万行业成分股".

*Alternative considered:* hardcode a DC→SW mapping table. Rejected — brittle and large; `index_classify` is authoritative and cached cheaply.

### Decision 3: Fetch the day's full `moneyflow` once per date, filter to members, cache per date
For each requested date, fetch `moneyflow(trade_date=YYYYMMDD, fields=...)` (all A-shares), build a `ts_code → net_inflow` map, then intersect with the member set and rank. Cache the per-date result keyed by `trade_date` with a longer TTL than the 5-min sector cache, since historical daily money-flow is immutable once the market closes. The today value uses a short TTL.

Net inflow per stock (in 万元) = `(buy_elg_amount - sell_elg_amount) + (buy_lg_amount - sell_lg_amount)`, then `/10000` → 亿元. This matches the user's ranking formula (主力 = 特大单 + 大单).

*Alternative considered:* call `moneyflow(ts_code=..., trade_date=...)` per member. Rejected — N calls per date hammers the rate limit; one bulk call per date is far cheaper and the day's table is reused across sectors.

### Decision 4: Caches as module-level dicts mirroring `_sector_mf_cache`
- `_sw_classify_cache`: SW2021 table, daily key.
- `_index_member_cache`: `index_code → [ts_code]`, daily key.
- `_stock_basic_name_cache`: `ts_code → name`, daily key.
- `_moneyflow_day_cache`: `trade_date → {ts_code: net_inflow_yi}`.
- `_stock_basics_cache`: `trade_date → {ts_code: {pe_ttm, total_mv_yi}}`, long TTL for closed days.

Keeps the change self-contained in `akshare_service.py` and consistent with existing style; no new infra.

### Decision 5: Frontend panel as a new child component
`SectorTopStocksPanel` renders below the "已选中" block (after line 432). It receives `sector` and the list of dates (derived from `data.daily_top` where the sector appears) and calls a new `fetchSectorTopStocks` service. It shows, per date (newest first), a ranked table: rank, company name (desktop) / name+code stacked (mobile), PE(TTM), 市值 (亿/万亿), and net inflow (亿元, signed, brass/oxblood coloring consistent with the existing legend). Market cap ≥10000亿 is displayed as 万亿 (e.g. 1.29万亿). Loading and empty/no-match states included. Triggered by `highlightedSector` changing.

## Risks / Trade-offs

- **DC ↔ SW2021 taxonomy mismatch** → A clicked sector may map imperfectly or not at all. Mitigation: normalization + layered matching; explicit "无法匹配" state rather than wrong data. Surfaced to the user instead of silently guessing.
- **Tushare rate limits** (`moneyflow` is a premium-ish endpoint; one call per date can still be heavy) → Mitigation: per-date cache with long TTL for closed days; reuse day table across sectors; reuse existing rate-limit error detection and return `error` gracefully.
- **`moneyflow` permission** — the account may lack access to the per-stock `moneyflow` API even though `moneyflow_ind_dc` works → Mitigation: detect the permission error and return a clear `error` message; document that this endpoint requires `moneyflow` access.
- **Selection without ≥2 dates** — the chart only draws flow lines for sectors appearing on ≥2 dates, but a sector could be highlighted via the legend. The panel handles any number of dates the sector actually appears in (1+).
- **Trade-off: passing dates from the client** couples the panel to the chart's date set. Acceptable — the panel exists only to explain the chart, so sharing its dates is correct by design.

## Migration Plan

Additive feature, no migration. Deploy backend (new endpoint + caches) and frontend (new service + panel) together. Rollback = revert both; the existing chart is unaffected because the `sector-money-flow` endpoint and Sankey rendering are untouched. No data model or schema changes.

## Open Questions

- Should the panel show member stocks that had **outflow** (negative net inflow) when fewer than 5 had inflow, or hard-stop at "top 5 by inflow including negatives"? Current decision: rank by net inflow descending and take top 5 regardless of sign (consistent with the user's "top by inflow" framing); revisit if users want inflow-only.
