## Context

- The `company-info` change (sibling openspec change) introduced `CompanyInfoPanel` rendering Tushare `stock_company` (doc_id=112) data — a static text profile. This change layers a separate, structural view on top using Tushare `fina_mainbz` (doc_id=81).
- Tushare `fina_mainbz` returns structured revenue / profit / cost rows keyed by `(ts_code, end_date, bz_item, bz_code)`, where `bz_code` is `P` (product), `D` (region), or `I` (industry). The response includes duplicates in some cases (e.g. 茅台 系列酒 / 其他酒系列 rows are byte-identical) and `bz_cost` is often `NaN` for region/industry dimensions.
- The project's `TUSHARE_TOKEN` is configured in `backend/.env` with sufficient points (the user's tier has been observed to allow this interface in real calls; the doc claims 2000 points are required).
- Existing pattern (per `company-info` change): module-level `_YFCache` keyed by symbol, `useState`+`useEffect` in the page (no `useSWR`), vintage Tailwind classes (`vt-panel`, `vt-tab`, etc.).
- Frontend stack: Next.js app router, Tailwind, project-local component conventions captured in `AGENTS.md` ("This is NOT the Next.js you know").
- No database is used for this data; everything is Tushare → in-memory cache → response.

## Goals / Non-Goals

**Goals:**
- Add a new `AShareService.get_main_business_composition(ts_code, period?, type?)` and a sibling `get_main_business_history(ts_code, type, top)` method in `backend/services/akshare_service.py`.
- Add `GET /api/stock/main-business` (single period) and `GET /api/stock/main-business/history` (cross-period) routes in `backend/api/stock.py`.
- Add a `<MainBusinessPanel />` React component that renders below `<CompanyInfoPanel />` on A-share pages, with sections: by-product, by-region (with overseas badge), by-industry (only when distinct from P), cross-period (top-3 product lines × last 4 annual periods).
- Use 24h in-memory cache keyed by `(ts_code, type, period)` to stay well under the Tushare 2000-point tier.
- Graceful empty / loading / error states consistent with `CompanyInfoPanel`.

**Non-Goals:**
- No new Tushare endpoints beyond `fina_mainbz` (no `fina_mainbz_vip` — that one needs 5000 points and is not necessary; one stock × 3 types × ~10 periods is comfortably under 100 calls per warm cache).
- No DB persistence. No Redis. No new env vars.
- No changes to US/HK stock pages.
- No changes to the existing `CompanyInfoPanel` component or its data source.
- No i18n / locale switching — the panel is Chinese-only, matching the rest of the page.

## Decisions

### 1. Two endpoints, not one fat endpoint
`GET /api/stock/main-business` (single period, one type) and `GET /api/stock/main-business/history` (4 periods, top-N items). Frontend fires up to 4 calls on mount: P latest, D latest, I latest, P history. Rationale: each call has a different cache key, different shape, and different render path. Merging them would force the response to embed both shapes and complicate the React component. The Tushare-cache and 24h TTL make the extra calls effectively free after the first visit. Alternatives considered: a single `/api/stock/main-business?expand=1` (rejected — over-fetching for the common case of "show me this one period"), and an SSE/WebSocket push (rejected — no real-time need).

### 2. Backend normalizes, frontend displays
The backend computes `revenue_share_pct`, `profit_share_pct`, `gross_margin_pct`, deduplicates, and sorts by `bz_sales` desc. The frontend receives ready-to-render rows. Rationale: keeps the React component free of arithmetic; the same normalization runs once per cache fill. CLAUDE.md says the frontend is the single source of truth for **currency unit conversion** (元 → 亿元), so the backend returns raw 元 and the frontend divides by 1e8 — consistent with the `company-info` change.

### 3. Reuse `_YFCache` with custom TTL, separate instance
Per `company-info` precedent: a module-level `_main_biz_cache = _YFCache(ttl=86400)` next to the existing `_yf_cache` and `_company_cache`. Key is `(ts_code, type, period)` for the single endpoint, `(ts_code, type, "history", n_periods)` for history. Alternatives considered: a generic `TushareCache` class (rejected — over-abstraction; we have one new Tushare method to cache). Per the existing pattern, errors do NOT cache — the cache only stores successful normalized responses.

### 4. By-industry section hidden by default
Many vertically-integrated companies (e.g. 比亚迪) report industry rows identical to product rows. The spec says hide the section when there's no new information. Implementation: backend returns both `rows_P` and `rows_I` and a small `has_distinct_industry: bool` flag in the P response. Frontend renders I only if `has_distinct_industry === true`. Alternative considered: always render I (rejected — clutters the page for the common no-new-info case).

