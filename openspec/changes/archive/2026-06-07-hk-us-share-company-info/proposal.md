## Why

The 2026-06-02-company-info change added an A-share company info panel to the stock detail page, replacing the redundant "近期行情" quotes table. The same panel still has to render for HK and US stock pages because the frontend guard `/^\d{6}$/.test(symbol)` skips the panel for those markets — leaving HK and US pages stuck with the same redundant quotes table. Futu's current installed SDK (10.5.6508) does NOT expose a company-profile endpoint — only market data. But the upstream Futu OpenD v10.7 (with futu-api 10.7.6708) DOES expose three new APIs: `get_company_profile` (returns a free-form label-value list of ~20 company fields), `get_company_executives` (returns directors with name, position, gender, age, education, salary), and `get_company_operational_efficiency` (operational metrics). We can give HK/US users a company panel that is actually closer in richness to the A-share one (chairman, secretary, address, business scope, website, phone, email, main business, introduction) by upgrading the SDK and consuming `get_company_profile` + `get_company_executives`.

## What Changes

- Upgrade `futu-api` to `>=10.7.6708` in the backend dependency manifest. (Latest PyPI version: 10.7.6708; OpenD binary must be ≥ matching version — the project already requires a running OpenD for HK/US data.)
- Add `FutuQuoteService.get_company_info(symbol)` that calls `OpenQuoteContext.get_company_profile(code)` and `OpenQuoteContext.get_company_executives(code)` in parallel, then normalizes the response into a structured dict. Cached 24h.
- Extend `GET /api/stock/company?symbol=` to dispatch by market. The 6-digit A-share path is unchanged; HK (`HK.00700` / `00700`) and US (`US.AAPL` / `AAPL`) symbols go to the new Futu method. Reject anything else with HTTP 400.
- Extend the frontend `CompanyInfo` interface to include the Futu fields: a `profile_labels` list of `{name, value, fieldType}` (the raw `get_company_profile` response) and an `executives` list of `{name, position, gender, age, education, begin_date, annual_salary}`. Tag the response with `market: "HK" | "US"`.
- Generalize `CompanyInfoPanel` to render two distinct layouts:
  - **A-share layout** (existing): all 17 Tushare fields including chairman, manager, secretary, reg_capital, employees, main_business, business_scope, introduction.
  - **HK/US layout** (new): the Futu `profile_labels` list rendered as a key-value panel, plus an "高管信息" (executives) section showing the top N executives (chairman/CEO/secretary derived from `positionName` matching), and a "公司简介" block from the profile labels. Unknown/missing labels are silently skipped (not rendered as empty rows).
- Drop the `/^\d{6}$/.test(symbol)` guard on the panel render. Render the panel for ALL symbols. Remove the trailing "近期行情" quotes table for HK/US pages too.
- A-share implementation and `AShareService.get_company_info` are NOT touched.

## Capabilities

### New Capabilities

- `hk-us-share-company-info`: HK/US listed-company basic information backed by Futu OpenAPI v10.7. Backend calls `get_company_profile` + `get_company_executives` and exposes the result via `GET /api/stock/company`. Frontend `CompanyInfoPanel` renders the Futu field set in a new branch for non-6-digit symbols.

### Modified Capabilities

- `a-share-company-info` (existing): the `GET /api/stock/company` endpoint now dispatches by market — A-share symbols still go through `AShareService.get_company_info` with the same 6-digit validation, but the route's symbol validator is extended to accept HK/US symbols. The A-share data shape, A-share cache, and A-share panel layout are unchanged. Add a delta spec under `specs/a-share-company-info/spec.md` documenting the shared route and the sibling HK/US panel branch.

## Impact

- **Backend**:
  - `backend/pyproject.toml` (or `requirements.txt`) — bump `futu-api` to `>=10.7.6708`. New transitive deps: `PyCryptodome`, `python-dateutil` (likely already present).
  - `backend/services/futu_quote_service.py` — new `get_company_info(symbol)` static method (~50 LoC); new module-level `_company_info_cache = _FutuCache(ttl=86400)`. Reuses existing `_FutuCache` pattern.
  - `backend/services/akshare_service.py` — `USStockService.get_company_info` / `HKStockService.get_company_info` delegators that wrap `FutuQuoteService.get_company_info` (mirroring `get_moneyflow` → `get_capital_flow`).
  - `backend/api/stock.py` — the `/company` route's 6-digit guard becomes a market dispatcher. Returns 400 only for symbols matching none of: `/^\d{6}$/`, `/^[A-Z]{1,5}$/`, `/^HK\.\d{4,5}$/`, `/^US\.[A-Z]{1,5}$/`.
- **Frontend**:
  - `frontend/src/services/companyInfo.ts` — extend `CompanyInfo` interface with `market: "A" | "HK" | "US"`, `profile_labels: CompanyLabel[]`, `executives: CompanyExecutive[]`. A-share fields stay optional / nullable.
  - `frontend/src/components/CompanyInfoPanel.tsx` — add a `data.market !== "A"` branch that renders a HK/US layout. The layout iterates `profile_labels` and renders each as a key-value row; renders an "高管信息" block from `executives`; renders a "公司简介" block from the matching profile label.
  - `frontend/src/app/stock/[symbol]/page.tsx` — drop the `/^\d{6}$/.test(symbol)` guard around the panel; render for ALL symbols. Remove the trailing "近期行情" quotes table for non-A-share pages.
- **Permissions / OpenD**: no new env vars. Requires `FUTU_OPEND_HOST` / `FUTU_OPEND_PORT` (already required for all HK/US data) and an OpenD binary at v10.7.6708 or later. If the user's OpenD is older, the new APIs will return an error and the panel will gracefully show "暂无公司信息".
- **Failure modes**: if Futu errors (older OpenD, network blip, unknown symbol), the panel renders "暂无公司信息" — same UX as A-share fallback.
- **No-touch guarantee**: `AShareService.get_company_info`, `_company_cache` (A-share 24h cache), the A-share 6-digit guard, and the A-share panel rendering path are not modified.
