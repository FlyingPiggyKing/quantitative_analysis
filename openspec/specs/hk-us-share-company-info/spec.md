## ADDED Requirements

### Requirement: Futu SDK is upgraded to v10.7
The backend dependency manifest SHALL require `futu-api >= 10.7.6708`. The new SDK exposes `OpenQuoteContext.get_company_profile` (proto 3243), `OpenQuoteContext.get_company_executives`, and `OpenQuoteContext.get_company_operational_efficiency`. The existing `_get_quote_context` factory continues to return a single shared `OpenQuoteContext`; concurrent calls to multiple new methods on the same context are safe per the existing pattern in `futu_quote_service.py`.

The Futu OpenD binary running on the user's machine MUST also be at v10.7.6708 or later — older OpenD does not recognize the new proto IDs and returns "Unknown protocol ID" errors. The SDK and OpenD must be version-matched.

#### Scenario: SDK version is at least 10.7.6708
- **WHEN** `uv pip show futu-api` is run in `backend/`
- **THEN** the installed version is `>= 10.7.6708`
- **THEN** `from futu import OpenQuoteContext; OpenQuoteContext.get_company_profile` resolves (i.e. the method exists)

#### Scenario: Older SDK fails the import check
- **WHEN** the installed `futu-api` is `< 10.7.6708`
- **THEN** `OpenQuoteContext.get_company_profile` does not exist and the backend `import` for the new company-info service method fails
- **THEN** a clear error message tells the implementer to run `uv pip install --upgrade "futu-api>=10.7.6708"`

### Requirement: OpenD Language setting controls label language
The language of the labels returned by Futu `get_company_profile` is controlled by the OpenD GUI's "Language" preference (set to "Simplified Chinese" in the GUI settings, NOT via editing `~/.com.futunn.FutuOpenD/UI/OpenD.xml` — the GUI overwrites the XML on restart). The Futu Python SDK exposes no `language` parameter; the choice is a server-side preference keyed to the OpenD instance.

- **HK tickers with OpenD set to Simplified Chinese**: server returns Chinese label names (公司全称, 上市日期, 法定代表人, etc.).
- **HK tickers with OpenD set to English**: server returns English label names (COMPANY NAME, LISTING DATE, CHAIRMAN, etc.).
- **US tickers**: server returns English label names regardless of OpenD language setting, because the source data is English.

A frontend `LABEL_TRANSLATIONS` table provides a fallback that maps common English label names to their Chinese display names so the panel reads in Chinese for both languages. The translation is best-effort — unmapped labels fall through to the English name as-is.

#### Scenario: HK ticker renders in Chinese
- **WHEN** OpenD language is set to Simplified Chinese
- **THEN** `GET /api/stock/company?symbol=00700` returns `profile_labels` whose `name` fields are in Chinese (e.g. "公司全称", "上市日期")
- **THEN** the frontend panel renders each label directly as its Chinese name (the `LABEL_TRANSLATIONS` table is a no-op)

#### Scenario: US ticker renders in Chinese via translation table
- **WHEN** `GET /api/stock/company?symbol=AAPL` returns English label names (e.g. "Company Name", "Listing Date") regardless of OpenD language
- **THEN** the frontend `LABEL_TRANSLATIONS` table maps them to "公司全称", "上市日期" for display
- **THEN** the underlying `value` fields remain in English (the company description and other text are always returned in their source language)

### Requirement: HK/US company info API
The backend SHALL expose `GET /api/stock/company?symbol=<hk-or-us-symbol>` that returns a Futu-backed company profile for HK and US stocks via the new `get_company_profile` + `get_company_executives` APIs. The endpoint dispatches by market:

