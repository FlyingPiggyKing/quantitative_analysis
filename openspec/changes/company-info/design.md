## Context

- The stock detail page at `frontend/src/app/stock/[symbol]/page.tsx` ends with a "近期行情" data table (line 640-676) that consumes the last 10 K-line rows already loaded for the price chart.
- For A-share symbols the page already filters financial-indicators rendering by `/^\d{6}$/.test(symbol)` (line 629), so the A-share detection point is well established.
- Tushare's `stock_company` endpoint (doc_id=112) returns 17 company-profile fields per `ts_code` and requires ≥ 120 points. The project's `TUSHARE_TOKEN` is already configured; `AShareService` already wraps Tushare calls in `backend/services/akshare_service.py`.
- Existing caching pattern: module-level `_yf_cache = _YFCache(ttl=300)` with `get_or_fetch` / `on_error_return_stale` helpers. Company info changes rarely (registration changes, name changes), so a long TTL is appropriate.
- Frontend uses `useState` + `useEffect` (not `useSWR`) for the existing data fetches in this page; the new fetch should follow the same pattern for consistency.

## Goals / Non-Goals

**Goals:**
- Add a new `GET /api/stock/company?symbol=` endpoint backed by Tushare `stock_company` (A-share only).
- Add a `CompanyInfoPanel` component that displays the company profile in the existing vintage style.
- On `/stock/{6-digit}` pages, swap the "近期行情" data-table section for the `CompanyInfoPanel`. US/HK pages keep the existing table.
- Cache company info for 24h to stay well under the 120-point Tushare tier.
- Graceful empty/loading/error states — the page must not break if the upstream call fails.

**Non-Goals:**
- No changes to US/HK stock pages.
- No new Tushare endpoints beyond `stock_company`.
- No edits to the price-chart or financial-indicators sections.
- No batch endpoint in this change (the existing `/api/stock/batch/info` is unaffected; a future change can add a company-info batch variant if needed).
- No new env vars or auth changes (reuses `TUSHARE_TOKEN`).

## Decisions

### 1. Reuse `_YFCache` with 24h TTL instead of a separate cache class
`_YFCache` already supports custom TTL per instance. A separate module-level `_company_cache = _YFCache(ttl=86400)` next to the existing `_yf_cache` is enough — no need for a new abstraction. Alternatives considered: Redis (rejected — the project runs single-process and the data is already in memory elsewhere) and DB-backed cache (rejected — overkill for static reference data).

### 2. Symbol → ts_code conversion via existing `_symbol_to_ts_code` helper
The helper at `backend/services/akshare_service.py:182` already maps `601899` → `601899.SH` correctly. Reuse it; do not duplicate the logic.

### 3. Single-row response shape: `{data: {...} | null, error: str | null}`
Matches the shape already used by `fundamentals` and other endpoints in the page (line 632: `fundamentals?.data ?? null`, `fundamentals?.error ?? null`). Consistency with existing call sites > inventing a new envelope.

### 4. Frontend fetch in the existing `useEffect` chain, not a new `useSWR`
The page already uses raw `useState`/`useEffect` for `stockInfo`, `klineData`, etc. Adding `useSWR` for one fetch would introduce a second mental model. Stay consistent: add `companyInfo` / `companyInfoLoading` / `companyInfoError` state and trigger the fetch inside the same `useEffect` that loads `stockInfo`. Alternative considered: colocate the fetch inside `CompanyInfoPanel` (cleaner separation but inconsistent with how the rest of the page handles its data).

### 5. Replace — not augment — the "近期行情" section for A-shares
The user explicitly asked to "replace" 底部的近期行情 with 公司基本信息. For A-shares the K-line tail is already shown in the price chart and the recent-quotes table becomes redundant. A clean swap avoids two similar-looking tables stacked. The kline data is still loaded (the price chart needs it) so there is no data loss.

### 6. Render company fields in a two-column grid with `vt-*` styles
Fields are naturally key/value. A CSS grid `grid-cols-1 sm:grid-cols-2` keeps it readable on mobile and dense on desktop. Reuse the existing `vt-panel`, `vt-tab`, `vt-engraved`, `vt-parchment` classes — no new style tokens.

### 7. Long-text fields truncated with `line-clamp-3` and expandable
`introduction`, `main_business`, `business_scope` can be hundreds of characters. `line-clamp-N` plus a "展开/收起" toggle keeps the page compact without losing information. Use a small `[+]`/`[−]` button styled like the rest of the UI.

### 8. Reject non-6-digit symbols at the API layer
Even though the frontend only calls this for A-share pages, the API must validate. Returns HTTP 400 with a Chinese error message consistent with the rest of the API (`{"error": "..."}`).

## Risks / Trade-offs

- [Tushare rate limit on cold cache] → 24h TTL means first call per symbol costs 1 point; subsequent calls are free. Worst case: 4500 symbols × 1 call = 4500 points just to warm the cache, which exceeds the 120-point tier's per-minute limit. Mitigation: warm the cache lazily per symbol (only when a user visits that stock page), not all at once.
- [Tushare returns null for a delisted/suspended symbol] → panel shows "暂无公司信息" placeholder, page otherwise unaffected.
- [Frontend swap removes the visible 10-row quotes table on A-share pages] → users who relied on the table at the bottom lose that view. Mitigation: the price chart at the top already shows the recent candles; if feedback shows the table was useful, we can add it back in a future change.
- [AGENTS.md warns "This is NOT the Next.js you know"] → any new component must be written against the local `node_modules/next/dist/docs/`. Mitigation: tasks step explicitly says to consult those docs before writing the new `CompanyInfoPanel.tsx`.
- [reg_capital unit confusion: Tushare returns 万元, CLAUDE.md says divide by 10000 for 亿元] → conversion happens in the frontend (single source of truth per project convention); backend returns the raw value and a `reg_capital_unit: "万元"` field for clarity.

## Migration Plan

- Backend: deploy with the new endpoint added; no DB migration (no schema change). Old endpoints unchanged.
- Frontend: deploy with the panel swap; revert is a single-file change to `page.tsx` (restore the old `<section>`) if the new panel causes user-reported issues.
- No feature flag needed — the change is small and reversible.

## Open Questions

- Should the `CompanyInfoPanel` also show the company's `industry` / `area` (which already come from the existing `stock_info` fetch)? If yes, the panel would be partially redundant with the price header. Default: keep the new panel independent and only use `stock_company` fields. Confirm during implementation if it feels sparse.
- Should the panel show `introduction` at all, or is it too marketing-heavy? Default: show it truncated with expand/collapse.
