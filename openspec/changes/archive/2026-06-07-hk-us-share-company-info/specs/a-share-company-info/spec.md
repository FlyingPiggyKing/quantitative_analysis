## MODIFIED Requirements

### Requirement: A-share company info API
The backend SHALL expose `GET /api/stock/company?symbol=` that returns the Tushare `stock_company` profile for a 6-digit A-share. The endpoint is a market dispatcher:

- Symbols matching `/^\d{6}$/` → A-share path → `AShareService.get_company_info` (unchanged).
- Symbols matching `/^[A-Z]{1,5}$/` or `/^US\.[A-Z]{1,5}$/` or `/^[0-9]{4,5}$/` or `/^HK\.[0-9]{4,5}$/` → HK/US path (see `hk-us-share-company-info` capability).
- All other inputs → HTTP 400.

For A-share symbols, the response SHALL be a JSON object containing a `data` field with the Tushare 17 fields below, plus an `error` field (null on success). The `data` object MUST include `market: "A"` (the discriminator that drives the frontend panel's branch) and MUST have `profile_labels: []` and `executives: []` (Futu-only fields, empty for A-share). The `market: "A"` tag was added in §10.1 of tasks.md — without it, the frontend's `data.market === "A"` check fails and the panel falls through to the empty-state.

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

Futu-only fields (`profile_labels`, `executives`) MUST be empty arrays for A-share responses.

The endpoint MUST reject symbols that are not 6-digit A-share codes AND not a valid HK/US symbol with HTTP 400.

#### Scenario: A-share symbol returns company profile
- **WHEN** client calls `GET /api/stock/company?symbol=601899`
- **THEN** backend dispatches to `AShareService.get_company_info` (NOT the Futu path) and calls Tushare `pro.stock_company(ts_code='601899.SH')`
- **THEN** returns 200 with the Tushare 17 fields above populated in `data`, `data.market === "A"`, `data.profile_labels === []`, `data.executives === []`, and `error: null`

#### Scenario: Non-A-share, non-HK/US symbol is rejected
- **WHEN** client calls `GET /api/stock/company?symbol=ABC123` (6 chars but not all digits) or any string matching none of the supported regexes
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}` and does not call Tushare or Futu

#### Scenario: Unknown A-share symbol
- **WHEN** client calls `GET /api/stock/company?symbol=999999` and Tushare returns no rows
- **THEN** backend returns 200 with `{"data": null, "error": "未找到该公司信息"}`

#### Scenario: Tushare upstream error
- **WHEN** Tushare raises an exception or returns a non-OK response
- **THEN** backend returns 200 with `{"data": null, "error": "获取公司信息失败: <message>"}` and does not crash

### Requirement: Backend caches company info
The backend MUST cache the Tushare `stock_company` response per `ts_code` for at least 24 hours. Cache hits MUST NOT call Tushare again. (The HK/US company-info path has its own 24h cache; this requirement applies only to the A-share path.)

#### Scenario: Repeated request within TTL is served from cache
- **WHEN** `GET /api/stock/company?symbol=601899` is called a second time within 24 hours
- **THEN** the response is served from the in-process A-share cache and Tushare is not called

### Requirement: Frontend replaces recent-quotes table with company info panel on A-share pages
On the stock detail page (`/stock/{symbol}`), when `symbol` matches `/^\d{6}$/` (A-share), the page MUST render a `CompanyInfoPanel` in place of the existing "近期行情" data table section. The `CompanyInfoPanel` MUST receive `data.market === "A"` and MUST render the A-share layout (chairman, manager, secretary, reg_capital, employees, main_business, business_scope, introduction, etc.).

The A-share layout MUST display at minimum: company full name, registered capital (converted to 亿元), registered date, province + city, chairman, manager, board secretary, office, employees, website (as a link), main business, and business scope. Long text fields (introduction, main_business, business_scope) MUST be wrapped/truncated so they do not break the page layout.

The same component on non-A-share pages renders a sibling HK/US layout (see `hk-us-share-company-info`); the A-share layout MUST NOT iterate over `profile_labels` / `executives` and the HK/US layout MUST NOT include the A-share fields.

#### Scenario: A-share page renders A-share branch of company info panel
- **WHEN** user opens `http://localhost:3000/stock/601899`
- **THEN** the page fetches `/api/stock/company?symbol=601899` and renders a `CompanyInfoPanel` with `data.market === "A"` containing 紫金矿业's company name, registered capital, address, chairman, etc.
- **THEN** the page does NOT render the "近期行情" data table
- **THEN** the panel does NOT render the `profile_labels`/`executives` sections (which are empty for A-share anyway)

#### Scenario: A-share company info load failure shows placeholder
- **WHEN** the `/api/stock/company` request fails or returns `data: null`
- **THEN** the panel renders a "暂无公司信息" placeholder inside the panel (not a full-page error)
- **THEN** the rest of the page (price header, trend prediction, financial indicators) still renders normally

#### Scenario: A-share company info loading state
- **WHEN** the `/api/stock/company` request is in flight
- **THEN** the panel shows a skeleton/loading state consistent with the rest of the page's vintage style
