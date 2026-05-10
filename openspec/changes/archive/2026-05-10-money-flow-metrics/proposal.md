## Why

Phase 6 of the ENHANCEMENT_ROADMAP calls for Money Flow Score (10% weight in multi-factor scoring). After researching available data sources, the original plan needs adjustment: Northbound capital flow (北向资金) is only available at aggregate market level via Tushare's `moneyflow_hsgt`, not at individual stock level. However, main force net inflow (主力资金净流入) is available for all markets — via Tushare for A-shares (`moneyflow_ths`) and via Futu OpenAPI for HK/US stocks (`get_capital_flow`).

## What Changes

- Add money flow data fetching for A-shares (via Tushare `moneyflow_ths`), HK stocks (via Futu `get_capital_flow`), and US stocks (via Futu `get_capital_flow`)
- Display money flow trend sparkline thumbnails on the watch list, positioned next to PE sparkline thumbnails
- Display money flow data on stock detail page with 5-day cumulative value (主力(5日)) and sparkline
- Each sparkline shows 30-day net inflow trend with red for inflow, green for outflow
- New API endpoints: `/api/stock/{symbol}/moneyflow` supporting all three markets
- Add money flow score to the multi-factor scoring service
- Created `scoring_service.py` with `calculate_money_flow_score()` method

## Capabilities

### New Capabilities

- `money-flow-sparkline`: Display 30-day money flow trend sparkline (inflow/outflow) next to PE thumbnail on watch list. Similar rendering style to `pe-sparkline` spec.
- `a-share-moneyflow-api`: Fetch A-share main force net inflow via Tushare `moneyflow_ths` API (30-day history, includes `net_amount`, `buy_lg_amount`, `net_d5_amount`)
- `hk-us-moneyflow-api`: Fetch HK/US stock main force net inflow via Futu `get_capital_flow` API (30-day history, includes `main_in_flow`)
- `money-flow-score`: Add money flow component (10% weight) to multi-factor scoring system

### Modified Capabilities

- `pe-sparkline`: No spec changes, but the sparkline rendering component will be reused for money flow sparklines with similar styling
- `stock-valuation-metrics`: Add money flow data to the valuation endpoint response structure

## Impact

- **Backend**: New service methods in `akshare_service.py` (Tushare `get_moneyflow` for AShareService, HKStockService, USStockService) and `get_capital_flow` in `futu_quote_service.py`
- **API**: New endpoint `/api/stock/{symbol}/moneyflow` that detects market from symbol prefix (SH/SZ for A-share, HK for HK, US for US)
- **Frontend**: New `MoneyFlowSparkline.tsx` component rendered alongside PE sparkline on watch list and stock detail page
- **Frontend**: Stock detail page shows "主力(5日)" value with sparkline next to PE sparkline
- **Scoring**: New `scoring_service.py` with `calculate_money_flow_score()` method (10% weight)
