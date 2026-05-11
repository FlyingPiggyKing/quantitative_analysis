## 1. Backend: Add Financial Data Fetching

- [x] 1.1 In `analyze_stock_trend()`, add fetching of financial fundamentals for A-share stocks using `AShareService.get_financial_fundamentals(symbol)`
- [x] 1.2 Pass `financial_data` to `format_data_context()` function

## 2. Backend: Extend format_data_context

- [x] 2.1 Add `financial_data` parameter to `format_data_context()` function signature
- [x] 2.2 Implement finance metrics text block formatting when `market == "A"` and `financial_data` is valid (no `error` key)
- [x] 2.3 Handle null fields by displaying `--`
- [x] 2.4 Skip finance metrics block when data is unavailable or contains error
- [x] 2.5 Fix `total_revenue` and `n_income` unit conversion from 元 to 亿元 (divide by 1e8)
- [x] 2.6 Fix `debt_to_assets` display to remove leading `+` sign

## 3. Backend: Update Agent Prompt

- [x] 3.1 Separate system prompt by market: A-share vs HK/US each have independent prompts
- [x] 3.2 A-share prompt includes `finance_metrics` example in `技术分析`
- [x] 3.3 HK/US prompt does NOT include `finance_metrics` field
- [x] 3.4 Both prompts use Chinese language (all users are Chinese)
- [x] 3.5 Add `money_flow` to HK/US example in `技术分析`

## 4. Frontend: Update TypeScript Interface

- [x] 4.1 Add optional `finance_metrics` field to `TechnicalAnalysis` interface in `trendPrediction.ts`
- [x] 4.2 Define the finance_metrics structure with `summary` and `interpretation` fields

## 5. Frontend: Update TrendAnalysisPanel

- [x] 5.1 Add `finance_metrics` rendering in `TechnicalSection` component
- [x] 5.2 Finance metrics block displays after `money_flow` block
- [x] 5.3 Uses optional chaining `data.finance_metrics &&` to ensure HK/US compatibility

## 6. Verification

- [ ] 6.1 Test A-share stock prediction includes finance metrics in context and output
- [ ] 6.2 Verify HK/US stocks do NOT include finance metrics in output
- [ ] 6.3 Verify frontend correctly displays finance_metrics when present
- [ ] 6.4 Verify `total_revenue` and `n_income` display in 亿元 (not 元)
- [ ] 6.5 Verify `debt_to_assets` displays without `+` prefix
