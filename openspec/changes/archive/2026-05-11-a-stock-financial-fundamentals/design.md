## Context

The stock detail page currently displays technical indicators (MACD, RSI, MA) and market valuation (PE, PB, turnover rate). A-share stocks have rich financial reporting data available via Tushare's `fina_indicator` and `income` tables, providing EPS, ROE, profit margins, growth rates, and debt ratios — the most powerful medium-term stock selection factors.

## Goals / Non-Goals

**Goals:**
- Add a new "财务指标" block on the A-share stock detail page showing latest quarter financial data
- Create backend API endpoint returning filtered financial indicators from Tushare
- Keep the block visually consistent with existing panels (same design system)
- HK/US stocks show "暂不适用" message in place of data

**Non-Goals:**
- Historical financial data tracking (time-series charts for fundamentals)
- Financial data for HK/US stocks (FutuAPI doesn't provide this)
- Earnings forecast/express data integration (these tables are often empty)
- Editing or predicting financial data

## Decisions

### 1. Data Source: `fina_indicator` + `income` (not `forecast`/`express`)

We tested `forecast` (业绩预告) and `express` (业绩快报) — both returned empty DataFrames for 平安银行 in 2025Q1. These tables are sparse and unreliable. We use `fina_indicator` (quarterly) and `income` (quarterly) tables which returned complete data.

**Alternatives considered:**
- `balance` (资产负债表) — too many fields, more complex; `fina_indicator` already derives key ratios from it
- `cashflow` — useful but secondary; add later if needed

### 2. Display Fields: Curated subset with corrected `gross_margin`

| Category | Fields | Source | Notes |
|----------|--------|--------|-------|
| **报告信息** | `period`, `ann_date`, `report_label` | `fina_indicator` | `report_label` derived from `end_date` (0331→一季报, 0630→半年报, 0930→三季报, 1231→年报) |
| **EPS** | `eps`, `bps` | `fina_indicator` | |
| **ROE** | `roe`, `roe_yearly` | `fina_indicator` | `roe_yearly` is Tushare raw value: for quarterly reports it's `roe × 4` (not a true annualized figure); treat as reference only |
| **Profitability** | `gross_margin`, `netprofit_margin` | computed / `fina_indicator` | **`gross_margin` correction**: Tushare `fina_indicator.gross_margin` returns gross profit in 元 for quarterly reports (e.g., 5,175,926,820.42), not a percentage. If value > 1000, compute as `(gross_margin / revenue) × 100` to get the correct % |
| **Growth (YoY)** | `basic_eps_yoy`, `netprofit_yoy`, `tr_yoy` | `fina_indicator` | |
| **Financial Health** | `debt_to_assets`, `current_ratio` | `fina_indicator` | |
| **Revenue/Profit** | `total_revenue`, `n_income` | `income` | |

### 3. `gross_margin` Data Correction (Critical)

Tushare's `fina_indicator.gross_margin` is inconsistent across report types:
- **Annual reports**: returns a percentage (e.g., `33.26` for 33.26%)
- **Quarterly reports**: returns gross profit in 元 (e.g., `5,175,926,820.42`)

**Fix**: Heuristic — if `gross_margin > 1000`, treat it as gross profit in 元 and compute percentage:
```
gross_margin_corrected = (gross_margin_raw / revenue) × 100
```
Verified with 阳光电源 (300274) Q1 2026: `5,175,926,820.42 / 15,560,645,284.03 × 100 = 33.26%` ✓

### 4. Report Label Derivation

`report_label` is derived from `end_date` (period) month-day suffix:

| end_date suffix | report_label |
|-----------------|--------------|
| `0331` | `YYYY年一季报` |
| `0630` | `YYYY年半年报` |
| `0930` | `YYYY年三季报` |
| `1231` | `YYYY年年报` |

`ann_date` is displayed as `YYYY-MM-DD发布` (e.g., "2026-04-28发布").

### 5. Display Layout: 4-column grid, collapsible

Mirrors `IndicatorPanel` layout:
- 4 columns on desktop (matching MACD/RSI/MA columns)
- Collapsible with `−`/`+` toggle
- Same styling: `vt-panel`, `GroupTitle`, `Cell` sub-components
- Block is a standalone `vt-panel` below "AI趋势分析"

### 6. Error Resilience

The `income` API call is wrapped in `try/except`:
- If `income` fails (e.g., rate limit), `fina_indicator` data is still returned
- `gross_margin` computation still works if `revenue` was already returned from a prior call
- Rate limit errors are logged as warnings, not propagated as errors

### 7. Only A-share

The block renders "暂不适用" for non-6-digit symbols (HK/US). No backend calls are made for those markets.

## Risks / Trade-offs

- **[Risk] Field `None` values**: Many `fina_indicator` fields return `None` when not reported for a given period. → **Mitigation**: Frontend displays `--` for null values; no error shown
- **[Risk] `roe_yearly` non-standard**: For quarterly reports, Tushare returns `roe × 4`, which is not a true annualized ROE. It's a raw Tushare value; user should interpret as "Q1 × 4 reference" only. → **Mitigation**: Documented; no fix needed in code
- **[Risk] Tushare rate limit**: `fina_indicator` + `income` = 2 API calls per request. → **Mitigation**: `income` call is gracefully wrapped; `fina_indicator` data still returns on failure

## Migration Plan

1. Add `get_financial_fundamentals` to `AShareService`
2. Add `/api/stock/{symbol}/fundamentals` endpoint to `backend/api/stock.py`
3. Create `FinancialIndicatorsPanel.tsx` component
4. Add component as standalone block in `stock/[symbol]/page.tsx` below "AI趋势分析", wrapped in A-share check
5. Verify with known A-share symbols (e.g., `000001.SZ`, `300274.SZ`)

## Open Questions

- ~~Should we display YoY growth with color coding (green/red for positive/negative)?~~ **DONE**: implemented with red for positive, green for negative
- ~~Should we add `report_type` to clarify annual vs quarterly data?~~ **DONE**: `report_label` derived from `end_date` and displayed in panel header
