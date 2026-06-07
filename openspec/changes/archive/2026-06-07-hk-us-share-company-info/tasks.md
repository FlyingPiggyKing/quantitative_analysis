## 1. Backend dependency upgrade

- [x] 1.1 Open `backend/pyproject.toml` (or `requirements.txt` / `uv.lock` — pick the project's actual manifest) and bump `futu-api` to `>=10.7.6708`. New transitive deps (`PyCryptodome`, `python-dateutil`) should already be present in the existing lockfile; if not, add them.
- [x] 1.2 Run `uv pip install --upgrade "futu-api>=10.7.6708"` from the `backend/` directory and confirm the new SDK installs without breaking the existing `import tushare as ts` / `import futu` imports.
- [x] 1.3 Run a one-liner sanity check: `python -c "from futu import OpenQuoteContext; assert callable(OpenQuoteContext.get_company_profile); assert callable(OpenQuoteContext.get_company_executives); print('ok')"` to confirm the new methods are accessible.

## 2. Backend service method

- [x] 2.1 In `backend/services/futu_quote_service.py`, add a module-level `_company_info_cache = _FutuCache(ttl=86400)` next to the existing `_futu_cache` and a small `_FutuCache` for the company-info response.
- [x] 2.2 Add a static method `FutuQuoteService.get_company_info(symbol: str) -> dict`. Inside the method, resolve the symbol to a Futu code via the existing `_get_futu_code` helper (returns `(futu_code, market)`), then use `concurrent.futures.ThreadPoolExecutor(max_workers=2)` to call `OpenQuoteContext.get_company_profile(futu_code)` and `OpenQuoteContext.get_company_executives(futu_code)` in parallel. Merge the two DataFrames into a single response dict of shape `{"symbol", "code", "market", "profile_labels": [{name, value, fieldType}], "executives": [{name, displayName, position, beginDate, gender, age, education, annualSalary}]}`. The `name` field is derived from the first non-empty `name` value in `profile_labels` whose `fieldType` is `0` (text) — fall back to `""`. Cache the result for 24h via `_company_info_cache.get_or_fetch`. On any exception, return `{"data": None, "error": "获取公司信息失败: <msg>"}` (capped at 120 chars).
- [x] 2.3 Verify the method locally by calling it for `AAPL` (with OpenD running) and confirming `data.profile_labels` has ≥ 10 entries and `data.executives` has ≥ 3 entries. If OpenD is unavailable, the test is skipped and the test step below is deferred.
- [x] 2.4 In `backend/services/akshare_service.py`, add `USStockService.get_company_info` and `HKStockService.get_company_info` static methods that delegate to `FutuQuoteService.get_company_info`, mirroring the existing `get_moneyflow` → `get_capital_flow` pattern.

## 3. Backend API route

- [x] 3.1 In `backend/api/stock.py`, replace the 6-digit-only guard on the `/company` route with a market dispatcher: try `/^\d{6}$/.test(symbol)` first → A-share path (unchanged); else try `/^HK\.\d{4,5}$/` or `/^\d{4,5}$/` → HK path; else try `/^US\.[A-Z]{1,5}$/` or `/^[A-Z]{1,5}$/` → US path; else return HTTP 400 with `{"error": "Unsupported symbol"}`. The response shape remains `{"data": ..., "error": ...}` for all paths.
- [x] 3.2 Confirm the route still resolves before the catch-all `/{symbol}` route in the file (FastAPI uses the order of `@router.get` decorators — verify the existing ordering pattern).
- [x] 3.3 Restart the backend and hit `curl http://localhost:8000/api/stock/company?symbol=601899` → expect 200 with the A-share Tushare shape. Hit `curl http://localhost:8000/api/stock/company?symbol=AAPL` → expect 200 with the Futu `profile_labels` shape (or 400 if OpenD is not running with v10.7+). Hit `curl http://localhost:8000/api/stock/company?symbol=00700` → expect 200 with the HK shape. Hit `curl http://localhost:8000/api/stock/company?symbol=garbage!` → expect 400.

## 4. Frontend — read local Next.js docs first

- [x] 4.1 Before writing any frontend code, read `node_modules/next/dist/docs/` per `frontend/AGENTS.md` — confirm the current Next.js conventions for client components, dynamic routing params, and the panel layout API. Update the panel's signature accordingly.

## 5. Frontend — service + types

- [x] 5.1 In `frontend/src/services/companyInfo.ts`, add types `CompanyLabel { name: string; value: string; fieldType: 0 \| 1 \| 2 }` and `CompanyExecutive { name: string \| null; displayName: string \| null; position: string \| null; beginDate: string \| null; gender: string \| null; age: string \| null; education: string \| null; annualSalary: number \| null }`. Extend the `CompanyInfo` interface with `market: "A" \| "HK" \| "US"`, `profile_labels: CompanyLabel[]`, `executives: CompanyExecutive[]`. All other existing fields (`com_name`, `chairman`, `reg_capital`, etc.) become optional / nullable. The `getCompanyInfo(symbol)` helper is unchanged (calls the same `/api/stock/company?symbol=` URL).

## 6. Frontend — CompanyInfoPanel component

- [x] 6.1 In `frontend/src/components/CompanyInfoPanel.tsx`, add a top-level branch on `data.market`. If `market === "A"`, render the existing JSX verbatim (do NOT modify the existing A-share branch beyond the prop type). If `market === "HK" \|\| "US"`, render a new HK/US layout (see next steps).
- [x] 6.2 In the HK/US branch, render the panel header `❖ 公 司 信 息` (same heading as A-share) followed by a two-column grid of `profile_labels` rows. Each row: `<span className="vt-engraved ...">{label.name}</span><span className="font-[var(--font-geist-mono)] ...">{label.value || "--"}</span>`. Skip rows where `label.value` is empty. For `fieldType === 1` (LinkType), wrap `value` in an `<a href={value} target="_blank" rel="noopener noreferrer">` styled like the existing website link in the A-share branch. Reuse `vt-panel`, `vt-tab`, `vt-engraved`, `vt-parchment`, `vt-brass-300`, `vt-brass-400`, `font-[var(--font-playfair)]`, `font-[var(--font-geist-mono)]` — no new style tokens.
- [x] 6.3 Below the grid, render a `❖ 高 管 信 息` section that iterates `executives` and shows each `position` and `displayName` (fall back to `name`) as a row. Skip rows where both `position` and `displayName`/`name` are empty. Cap at the first 5 executives.
- [x] 6.4 Loading state: render the same 6-grey-bars skeleton as the A-share branch. Empty/error state: render the same `暂无公司信息` placeholder as the A-share branch.

## 7. Frontend — wire panel and remove the old table for all markets

- [x] 7.1 In `frontend/src/app/stock/[symbol]/page.tsx`, drop the `/^\d{6}$/.test(symbol)` guard around the `<CompanyInfoPanel>` render — render the panel for all symbols.
- [x] 7.2 Delete the entire trailing "近期行情" `<section>` (the quotes table) for non-A-share pages. The cleanest implementation: remove the `else` branch entirely and the surrounding `({/^\d{6}$/.test(symbol) ? <panels/> : <table/>})` ternary. The A-share branch keeps `CompanyInfoPanel` + `MainBusinessPanel`; the non-A-share branch becomes empty (the page already has the price chart at top).
- [x] 7.3 Manual test: open `http://localhost:3000/stock/601899` → A-share panel renders with 紫金矿业's Tushare data, no recent-quotes table. Open `http://localhost:3000/stock/AAPL` → HK/US panel renders with Futu profile labels and executives. Open `http://localhost:3000/stock/00700` → HK panel renders with Chinese labels and executives. The A-share `MainBusinessPanel` (main business composition) is NOT rendered for HK/US — only the company-info panel.

## 8. Verification

- [x] 8.1 Backend `curl` matrix: A-share 6-digit returns Tushare shape, US letter returns Futu shape, HK numeric returns Futu shape, garbage returns 400.
- [x] 8.2 Frontend: A-share page shows the A-share panel with Tushare fields; US page shows the Futu-field panel; HK page shows the Chinese-label panel; the trailing "近期行情" table is gone for HK/US.
- [x] 8.3 Cache: second backend call within 24h does not hit Futu (log inspection or counter).
- [x] 8.4 Failure mode: stop OpenD → US/HK pages still load with the "暂无公司信息" placeholder inside the panel. A-share page unaffected.
- [x] 8.5 No regressions on the price chart, financial indicators, trend prediction, or watchlist sections.
- [x] 8.6 Run `git diff --stat backend/services/akshare_service.py` — confirm `AShareService.get_company_info` and the A-share `_company_cache` are not touched.

## 9. Bug fix: response-shape consistency

- [x] 9.1 `FutuQuoteService.get_company_info` returns `{data, error}` (not flat top-level) so the frontend `res.data` lookup matches the A-share convention.
- [x] 9.2 `_FutuCache.get_or_fetch` treats `error=None` as a successful result (was: only treated key-absence as success, threw on `error=None`).

## 10. A-share response: add market discriminator

- [x] 10.1 `AShareService.get_company_info` (in `backend/services/akshare_service.py`) now includes `market: "A"` in the returned `data` object, and initializes `profile_labels: []` and `executives: []`. Required so the frontend's `data.market === "A"` branch dispatches correctly.

## 11. Frontend panel: mirror A-share layout for HK/US

- [x] 11.1 Rewrote `HkusPanel` to mirror the A-share panel's structure rather than the original "raw key-value grid" approach from the design. Top-tier fields (公司全称, 上市日期, 员工人数, ISIN, 所在地区, 公司主页) extracted from `profile_labels` via a `pick(name1, name2, ...)` lookup keyed on the Futu label name (case-insensitive). Supports both Chinese ("公司全称", "公司名称") and English ("COMPANY NAME", "SYMBOL") keys.
- [x] 11.2 Add a `translateLabel(name)` helper with a `LABEL_TRANSLATIONS` table (~30 entries) mapping common English label names to Chinese. US stocks' Futu response uses English label names even when OpenD is set to Chinese; this is a safety net so labels still render in Chinese on US stocks (where the server data is inherently English-sourced).
- [x] 11.3 Executives section rewritten: `translatePosition(pos)` pattern-matches against the position string to a concise Chinese label (董事长, 总经理, 独立董事, etc.). Multi-role positions like "INDEPENDENT DIRECTOR, CHAIRMAN OF THE AUDIT COMMITTEE" reduce to the first matching role. Executives sharing the same translated position are merged into one row with names joined by "、".
- [x] 11.4 `ExecRow` component: position on top (small dim caption, wraps freely), names below (prominent mono-font value, joins with "、"). Replaces the side-by-side `Cell` for executives because very long English position names (e.g. "EXECUTIVE VICE PRESIDENT AND CHIEF HUMAN RESOURCES OFFICER") would otherwise squeeze the value column to character-per-line wrapping.
- [x] 11.5 Added a `hidden` set of label names that are filtered out of the extra-labels list and never rendered in any section: `公司代码`/`SYMBOL` (already in the page header), `注册办事处`/`REGISTERED OFFICE` (Cayman-registered agent address), `总办事处及主要营业地点`/`HEAD OFFICE AND PRINCIPAL PLACE OF BUSINESS`, and `传真`/`FAX` (per user feedback).
- [x] 11.6 Removed the dedicated `办公地址` block since both its data sources (registered office + head office) are now hidden.
- [x] 11.7 Removed the dedicated `法人代表`/`总经理`/`董秘` row; the chairman info now lives only in the 高管信息 grid (as "董事长: <name>"), avoiding duplication.

## 12. Older-OpenD failure mode

- [x] 12.1 `FutuQuoteService.get_company_info` catches "Unknown protocol ID" / "Unknown proto" / "protocol id" exceptions from Futu and returns a clean empty response (`{data: {profile_labels: [], executives: [], name: ""}, error: null}`) instead of leaking the raw error. Frontend's `HkusPanel` then renders the "暂无公司信息" placeholder. Aligns with the design's "failure modes" section.

## 13. OpenD language setting (operational)

- [x] 13.1 Documented the OpenD language requirement in CLAUDE.md / README. Set OpenD GUI's "Language" preference to "Simplified Chinese" via the GUI Settings panel (not via editing `~/.com.futunn.FutuOpenD/UI/OpenD.xml` — the GUI overwrites the XML on restart). After this, the Futu server returns Chinese label names for HK tickers; US tickers still return English (server source data is English) — handled by the `LABEL_TRANSLATIONS` table.
