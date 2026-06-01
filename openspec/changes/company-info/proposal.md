## Why

A-share stock detail pages (e.g. `/stock/601899`) currently show a "近期行情" (Recent Quotes) table at the bottom, but lack static company profile information (registered capital, chairman, address, main business, etc.). The Tushare `stock_company` API (doc_id=112) is already available, has a 120-point permission tier, and returns the full company profile for A-shares. Replacing the trailing quotes table with a company-info panel for A-share pages gives the user immediately useful context (who runs the company, where it is, what it does) in the same screen real estate.

## What Changes

- Add a new backend service method `AShareService.get_company_info(symbol)` that calls Tushare `stock_company` and normalizes the response.
- Add a new backend endpoint `GET /api/stock/company?symbol=601899` that returns the company profile (A-share only).
- Add a new React `CompanyInfoPanel` component that renders the 17 company fields in a two-column grid with the same vintage style as the rest of the page.
- On the stock detail page, for symbols matching `/^\d{6}$/` (A-shares), **replace** the trailing "近期行情" table section with the new `CompanyInfoPanel`. Non-A-share pages (US/HK) keep the existing recent-quotes table unchanged.
- Cache company info on the backend (Tushare data is static; cache aggressively to stay well under the 120-point rate limit).

## Capabilities

### New Capabilities

- `a-share-company-info`: A-share listed-company basic information. Backend exposes Tushare `stock_company` data via `/api/stock/company`; frontend renders it as a panel replacing the "近期行情" section on `/stock/{6-digit-symbol}` pages.

### Modified Capabilities

- (none) — the existing recent-quotes behavior on US/HK pages is untouched; no existing spec's REQUIREMENTS change.

## Impact

- **Backend**:
  - `backend/services/akshare_service.py` — new `AShareService.get_company_info` + `get_company_info_batch` (for the existing `/api/stock/batch/info` style of caller, if needed).
  - `backend/api/stock.py` — new `GET /api/stock/company` route.
  - New in-memory cache entry keyed by `ts_code` (reuse `_YFCache` pattern with long TTL, e.g. 24h).
- **Frontend**:
  - `frontend/src/app/stock/[symbol]/page.tsx` — replace the "近期行情" `<section>` with a new `CompanyInfoPanel` for `/^\d{6}$/` symbols; new `useSWR` fetch for `/api/stock/company`.
  - New component `frontend/src/components/CompanyInfoPanel.tsx` (or colocated).
- **Permissions**: requires Tushare token with ≥ 120 points; existing `TUSHARE_TOKEN` env var is reused.
- **Failure modes**: if Tushare errors or returns empty, the panel renders an "暂无公司信息" placeholder (no fallback to old table — the replacement is unconditional for A-shares).
