## Why

Financial fundamentals (earnings, ROE, profit margins, growth rates) are the strongest medium-term predictors of stock performance. Adding this data to the stock detail page enables investors to evaluate a stock's fundamental health alongside technical indicators and trend analysis, shifting the tool from short-term focused to medium-term capable.

## What Changes

- **New A-Stock Financial Fundamentals Block**: Display financial health indicators (EPS, ROE, profit margins, revenue growth, debt ratio) in a standalone block below the "AI趋势分析" section. Panel header shows report label (e.g., "2026年一季报") and announcement date (e.g., "2026-04-28发布").
- **New Backend API Endpoint**: `/api/stock/{symbol}/fundamentals` for A-shares returning `fina_indicator` and `income` data from Tushare
- **Conditional Rendering**: The block only appears for A-share stocks (SH/SZ codes, 6-digit format); HK/US stocks show "暂不适用"
- **Latest Period Data**: Display the most recent quarterly financial data available

## Capabilities

### New Capabilities

- `a-stock-financial-fundamentals`: Display financial indicators (EPS, ROE, profit margins, growth rates, debt ratios) on A-share stock detail page. Data sourced from Tushare `fina_indicator` and `income` tables via new backend endpoint.

### Modified Capabilities

- (none — no existing spec behavior changes)

## Impact

- **Backend**: New endpoint `/api/stock/{symbol}/fundamentals` in `backend/api/stock.py`; new service methods in `backend/services/akshare_service.py` calling Tushare `fina_indicator` and `income` APIs
- **Frontend**: New `FinancialIndicatorsPanel` component; integrated into `stock/[symbol]/page.tsx` as a standalone block between "AI趋势分析" and "近期行情", conditionally rendered for A-share only
- **Dependencies**: Requires Tushare token (already configured) with sufficient points (2000+)
- **Data Corrections**: `gross_margin` from Tushare `fina_indicator` returns gross profit in 元 (not %) for quarterly reports; service layer computes correct percentage using `revenue`
- **Market Scope**: A-share only (SH/SZ 6-digit symbols); HK/US markets display "暂不适用"
