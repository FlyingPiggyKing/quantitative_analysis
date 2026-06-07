## 1. Backend service

- [x] 1.1 Add `_company_cache = _YFCache(ttl=86400)` module-level instance in `backend/services/akshare_service.py` next to `_yf_cache`
- [x] 1.2 Add `AShareService.get_company_info(symbol: str) -> dict` static method. Convert symbol via `_symbol_to_ts_code`, call `ts.pro_api().stock_company(ts_code=ts_code)`, wrap in `_company_cache.get_or_fetch(key, fetch)`, return shape `{"data": <row or null>, "error": <str or null>}` (reuse `safe_float` / null-on-empty pattern from `get_daily_basic`)
- [x] 1.3 Verify the method locally by calling it for `601899` (or another known A-share) and confirming the 17 fields are present

## 2. Backend API route

- [x] 2.1 Add `GET /api/stock/company` route in `backend/api/stock.py`. Validate `symbol` is 6 digits → 400 `{"error": "A-share symbol required (6-digit numeric)"}`; otherwise delegate to `AShareService.get_company_info` and return its dict with HTTP 200
- [x] 2.2 Confirm the route resolves before the catch-all `/{symbol}` route (check existing ordering pattern in the file)
- [x] 2.3 Restart backend, hit `curl http://localhost:8000/api/stock/company?symbol=601899` and confirm a 200 with the 17 fields
- [x] 2.4 Hit `curl http://localhost:8000/api/stock/company?symbol=AAPL` and confirm a 400

## 3. Frontend — read local Next.js docs first

- [x] 3.1 Before writing any frontend code, read `node_modules/next/dist/docs/` (or the relevant guide for this project) per the AGENTS.md warning — confirm the current Next.js conventions for client components, routing params, and styling in this repo

## 4. Frontend — service + state

- [x] 4.1 Add `getCompanyInfo(symbol: string)` helper to `frontend/src/services/stock.ts` (or a new `frontend/src/services/companyInfo.ts` if it doesn't fit the existing module) that calls `GET /api/stock/company?symbol=` and returns `{data, error}` typed
- [x] 4.2 In `frontend/src/app/stock/[symbol]/page.tsx`, add `CompanyInfo` / `companyInfoLoading` / `companyInfoError` state and a `useEffect` branch (triggered when `symbol` matches `/^\d{6}$/`) that calls the new helper and stores the result

## 5. Frontend — CompanyInfoPanel component

- [x] 5.1 Create `frontend/src/components/CompanyInfoPanel.tsx` ("use client"). Props: `data: CompanyInfo | null`, `loading: boolean`, `error: string | null`. Render a `<section className="vt-panel p-3 sm:p-4">` with the heading `❖ 公 司 信 息` (matching the existing `❖ 近 期 行 情` style)
- [x] 5.2 Inside the panel, render a two-column grid (mobile single-column) of label/value rows. Map: 公司全称 (com_name), 股票代码 (ts_code), 统一社会信用代码 (com_id), 法人代表 (chairman), 总经理 (manager), 董秘 (secretary), 注册资本 (reg_capital / 10000 → "亿元" with 2 decimals), 注册日期 (setup_date), 所在地区 (province + city), 员工人数 (employees with `toLocaleString()`), 公司主页 (website rendered as `<a>`), 邮箱 (email rendered as `mailto:`), 办公地址 (office)
- [x] 5.3 Render `main_business`, `business_scope`, and `introduction` as full-width rows with `line-clamp-3` and a `展开/收起` toggle button (local `useState` for the expanded flag)
- [x] 5.4 Loading state: show a skeleton block (e.g. 6 grey bars) matching the panel's footprint. Error / null state: render the panel header + a `暂无公司信息` placeholder paragraph (do NOT hide the panel entirely, per spec)
- [x] 5.5 Confirm no new style tokens — only reuse `vt-panel`, `vt-tab`, `vt-engraved`, `vt-parchment`, `vt-brass-400`, `vt-oxblood-400`, `vt-emerald-400`, `font-[var(--font-playfair)]`, `font-[var(--font-geist-mono)]`

## 6. Frontend — wire panel and remove the old table for A-shares

- [x] 6.1 Import `CompanyInfoPanel` in `frontend/src/app/stock/[symbol]/page.tsx`
- [x] 6.2 Replace the "近期行情" `<section>` (lines 640-676) with a new conditional: when `/^\d{6}$/.test(symbol)` render `<CompanyInfoPanel data={...} loading={...} error={...} />`; otherwise keep the existing table. Verify the surrounding financial-indicators section (line 628-637) already uses the same `/^\d{6}$/` guard for reference
- [x] 6.3 Manual test: open `http://localhost:3000/stock/601899` in the browser — company info panel renders with 紫金矿业's data, no "近期行情" table
- [x] 6.4 Manual test: open `http://localhost:3000/stock/AAPL` (or any non-A-share) — the "近期行情" table renders as before, no company panel

## 7. Verification

- [ ] 7.1 Backend: `curl` the new endpoint for `601899` returns the 17 fields; for `AAPL` returns 400; for an unknown code returns `{data: null, error: "未找到该公司信息"}`
- [ ] 7.2 Frontend: A-share page shows the panel, US/HK pages show the old table
- [ ] 7.3 Cache: second backend call within 24h does not hit Tushare (log inspection or counter)
- [ ] 7.4 Failure mode: temporarily set `TUSHARE_TOKEN` to invalid → page still loads, panel shows "暂无公司信息"
- [ ] 7.5 No regressions on the price chart, financial indicators, trend prediction, or watchlist sections
