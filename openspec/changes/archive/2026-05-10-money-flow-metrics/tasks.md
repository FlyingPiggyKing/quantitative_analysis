## 1. Backend: A-Share Money Flow API (Tushare)

- [x] 1.1 Add `get_moneyflow(symbol, days=30)` method to `AShareService` using `pro.moneyflow_ths` API
- [x] 1.2 Normalize response to include `trade_date`, `net_amount`, `buy_lg_amount`, `net_d5_amount` fields
- [x] 1.3 Add `net_5d_total` calculation (sum of last 5 `buy_lg_amount`)
- [x] 1.4 Add error handling for empty DataFrame and API exceptions

## 2. Backend: HK/US Money Flow API (Futu)

- [x] 2.1 Locate existing Futu service file (`backend/services/futu_quote_service.py`)
- [x] 2.2 Add `get_capital_flow(symbol, days=30)` method using `get_capital_flow` with `PeriodType.DAY`
- [x] 2.3 Normalize response to include `date`, `main_in_flow` fields
- [x] 2.4 Add market detection from symbol prefix (HK. or US.)
- [x] 2.5 Add error handling for connection/API exceptions
- [x] 2.6 Add `get_moneyflow()` wrapper to `HKStockService` and `USStockService`

## 3. Backend: Unified API Endpoint

- [x] 3.1 Add GET `/api/stock/{symbol}/moneyflow` endpoint in `backend/api/stock.py`
- [x] 3.2 Implement market detection from symbol prefix (SH/SZ → Tushare, HK/US → Futu)
- [x] 3.3 Route to appropriate service based on detected market
- [x] 3.4 Return unified response format with `symbol`, `market`, `data`, `latest`, `net_5d_total` fields
- [x] 3.5 Handle unsupported symbol format with 400 error

## 4. Backend: Money Flow Score Integration

- [x] 4.1 Create `scoring_service.py` with `calculate_money_flow_score()` method
- [x] 4.2 Implement scoring logic: positive for net inflow, negative for net outflow, 0 for errors
- [x] 4.3 Update `calculate_composite_score()` to include money_flow at 10% weight
- [x] 4.4 Add `money_flow` to score breakdown in composite response

## 5. Frontend: Money Flow Sparkline Component

- [x] 5.1 Create `MoneyFlowSparkline.tsx` component (80×30px SVG)
- [x] 5.2 Color convention: red (#ef4444) for inflow, green (#22c55e) for outflow
- [x] 5.3 Handle null values by skipping data points
- [x] 5.4 Show "-" placeholder (gray #9ca3af) when no data
- [x] 5.5 Show skeleton placeholder (#e5e7eb) while loading

## 6. Frontend: Integrate Money Flow into Watch List

- [x] 6.1 Locate existing watch list component (`frontend/src/components/WatchList.tsx`)
- [x] 6.2 Add `fetchMoneyFlowByMarket()` function to fetch moneyflow for each symbol
- [x] 6.3 Render `<MoneyFlowSparkline />` with label "主力资金" next to PE sparkline
- [x] 6.4 Add "主力资金" column header in desktop table and "主力" label in mobile view

## 7. Frontend: Integrate Money Flow into Stock Detail Page

- [x] 7.1 Add `MoneyFlowSparkline` import and `moneyFlowHistory` state to stock detail page
- [x] 7.2 Fetch moneyflow data via `/api/stock/{symbol}/moneyflow?days=30`
- [x] 7.3 Display "主力(5日)" label with 5-day cumulative value and sparkline next to PE sparkline
- [x] 7.4 Show inflow value in red (+X.X亿), outflow value in green (X.X亿)

## 8. Bug Fixes

- [x] 8.1 Fix `_is_hk_stock_symbol()` to recognize `HK.` prefix (was missing)
- [x] 8.2 Fix `_is_us_stock_symbol()` to recognize `US.` prefix (was missing)
- [x] 8.3 Fix Futu `get_capital_flow()` parameter name: `code` → `stock_code`
- [x] 8.4 Fix Futu `get_capital_flow()` return value count: expected 3, got 2

## 9. Testing & Verification

- [ ] 9.1 Test A-share money flow: call `/api/stock/SH600000/moneyflow` and verify data
- [ ] 9.2 Test HK stock money flow: call `/api/stock/HK.00700/moneyflow` and verify data
- [ ] 9.3 Test US stock money flow: call `/api/stock/US.AAPL/moneyflow` and verify data
- [ ] 9.4 Verify sparklines render correctly on watch list for each market type
- [ ] 9.5 Verify stock detail page shows "主力(5日)" value correctly
- [ ] 9.6 Test error cases: invalid symbol, API failures
