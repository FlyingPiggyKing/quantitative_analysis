## Context

- The 2026-06-02-company-info change added `AShareService.get_company_info`, `GET /api/stock/company?symbol=`, and a frontend `CompanyInfoPanel` (Tushare 17-field schema) — wired to the A-share page only via the guard `/^\d{6}$/.test(symbol)`.
- For HK/US pages the same guard skips the panel, so the redundant "近期行情" 10-row quotes table still renders at the bottom of every HK/US stock page.
- The currently installed `futu-api` is 10.5.6508. It does NOT expose a `get_company_profile` method (verified via `dir(OpenQuoteContext)` and `find` on the SDK source). PyPI shows `futu-api 10.7.6708` as the latest; we installed it in an isolated venv (`/tmp/futu-probe/venv`) and confirmed three new APIs:
  - `OpenQuoteContext.get_company_profile(code)` — returns a `pd.DataFrame` of `{name, value, field_type}` rows (proto `Qot_GetCompanyProfile`, ProtoID 3243). The list is a free-form key-value bag whose actual labels come from the Futu server; we observed the protobuf defines `CompanyLabItem { name, value, fieldType }` with `fieldType ∈ {SourceText, LinkType, IndependentTitle}`.
  - `OpenQuoteContext.get_company_executives(code)` — returns a `pd.DataFrame` of director rows with columns: `display_leader_name`, `leader_name`, `position_name`, `begin_date_str`, `leader_gender`, `leader_age`, `highest_education`, `annual_salary`, `issue_date_str` (proto `Qot_GetCompanyExecutives`).
  - `OpenQuoteContext.get_company_operational_efficiency(code, num, ...)` — not used in this change; future capability.
- Typical Futu server response for a HK ticker (e.g. `HK.00700`) returns ~20 labels including (Chinese): 公司全称, 英文名称, 注册地址, 法定代表人, 总经理, 董秘, 公司电话, 公司传真, 公司邮箱, 公司网址, 主营业务, 经营范围, 公司简介, 上市日期, 发行价, etc. Labels for US tickers may be in English.
- Existing pattern: `USStockService` / `HKStockService` in `backend/services/akshare_service.py` are thin delegators to `FutuQuoteService` (see `get_moneyflow` → `get_capital_flow`). Mirror that pattern.
- The frontend's stock detail page (`frontend/src/app/stock/[symbol]/page.tsx`) already has a `companyInfo` / `companyInfoLoading` / `companyInfoError` state guarded by `/^\d{6}$/`; the guard is the only thing that has to change. The `CompanyInfo` TypeScript type and the panel component live in their own files (`frontend/src/services/companyInfo.ts`, `frontend/src/components/CompanyInfoPanel.tsx`).
- Per `frontend/AGENTS.md`: "This is NOT the Next.js you know — read `node_modules/next/dist/docs/` before writing any code." The implementer must do this for the panel layout changes.

## Goals / Non-Goals