### 5. Top-3 by latest-period revenue, "其他" bucket
For the cross-period chart, picking top-3 by latest-period revenue matches what users care about (the biggest lines today). The "其他" bucket keeps the total coherent and avoids clipping. The `top` query param is fixed at 3 in the spec but exposed for future flexibility (e.g. expand to top-5 in a later change).

### 6. Cross-period pulls 4 annual periods explicitly
Use `end_date` filter on `fina_mainbz`: `end_date ∈ {20211231, 20221231, 20231231, 20241231}`. The latest annual period is computed from `datetime.now()` (current month > 4 → last full year, else year-1) — same logic used elsewhere in the project for the latest report period. The call returns a list; backend merges them into `series[]` with `values[]` per period. Alternative considered: looping single-period calls (rejected — N×3 cache lookups vs. 1). We use a single Tushare call with `end_date` filter to reduce round-trip cost.

### 7. "海外" badge via simple string match
Regex `/国外|海外|境外|出口|overseas/i` against `bz_item`. Most A-share companies use 国内/国外 or 中国大陆/国外. Some use 境内/境外. The catch-all keeps the badge logic one line in the React component. False positives (e.g. "出口退税" as an item) are tolerable — at worst a mislabeled badge on a small row.

### 8. No new dependencies
Pure backend Python (uses existing `tushare` + `pandas` already in `pyproject.toml`). Pure React + existing Tailwind classes for the frontend. No new chart library — the spec calls for "stacked bar" and "column chart" but doesn't mandate a library; a hand-rolled CSS bar with `width: <pct>%` is sufficient and matches the vintage aesthetic (no flashy chart.js / recharts).

## Risks / Trade-offs

- [Tushare returns NaN for bz_cost in region/industry rows] → Spec mandates `null` gross margin in that case; frontend shows `—`. No silent "0%" — that would be misleading.
- [Duplicate rows for some companies] → Backend dedups by full tuple. Trade-off: if a company intentionally reports two truly-different lines that happen to have the same numbers (rare), the second is dropped. Acceptable risk.
- [First-visit latency for 4 simultaneous fetches] → All 4 calls hit the cache after the first visit; the first visit can take 1–2s for cold cache (4 sequential Tushare calls). Mitigation: render sections independently with their own loading skeletons so the page doesn't appear frozen; the by-product table is the critical path and renders first.
- [Tushare rate limit on burst cache warm] → 4 calls per (ts_code, type) on first visit is fine; the user's tier comfortably handles this. If we ever pre-warm across many symbols, the existing 24h TTL won't help. Mitigation: no pre-warming in this change.
- [Cross-period with non-existent period] → If a company IPO'd in 2022, the 2021 period returns empty. The spec mandates `null` yoy for the first non-null period and `—` rendering. No crash, no all-zero bar.
- [Data freshness] → Tushare updates `fina_mainbz` after each quarterly report is published. Annual reports usually appear April–May for Dec-31 periods. A user visiting in March will see 2023 data, not 2024. Acceptable — match the behavior of the existing `stock_company` panel.
- [AGENTS.md "This is NOT the Next.js you know"] → any new component must be written against the local `node_modules/next/dist/docs/`. Tasks step explicitly says to consult those docs before writing the new `MainBusinessPanel.tsx`.
- [No `update_flag` in real response] → Spec explicitly does NOT promise this field. Documented in the proposal as a caveat.

## Migration Plan

- **Backend**: deploy with two new endpoints added; no DB migration. Old endpoints unchanged. Reuses existing `TUSHARE_TOKEN` (same permission tier as `stock_company`).
- **Frontend**: deploy with one new component + one insertion point in `page.tsx`. Revert is a single-file change: remove the `<MainBusinessPanel />` line and the import.
- **No feature flag needed** — the change is purely additive (a new panel below an existing one) and reversible in one line.
- **Cache invalidation**: the in-memory cache dies with the process; on next deploy all entries are fresh. No external cache to flush.

## Open Questions

- Should the by-product bar chart use color coding to distinguish product lines (each row its own color) or a single vintage accent color? Default: each row gets a distinct muted color from the existing Tailwind palette. Confirm during implementation.
- Should the by-product section also show a "YoY vs prior period" column (single most recent YoY, not the full 4-year chart)? Default: skip it; the 跨期对比 section already shows YoY for top-3. If users want YoY for all products, add in a follow-up.
- Should the 跨期对比 chart use bars or lines? Default: bars (column chart), since the spec calls it a "column chart" of revenue. Lines imply continuous change and can mislead across discrete annual reports.
- Should the panel auto-refresh after quarterly report publication? Default: no — 24h TTL means a user revisiting the page within a day sees cached data, which is fine. A "force refresh" button is out of scope.