- Symbols matching `/^\d{6}$/` → A-share path (unchanged from `a-share-company-info` spec).
- Symbols matching `/^[A-Z]{1,5}$/` (e.g. `AAPL`, `TSLA`) or `/^US\.[A-Z]{1,5}$/` (e.g. `US.AAPL`) → US path via `FutuQuoteService.get_company_info`.
- Symbols matching `/^[0-9]{4,5}$/` (e.g. `00700`) or `/^HK\.[0-9]{4,5}$/` (e.g. `HK.00700`) → HK path via `FutuQuoteService.get_company_info`.
- All other inputs → HTTP 400 `{"error": "Unsupported symbol"}`.

The response SHALL be a JSON object with shape `{"data": <profile|empty-marker|null>, "error": <str|null>}` — wrapped in `{data, error}` for consistency with the A-share path (the original implementation returned a flat top-level object; this was fixed in §9 of tasks.md). The `data` object MUST include a `market` discriminator set to `"HK"` or `"US"` and:

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | str | Caller-provided symbol (e.g. `AAPL` or `00700`) |
| `code` | str | Futu code (e.g. `US.AAPL` or `HK.00700`) |
| `market` | str | `"HK"` or `"US"` |
| `name` | str | Company name; from the first `name` label in `profile_labels`, falls back to `""` |
| `profile_labels` | array | Raw `get_company_profile` response. Each item is `{name: str, value: str, fieldType: 0\|1\|2}`. May be `[]`. |
| `executives` | array | Raw `get_company_executives` response. Each item is `{name, displayName, position, beginDate, gender, age, education, annualSalary}`. May be `[]`. |

A-share-only fields (`chairman`, `manager`, `secretary`, `reg_capital`, `setup_date`, `province`, `city`, `introduction`, `website`, `email`, `office`, `employees`, `main_business`, `business_scope`, `com_id`, `com_name`, `ts_code`) MUST be `null` / absent for HK/US responses.

#### Scenario: US ticker returns company profile
- **WHEN** client calls `GET /api/stock/company?symbol=AAPL`
- **THEN** backend calls `FutuQuoteService.get_company_info("AAPL")`, which calls `OpenQuoteContext.get_company_profile("US.AAPL")` and `OpenQuoteContext.get_company_executives("US.AAPL")` in parallel via `concurrent.futures.ThreadPoolExecutor(max_workers=2)`
- **THEN** backend returns 200 with `data.market === "US"`, `data.code === "US.AAPL"`, `data.profile_labels` populated (typical length 18), `data.executives` populated (typical length 5+)
- **THEN** `error` is `null`

#### Scenario: HK bare-numeric ticker returns company profile
- **WHEN** client calls `GET /api/stock/company?symbol=00700`
- **THEN** backend resolves to Futu code `HK.00700` and returns 200 with `data.market === "HK"`, `data.code === "HK.00700"`, `data.profile_labels` populated with Chinese labels (公司全称, 上市日期, etc.)
- **THEN** `error` is `null`

#### Scenario: HK dotted-form ticker returns company profile
- **WHEN** client calls `GET /api/stock/company?symbol=HK.00700`
- **THEN** backend returns the same 200 response as the bare-numeric form
- **THEN** `data.code === "HK.00700"`

#### Scenario: A-share symbol still routes to A-share path
- **WHEN** client calls `GET /api/stock/company?symbol=601899`
- **THEN** backend dispatches to `AShareService.get_company_info`, NOT the Futu path
- **THEN** response shape matches the A-share spec (Tushare 17 fields, `market: "A"`, `profile_labels: []`, `executives: []`)

#### Scenario: Unsupported symbol is rejected
- **WHEN** client calls `GET /api/stock/company?symbol=BAD-CHAR!` or any string matching none of the regexes above
- **THEN** backend returns HTTP 400 with `{"error": "Unsupported symbol"}` and does not call Futu