**Goals:**
- Upgrade `futu-api` to `>=10.7.6708` in the backend manifest.
- Add a backend method `FutuQuoteService.get_company_info(symbol)` that calls `get_company_profile(code)` and `get_company_executives(code)` (in parallel, since they're independent), merges the responses, and normalizes into the existing `CompanyInfo` shape (extended with `profile_labels`, `executives`, and a `market` tag).
- Extend `GET /api/stock/company?symbol=` to dispatch by market. Keep the 6-digit A-share path unchanged; add HK (4-5 digit or `HK.xxxxx`) and US (1-5 letters or `US.XXXXX`) paths. Reject anything else with HTTP 400.
- Add a sibling `CompanyInfo` schema for HK/US fields. The `CompanyInfoPanel` component picks layout by `data.market`.
- Drop the `/^\d{6}$/` guard on the panel render — render for all symbols. Replace the trailing "近期行情" quotes table for HK/US too.
- Cache Futu company info for 24h (re-use the existing `_FutuCache` pattern with TTL=86400). Futu's profile response is static reference data; the 24h TTL makes the second-call case free and is graceful under OpenD disconnects.
- Preserve the A-share implementation exactly: no changes to `AShareService.get_company_info`, `_company_cache` (A-share 24h cache), the A-share 6-digit guard, or the A-share panel rendering path.

**Non-Goals:**
- No new Tushare / Futu calls beyond `get_company_profile` + `get_company_executives` (no `get_company_operational_efficiency` or `get_executive_background` in this change).
- No new env vars, no auth changes, no DB migration.
- No batch company-info endpoint.
- No changes to the existing A-share panel layout, types, or service method body.
- No realtime updates — company info is static and 24h cache is fine.
- No Futu OpenD binary version enforcement in the backend (the project already requires an OpenD for any HK/US data; the user's existing OpenD must be ≥ 10.7.6708 to use the new APIs).

## Decisions

### 1. Use `get_company_profile` + `get_company_executives` as the data source (not just `get_market_snapshot`)
`get_market_snapshot` has live prices, market cap, PE/PB; `get_company_profile` has the static identity/management data (chairman, address, business scope, website, etc.) that the A-share panel shows. They are different concerns. For the company-info panel, `get_company_profile` is the correct primary source; `get_company_executives` supplements it with structured director data (name, position, age, education, salary).

Alternatives considered:
- Snapshot only: would lose chairman/CEO/address — the most "company identity" fields. Defeats the purpose.
- `get_stock_basicinfo` only: would lose everything except name/listing date — basically nothing.

### 2. Run the two Futu calls in parallel (concurrent.futures)
Both `get_company_profile` and `get_company_executives` are independent (no shared parameters, no shared output). Two sequential calls double the wall-clock latency for what should be ~2 RPCs. Use a 2-thread `concurrent.futures.ThreadPoolExecutor` inside `FutuQuoteService.get_company_info` and merge the results. The Futu Python SDK is thread-safe (the same `OpenQuoteContext` is used across `get_snapshot` / `get_kline_data` in the existing code).

### 3. Pass the raw `profile_labels` list to the frontend; render as a generic key-value panel
The Futu `get_company_profile` response is a free-form list whose actual labels depend on the market and the Futu server build. Hard-coding a label-to-field mapping on the backend (e.g. "公司全称" → `com_name`) is fragile: a label rename on Futu's side silently breaks the field. Instead, pass the raw list to the frontend and let the panel iterate over it.

For the **subset of fields where parity with the A-share panel matters** (chairman, secretary, address, website, business scope, introduction), the frontend uses a small lookup table that matches by label name. Labels that aren't matched are still rendered in a "其他公司信息" (or "Additional Information") subsection. This keeps the panel robust to Futu label changes and the panel rich when Futu adds new labels.

Alternatives considered:
- Backend normalization only (drop unknown labels): rigid, breaks on label renames, loses data.
- Frontend-only with no A-share parity: gives the user less structure, harder to scan.

### 4. Single cache key per symbol covers both calls
The 24h cache key is `f"company_info:{symbol}"`. Cache hit returns the merged dict from cache; cache miss runs both calls in parallel and stores the merged dict. No partial caching — a cached entry means both fields are present (or both are `null` on Futu failure).

### 5. Route-level market dispatcher
`GET /api/stock/company?symbol=` is the single endpoint. Frontend service `getCompanyInfo` calls it for all markets. The dispatcher logic lives in `backend/api/stock.py`'s `get_company_info` handler.

### 6. Extend the existing `CompanyInfo` interface with optional Futu fields
`profile_labels: CompanyLabel[]` and `executives: CompanyExecutive[]` are added to the interface. Both default to `[]` (empty) for A-share responses. The A-share service method does not need to populate them. Single type keeps the service `getCompanyInfo` returning a uniform shape. The panel component branches on `data.market` to choose the layout.

### 7. Branch the `CompanyInfoPanel` render on `data.market`
The existing A-share layout stays intact inside a `data.market === "A"` branch (copy the JSX verbatim). A new `data.market === "HK" || "US"` branch renders the Futu field set: a section heading `❖ 公 司 信 息`, then two-column grid of `profile_labels`, then an `❖ 高 管 信 息` section listing executives, then a `公司简介` block derived from the matching profile label.

### 8. Drop the `/^\d{6}$/.test(symbol)` guard in `page.tsx`
Currently the panel is only fetched and rendered when the symbol is 6 digits. Removing the guard means the panel renders for HK and US too, and the trailing "近期行情" quotes table is removed for those markets.

### 9. New `HKStockService.get_company_info` and `USStockService.get_company_info` delegators
Mirror the existing `get_moneyflow` → `get_capital_flow` pattern in `akshare_service.py`. The wrappers are there for consistency with the existing architecture (potential future callers like batch endpoints). ~5 LoC each.

### 10. A-share implementation stays bit-for-bit unchanged
Verified by reading `backend/services/akshare_service.py:430-510` and the existing `CompanyInfoPanel.tsx`. The A-share branch in the panel is the *first* branch in the new conditional, with the existing JSX copied verbatim. Any regression shows up immediately when opening `http://localhost:3000/stock/601899`.

## Risks / Trade-offs

- [Futu OpenD binary version mismatch] → If the user's OpenD is older than 10.7.6708, the new APIs return errors (`retType != RET_OK`). The 24h cache + the existing `_futu_cache.on_error_return_stale` 5-min snapshot cache means a transient error doesn't break the page; a persistent error (older OpenD) shows "暂无公司信息" everywhere. Mitigation: document the OpenD version requirement in `backend/.env.example` or in CLAUDE.md; not block the change on a hard version check.
- [Futu labels change without notice] → The frontend's label-to-field lookup table is best-effort. If a label is renamed, the affected row is missing from the panel but the page still loads. The "其他公司信息" subsection still surfaces unmatched labels.
- [Futu response is sometimes empty for less-covered US tickers] → `data.profile_labels` is `[]`; panel renders the heading and the "暂无公司信息" placeholder. Same UX as A-share empty case.
- [Hitting two Futu endpoints per company info call] → With the 24h outer cache, first call is 2 Futu calls; subsequent calls within 24h are 0. Both endpoints are local OpenD (low latency, no rate limits). No risk in practice.
- [Frontend layout refactor may break the existing A-share panel] → Mitigation: the A-share branch is the *first* branch in the new conditional, with the existing JSX copied verbatim. Any regression shows up immediately when opening `http://localhost:3000/stock/601899`.
- [AGENTS.md says "This is NOT the Next.js you know"] → The implementer MUST read `node_modules/next/dist/docs/` before changing the component or page. Tasks step 4.1 makes this explicit.
- [Two parallel Futu calls share one `OpenQuoteContext`] → Verified safe by reading `futu_quote_service.py:175-187` — the same `_quote_ctx` is used by `get_snapshot`, `get_kline_data`, etc. The Futu SDK is designed for concurrent queries on a single context.

## Migration Plan

- Backend: deploy with the upgraded `futu-api` and the new endpoint behavior; no DB migration, no schema change. Old A-share behavior bit-for-bit unchanged.
- Frontend: deploy with the new panel layout. If HK/US panel looks wrong, revert is a single-file change to `page.tsx` (restore the `/^\d{6}$/.test(symbol)` guard).
- OpenD upgrade is OUT of scope for this change — the user already runs OpenD; they upgrade their OpenD binary on their own schedule. If the upgrade is required to test, document in the PR.

## Open Questions

- Should the HK/US panel also display the company name in Chinese where Futu provides one? Confirmed: `get_company_profile` returns labels that include 公司全称 / 英文名称 for HK tickers. The English-or-Chinese decision is a frontend rendering concern (just display `label.value` as-is — Futu already picks the right language per market). No extra work.
- Should the "高管信息" executives section be paginated/limited? Default: show top 5 (chairman + top 4 by `positionName` order received from Futu). Confirm during implementation if it feels too dense.
- Should the `get_company_executives` call be skipped for some markets? Default: call it for both HK and US. The `positionName` strings differ slightly per market (US uses "Chief Executive Officer", HK uses "董事长") — the frontend label-normalization handles both.
- `annual_salary` is `uint64` (cents/分? raw number?). For HK, listed company disclosures publish HKD. For US, USD. Confirm the unit during implementation; the frontend just displays the number with a currency suffix.
