## ADDED Requirements

### Requirement: A-share company info API
The backend SHALL expose `GET /api/stock/company?symbol=<6-digit-symbol>` that returns the Tushare `stock_company` profile for the given A-share. The response SHALL be a JSON object containing a `data` field with the company fields below, plus an `error` field (null on success).

The returned `data` object SHALL include (when present in the upstream Tushare response):
- `ts_code` (str) — e.g. `601899.SH`
- `com_name` (str) — full company name
- `com_id` (str) — unified social credit code (统一社会信用代码)
- `exchange` (str) — `SSE` / `SZSE` / `BSE`
- `chairman` (str) — legal representative
- `manager` (str) — general manager
- `secretary` (str) — board secretary
- `reg_capital` (float) — registered capital in **万元** (frontend will convert to 亿元 for display by dividing by 10000)
- `setup_date` (str) — YYYY-MM-DD
- `province` (str)
- `city` (str)
- `introduction` (str, may be long) — company description
- `website` (str)
- `email` (str)
- `office` (str) — registered office address
- `employees` (int)
- `main_business` (str)
- `business_scope` (str)

The endpoint MUST reject symbols that are not 6-digit A-share codes with HTTP 400.

#### Scenario: A-share symbol returns company profile
- **WHEN** client calls `GET /api/stock/company?symbol=601899`
- **THEN** backend calls Tushare `pro.stock_company(ts_code='601899.SH')` and returns 200 with the 17 fields above populated in `data`, and `error: null`

#### Scenario: Non-A-share symbol is rejected
- **WHEN** client calls `GET /api/stock/company?symbol=AAPL`
- **THEN** backend returns HTTP 400 with `{"error": "A-share symbol required (6-digit numeric)"}` and does not call Tushare

#### Scenario: Unknown A-share symbol
- **WHEN** client calls `GET /api/stock/company?symbol=999999` and Tushare returns no rows
- **THEN** backend returns 200 with `{"data": null, "error": "未找到该公司信息"}`

#### Scenario: Tushare upstream error
- **WHEN** Tushare raises an exception or returns a non-OK response
- **THEN** backend returns 200 with `{"data": null, "error": "获取公司信息失败: <message>"}` and does not crash

### Requirement: Backend caches company info
The backend MUST cache the Tushare `stock_company` response per `ts_code` for at least 24 hours. Cache hits MUST NOT call Tushare again.

#### Scenario: Repeated request within TTL is served from cache
- **WHEN** `GET /api/stock/company?symbol=601899` is called a second time within 24 hours
- **THEN** the response is served from the in-process cache and Tushare is not called

### Requirement: Frontend replaces recent-quotes table with company info panel on A-share pages
On the stock detail page (`/stock/{symbol}`), when `symbol` matches `/^\d{6}$/` (A-share), the page MUST render a `CompanyInfoPanel` in place of the existing "近期行情" data table section. Non-A-share pages (US/HK) MUST continue to render the existing "近期行情" table unchanged.

The `CompanyInfoPanel` MUST display at minimum: company full name, registered capital (converted to 亿元), registered date, province + city, chairman, manager, board secretary, office, employees, website (as a link), main business, and business scope. Long text fields (introduction, main_business, business_scope) MUST be wrapped/truncated so they do not break the page layout.

#### Scenario: A-share page renders company info panel
- **WHEN** user opens `http://localhost:3000/stock/601899`
- **THEN** the page fetches `/api/stock/company?symbol=601899` and renders a `CompanyInfoPanel` containing 紫金矿业's company name, registered capital, address, chairman, etc.
- **THEN** the page does NOT render the "近期行情" data table

#### Scenario: US stock page still shows recent quotes
- **WHEN** user opens `http://localhost:3000/stock/AAPL`
- **THEN** the page renders the "近期行情" data table as before and does NOT render the `CompanyInfoPanel`

#### Scenario: HK stock page still shows recent quotes
- **WHEN** user opens `http://localhost:3000/stock/00700` (or any HK symbol)
- **THEN** the page renders the "近期行情" data table as before and does NOT render the `CompanyInfoPanel`

#### Scenario: Company info load failure shows placeholder
- **WHEN** the `/api/stock/company` request fails or returns `data: null`
- **THEN** the page renders a "暂无公司信息" placeholder inside the panel (not a full-page error)
- **THEN** the rest of the page (price header, trend prediction, financial indicators) still renders normally

#### Scenario: Company info loading state
- **WHEN** the `/api/stock/company` request is in flight
- **THEN** the panel shows a skeleton/loading state consistent with the rest of the page's vintage style