#### Scenario: Older OpenD (Unknown protocol ID) returns clean empty
- **WHEN** Futu OpenD is older than 10.7.6708 and returns "Unknown protocol ID" on both `get_company_profile` and `get_company_executives`
- **THEN** backend returns 200 with `data: {symbol, code, market, name: "", profile_labels: [], executives: []}, error: null`
- **THEN** the frontend panel renders the "暂无公司信息" placeholder
- **THEN** no raw "Unknown protocol ID" error text leaks to the user

#### Scenario: Futu upstream error (other)
- **WHEN** Futu raises any other exception (network blip, unknown symbol, etc.)
- **THEN** backend returns 200 with `{"data": null, "error": "获取公司信息失败: <message capped at 120 chars>"}` and does not crash
- **THEN** no 5xx response is returned to the client

#### Scenario: Partial Futu response (profile OK, executives fail)
- **WHEN** `get_company_profile` succeeds but `get_company_executives` raises
- **THEN** backend returns 200 with `data.profile_labels` populated and `data.executives: []`, and `error: null`
- **THEN** the panel still renders the profile section and shows an empty-state for the executives section

### Requirement: Backend caches HK/US company info
The backend MUST cache the merged Futu company-info response (both `profile_labels` and `executives`) per symbol for at least 24 hours. Cache hits MUST NOT call Futu again.

The cache uses the `_FutuCache` class in `backend/services/futu_quote_service.py`. The cache's `get_or_fetch` MUST treat a response with `error: null` (or absent `error` key) as a successful result to be cached. (Earlier implementation only treated key-absence as success, which crashed on `error=None` — fixed in §9.2 of tasks.md.)

#### Scenario: Repeated request within TTL is served from cache
- **WHEN** `GET /api/stock/company?symbol=AAPL` is called a second time within 24 hours
- **THEN** the response is served from the in-process cache and Futu is not called

### Requirement: Frontend renders HK/US company info panel on HK and US stock pages
On the stock detail page (`/stock/{symbol}`), the page MUST render a `CompanyInfoPanel` for ALL symbols (no 6-digit guard). The panel branches on `data.market` to pick the A-share or HK/US layout. The "近期行情" data table section is removed for all markets.

The HK/US layout MUST mirror the A-share panel's structure as closely as possible:

1. **Top grid** (2-column on sm+, single-column on mobile): 公司全称, 上市日期, 员工人数, ISIN, 所在地区 (only if region is available), 公司主页 (as a link). Fields are extracted from `profile_labels` via a `pick(name1, name2, ...)` lookup keyed on label name (case-insensitive). Both Chinese keys (公司全称, 上市日期, etc.) and English keys (COMPANY NAME, LISTING DATE, etc.) are tried in order.
2. **高管信息 grid** (2-column): one row per unique translated position. Multiple executives sharing the same position are merged into one row with names joined by "、". The row uses an `ExecRow` component (position on top as small dim caption, names below as prominent value) — not the side-by-side `Cell` layout, because long English position names (e.g. "EXECUTIVE VICE PRESIDENT AND CHIEF HUMAN RESOURCES OFFICER") would otherwise squeeze the value column to character-per-line wrapping.
3. **主要业务及产品** block: from `BUSINESS` / `公司业务` / `主营业务` label, rendered as a `CollapsibleText` (3 lines clamped, expandable).
4. **公司介绍** block: from `DESCRIPTION` / `公司简介` / `公司介绍` label, rendered as a `CollapsibleText`. Skipped if the value is identical to `主要业务及产品`.
5. **Empty/error/loading states**: same 6-grey-bars skeleton and "暂无公司信息" placeholder as the A-share branch.

**Label translation**: A `LABEL_TRANSLATIONS` table (~30 entries) maps English label names to Chinese. Mapped labels display in Chinese even when the server returns English. Unmapped labels fall through to the original name.

**Hidden labels**: These label names are never displayed in any section (filtered out of both the top grid's `pick` lookups AND the extra-labels grid):
- `公司代码` / `SYMBOL` (already in the page header)
- `注册办事处` / `REGISTERED OFFICE` (Cayman registered agent address — usually noise)
- `总办事处及主要营业地点` / `HEAD OFFICE AND PRINCIPAL PLACE OF BUSINESS`
- `传真` / `FAX`

**Position translation**: A `translatePosition(pos)` function pattern-matches against the position string and returns a concise Chinese label. Recognized patterns: 董事长 (CHAIRMAN), 副董事长 (VICE CHAIRMAN), 总经理 (CEO/CHIEF EXECUTIVE/总裁), 财务总监 (CFO), 运营总监 (COO), 技术总监 (CTO), 市场总监 (CMO), 人力总监 (CHIEF HUMAN RESOURCES), 会计主管 (CHIEF ACCOUNTING), 执行副总裁 (EVP), 副总裁 (CVP), 执行董事 (EXECUTIVE DIRECTOR), 非执行董事 (NON-EXECUTIVE DIRECTOR), 独立非执行董事 (INDEPENDENT NON-EXECUTIVE DIRECTOR), 独立董事 (INDEPENDENT DIRECTOR), 董秘 (SECRETARY), 总裁 (PRESIDENT). Multi-role positions reduce to the first matching role. Fallback: the first comma-separated chunk of the original position, capped at 40 chars with "…" suffix.

#### Scenario: US stock page renders company info panel
- **WHEN** user opens `http://localhost:3000/stock/AAPL`
- **THEN** the page fetches `/api/stock/company?symbol=AAPL` and renders a `CompanyInfoPanel` with `data.market === "US"` and the Futu `profile_labels` and `executives` populated
- **THEN** the page does NOT render the "近期行情" data table
- **THEN** the panel renders: 公司全称 (苹果), 上市日期 (1980/12/12), 员工人数 (166,000), ISIN, 所在地区 (加利福尼亚州 · Cupertino), 公司主页; 高管信息 (with translated positions and merged same-position rows); 公司介绍 (苹果公司从事智能手机...)

#### Scenario: HK stock page renders company info panel
- **WHEN** user opens `http://localhost:3000/stock/00700` (or `HK.00700`)
- **THEN** the page fetches `/api/stock/company?symbol=00700` and renders a `CompanyInfoPanel` with `data.market === "HK"` and the Futu `profile_labels` (with Chinese labels) and `executives` populated
- **THEN** the page does NOT render the "近期行情" data table
- **THEN** the panel renders: 公司全称 (腾讯控股有限公司), 上市日期 (2004/06/16), 员工人数 (115,849), ISIN, 公司主页; 高管信息 (with translated positions and merged same-position rows); 主要业务及产品 (Tencent Holdings Ltd是一家主要提供...); 公司介绍 (腾讯以技术丰富互联网用户的生活...)

#### Scenario: HK/US company info load failure shows placeholder
- **WHEN** the `/api/stock/company` request fails or returns `data: null`
- **THEN** the panel renders a "暂无公司信息" placeholder
- **THEN** the rest of the page (price header, trend prediction, etc.) still renders normally

#### Scenario: HK/US company info loading state
- **WHEN** the `/api/stock/company` request is in flight
- **THEN** the panel shows a skeleton/loading state consistent with the rest of the page's vintage style

#### Scenario: HK/US executives section merges same-position entries
- **WHEN** the response `data.executives` has multiple entries with positions that translate to the same Chinese role (e.g. 4 entries all translating to "独立董事")
- **THEN** the panel renders them as a single row: position on top, names joined by "、" below
- **THEN** no duplicate rows for the same role

#### Scenario: Frontend handles link-typed profile labels
- **WHEN** a `profile_labels` item has `fieldType === 1` (LinkType) and `value` is a URL
- **THEN** the panel renders `value` as a clickable link (`<a href={value} target="_blank" rel="noopener noreferrer">`)
- **WHEN** `fieldType === 0` (SourceText) or `fieldType === 2` (IndependentTitle)
- **THEN** the panel renders `value` as plain text
