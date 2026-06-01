"use client";

import {
  MainBusinessResponse,
  MainBusinessHistoryResponse,
  MainBusinessHistorySeries,
  MainBusinessHistoryValue,
} from "@/services/mainBusiness";

interface MainBusinessPanelProps {
  product: MainBusinessResponse | null;
  region: MainBusinessResponse | null;
  industry: MainBusinessResponse | null;
  history: MainBusinessHistoryResponse | null;
  loading: { p: boolean; d: boolean; i: boolean; h: boolean };
  error: string | null;
  hasDistinctIndustry: boolean;
}

const NA = "—";

// Vintage brass palette (Tailwind classes) — one per row in stacked bar.
// All warm tones so the bar reads as a continuous gradient against the dark page bg;
// previously mixed in `vt-ink-500/600` which blended into the background and looked like holes.
const PALETTE = [
  "bg-vt-brass-400",  // largest segment — highlight brass
  "bg-vt-brass-500",  // primary brass
  "bg-vt-brass-600",  // deep brass
  "bg-vt-brass-300",  // bright gold leaf — for visual rhythm
  "bg-vt-brass-700",  // antique brass shadow — darkest, for smallest segments
];

// 海外 / overseas regex (per design §7).
const OVERSEAS_RE = /国外|海外|境外|出口|overseas/i;

function formatYiYuan(val: number | null): string {
  if (val == null) return NA;
  return `${(val / 1e8).toFixed(2)} 亿`;
}

function formatPct(val: number | null, withSign = false): string {
  if (val == null) return NA;
  const rounded = val.toFixed(2);
  if (!withSign) return `${rounded}%`;
  return val >= 0 ? `+${rounded}%` : `${rounded}%`;
}

function pctColorClass(val: number | null, onPositive = "text-emerald-400", onNegative = "text-rose-400"): string {
  if (val == null) return "text-vt-parchment-dim";
  return val >= 0 ? onPositive : onNegative;
}

function isOverseas(item: string): boolean {
  return OVERSEAS_RE.test(item);
}

function SectionHeader({ children, caption }: { children: React.ReactNode; caption?: string }) {
  return (
    <div className="mt-5 mb-2 flex items-baseline justify-between gap-3">
      <h3 className="font-[var(--font-playfair)] text-base tracking-[0.16em] text-vt-parchment uppercase">
        {children}
      </h3>
      {caption && (
        <span className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim">
          {caption}
        </span>
      )}
    </div>
  );
}

function Skeleton({ rows = 4, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="animate-pulse space-y-1.5">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-3 bg-vt-ink-700/60 rounded" />
          ))}
        </div>
      ))}
    </div>
  );
}

function StackedBar({ rows }: { rows: { item: string; revenue_share_pct: number; is_adjustment?: boolean }[] }) {
  if (rows.length === 0) return null;
  // Exclude adjustment rows (inter-segment elimination) from the bar — they have negative
  // share and would either collapse to 0px (invalid CSS) or overflow the container.
  // We renormalize the remaining widths so the bar always sums to 100%.
  const positive = rows.filter((r) => !r.is_adjustment);
  if (positive.length === 0) return null;
  const sum = positive.reduce((acc, r) => acc + Math.max(0, r.revenue_share_pct), 0);
  const widthPct = (r: { revenue_share_pct: number }) =>
    sum > 0 ? Math.max(0, r.revenue_share_pct) / sum * 100 : 0;
  return (
    <div className="flex w-full h-3 rounded overflow-hidden border border-vt-ink-700/60 mt-2">
      {positive.map((r, i) => (
        <div
          key={`${r.item}-${i}`}
          className={`${PALETTE[i % PALETTE.length]} transition-all`}
          style={{ width: `${widthPct(r)}%` }}
          title={`${r.item}: ${r.revenue_share_pct.toFixed(2)}%`}
        />
      ))}
    </div>
  );
}

function ByProductSection({ data, loading }: { data: MainBusinessResponse | null; loading: boolean }) {
  if (loading && !data) return <Skeleton rows={4} cols={6} />;
  if (!data || data.rows.length === 0) {
    return <div className="text-xs text-vt-parchment-dim py-2">暂无按产品数据</div>;
  }

  // Split rows: real products (with positive sales) vs. inter-segment adjustments
  // (negative sales or name containing 抵销/抵减/调整/合计). Adjustments are not "products" —
  // they're reconciliation entries and live in a separate block below the main table.
  const realRows = data.rows.filter((r) => !r.is_adjustment);
  const adjustmentRows = data.rows.filter((r) => r.is_adjustment);
  const hasAdjustments = adjustmentRows.length > 0;

  // Compute gross total for the subtotal row. Falls back to sum of real rows if backend
  // didn't include gross_sales (older cache entries).
  const grossTotal = data.gross_sales ?? realRows.reduce((acc, r) => acc + r.sales, 0);
  const netTotal = data.total_sales ?? (grossTotal + adjustmentRows.reduce((acc, r) => acc + r.sales, 0));
  const netPct = grossTotal > 0 ? (netTotal / grossTotal) * 100 : 0;

  return (
    <div className="overflow-x-auto -mx-3 sm:mx-0 px-3 sm:px-0">
      <table className="w-full text-sm min-w-[640px] sm:min-w-0">
        <thead>
          <tr className="border-b border-vt-ink-700">
            <th className="text-left py-2 px-2 vt-tab text-[10px]">产 品</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">收 入</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">收入占比</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">利 润</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">利润占比</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">毛利率</th>
          </tr>
        </thead>
        <tbody>
          {realRows.map((r, i) => (
            <tr key={`${r.item}-${i}`} className="border-b border-vt-ink-700/40">
              <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs text-vt-parchment">{r.item}</td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment">{formatYiYuan(r.sales)}</td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-brass-300">{formatPct(r.revenue_share_pct)}</td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment">{formatYiYuan(r.profit)}</td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment">{formatPct(r.profit_share_pct)}</td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment">{formatPct(r.gross_margin_pct)}</td>
            </tr>
          ))}
          {/* Subtotal: 毛收入合计 = 100% of gross */}
          <tr className="border-t-2 border-vt-brass-500/60">
            <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              毛收入合计
            </td>
            <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              {formatYiYuan(grossTotal)}
            </td>
            <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              100.00%
            </td>
            <td className="py-1.5 px-2" colSpan={3}></td>
          </tr>
        </tbody>
      </table>

      {/* Stacked bar only for real products; sum normalizes to 100%. */}
      <StackedBar rows={data.rows} />

      {hasAdjustments && (
        <table className="w-full text-sm min-w-[640px] sm:min-w-0 mt-3">
          <tbody>
            {adjustmentRows.map((r, i) => (
              <tr key={`${r.item}-${i}`} className="border-b border-vt-ink-700/40">
                <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  <span className="inline-flex items-center gap-2">
                    {r.item}
                    <span className="inline-block text-[10px] tracking-widest uppercase px-1.5 py-0.5 border border-vt-parchment-dim text-vt-parchment-dim rounded-sm">
                      调整项
                    </span>
                  </span>
                </td>
                <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  {formatYiYuan(r.sales)}
                </td>
                <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  {/* No share for adjustment rows — they're not products, they're reconciliation. */}
                  &mdash;
                </td>
                <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  {formatYiYuan(r.profit)}
                </td>
                <td className="py-1.5 px-2" colSpan={2}></td>
              </tr>
            ))}
            <tr className="border-t-2 border-vt-brass-500/60">
              <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                净 收 入
              </td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                {formatYiYuan(netTotal)}
              </td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                {formatPct(netPct)}
              </td>
              <td className="py-1.5 px-2" colSpan={3}></td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

function ByRegionSection({ data, loading }: { data: MainBusinessResponse | null; loading: boolean }) {
  if (loading && !data) return <Skeleton rows={3} cols={3} />;
  if (!data || data.rows.length === 0) {
    return <div className="text-xs text-vt-parchment-dim py-2">暂无按地区数据</div>;
  }

  const realRows = data.rows.filter((r) => !r.is_adjustment);
  const adjustmentRows = data.rows.filter((r) => r.is_adjustment);
  const hasAdjustments = adjustmentRows.length > 0;
  const grossTotal = data.gross_sales ?? realRows.reduce((acc, r) => acc + r.sales, 0);
  const netTotal = data.total_sales ?? (grossTotal + adjustmentRows.reduce((acc, r) => acc + r.sales, 0));
  const netPct = grossTotal > 0 ? (netTotal / grossTotal) * 100 : 0;

  return (
    <div className="overflow-x-auto -mx-3 sm:mx-0 px-3 sm:px-0">
      <table className="w-full text-sm min-w-[400px] sm:min-w-0">
        <thead>
          <tr className="border-b border-vt-ink-700">
            <th className="text-left py-2 px-2 vt-tab text-[10px]">地 区</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">收 入</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">收入占比</th>
          </tr>
        </thead>
        <tbody>
          {realRows.map((r, i) => {
            const overseas = isOverseas(r.item);
            const valueCls = overseas ? "text-vt-brass-300" : "text-vt-parchment";
            return (
              <tr key={`${r.item}-${i}`} className="border-b border-vt-ink-700/40">
                <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs text-vt-parchment">
                  <span className="inline-flex items-center gap-2">
                    {r.item}
                    {overseas && (
                      <span className="inline-block text-[10px] tracking-widest uppercase px-1.5 py-0.5 border border-vt-brass-400 text-vt-brass-300 rounded-sm">
                        海外
                      </span>
                    )}
                  </span>
                </td>
                <td className={`py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs ${valueCls}`}>
                  {formatYiYuan(r.sales)}
                </td>
                <td className={`py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs ${valueCls}`}>
                  {formatPct(r.revenue_share_pct)}
                </td>
              </tr>
            );
          })}
          <tr className="border-t-2 border-vt-brass-500/60">
            <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              毛收入合计
            </td>
            <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              {formatYiYuan(grossTotal)}
            </td>
            <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              100.00%
            </td>
          </tr>
        </tbody>
      </table>
      <StackedBar rows={data.rows} />

      {hasAdjustments && (
        <table className="w-full text-sm min-w-[400px] sm:min-w-0 mt-3">
          <tbody>
            {adjustmentRows.map((r, i) => (
              <tr key={`${r.item}-${i}`} className="border-b border-vt-ink-700/40">
                <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  <span className="inline-flex items-center gap-2">
                    {r.item}
                    <span className="inline-block text-[10px] tracking-widest uppercase px-1.5 py-0.5 border border-vt-parchment-dim text-vt-parchment-dim rounded-sm">
                      调整项
                    </span>
                  </span>
                </td>
                <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  {formatYiYuan(r.sales)}
                </td>
                <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  &mdash;
                </td>
              </tr>
            ))}
            <tr className="border-t-2 border-vt-brass-500/60">
              <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                净 收 入
              </td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                {formatYiYuan(netTotal)}
              </td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                {formatPct(netPct)}
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

function ByIndustrySection({ data, loading }: { data: MainBusinessResponse | null; loading: boolean }) {
  if (loading && !data) return <Skeleton rows={3} cols={3} />;
  if (!data || data.rows.length === 0) {
    return <div className="text-xs text-vt-parchment-dim py-2">暂无按行业数据</div>;
  }

  const realRows = data.rows.filter((r) => !r.is_adjustment);
  const adjustmentRows = data.rows.filter((r) => r.is_adjustment);
  const hasAdjustments = adjustmentRows.length > 0;
  const grossTotal = data.gross_sales ?? realRows.reduce((acc, r) => acc + r.sales, 0);
  const netTotal = data.total_sales ?? (grossTotal + adjustmentRows.reduce((acc, r) => acc + r.sales, 0));
  const netPct = grossTotal > 0 ? (netTotal / grossTotal) * 100 : 0;

  return (
    <div className="overflow-x-auto -mx-3 sm:mx-0 px-3 sm:px-0">
      <table className="w-full text-sm min-w-[400px] sm:min-w-0">
        <thead>
          <tr className="border-b border-vt-ink-700">
            <th className="text-left py-2 px-2 vt-tab text-[10px]">行 业</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">收 入</th>
            <th className="text-right py-2 px-2 vt-tab text-[10px]">收入占比</th>
          </tr>
        </thead>
        <tbody>
          {realRows.map((r, i) => (
            <tr key={`${r.item}-${i}`} className="border-b border-vt-ink-700/40">
              <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs text-vt-parchment">{r.item}</td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment">{formatYiYuan(r.sales)}</td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-brass-300">{formatPct(r.revenue_share_pct)}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-vt-brass-500/60">
            <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              毛收入合计
            </td>
            <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              {formatYiYuan(grossTotal)}
            </td>
            <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              100.00%
            </td>
          </tr>
        </tbody>
      </table>
      <StackedBar rows={data.rows} />

      {hasAdjustments && (
        <table className="w-full text-sm min-w-[400px] sm:min-w-0 mt-3">
          <tbody>
            {adjustmentRows.map((r, i) => (
              <tr key={`${r.item}-${i}`} className="border-b border-vt-ink-700/40">
                <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  <span className="inline-flex items-center gap-2">
                    {r.item}
                    <span className="inline-block text-[10px] tracking-widest uppercase px-1.5 py-0.5 border border-vt-parchment-dim text-vt-parchment-dim rounded-sm">
                      调整项
                    </span>
                  </span>
                </td>
                <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  {formatYiYuan(r.sales)}
                </td>
                <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs text-vt-parchment-dim italic">
                  &mdash;
                </td>
              </tr>
            ))}
            <tr className="border-t-2 border-vt-brass-500/60">
              <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                净 收 入
              </td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                {formatYiYuan(netTotal)}
              </td>
              <td className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                {formatPct(netPct)}
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

/** Compute a simple YoY-average forecast for the next period. Returns null if not enough data. */
function predictNext(sales: (number | null)[]): number | null {
  const valid = sales.filter((s): s is number => s != null);
  if (valid.length < 2) return null;
  const last = valid[valid.length - 1];
  const yoys: number[] = [];
  for (let i = 1; i < valid.length; i++) {
    if (valid[i - 1] > 0) yoys.push((valid[i] - valid[i - 1]) / valid[i - 1]);
  }
  if (yoys.length === 0) return null;
  // Cap extreme predictions to avoid absurd projections (e.g., a 3x spike)
  const avgYoy = Math.max(-0.9, Math.min(2.0, yoys.reduce((a, b) => a + b, 0) / yoys.length));
  return last * (1 + avgYoy);
}

interface PeriodCell {
  period: string;
  /** Raw value, null = no published data for this year. */
  actual: number | null;
  /** Forecast value, present only for the last column when actual is null. */
  forecast: number | null;
  /** yoy of (actual or forecast) vs the prior period's actual. */
  yoy: number | null;
}

/** Build a list of period cells per series, with the last (no-data) period optionally filled
 *  by a YoY-average forecast derived from earlier years. */
function buildPeriodCells(series: MainBusinessHistorySeries, periods: string[]): PeriodCell[] {
  return periods.map((p, idx) => {
    const v = series.values.find((x) => x.period === p);
    const actual = v?.sales ?? null;
    if (actual != null) {
      return { period: p, actual, forecast: null, yoy: v?.yoy_pct ?? null };
    }
    // No data: try to forecast this year from prior years
    const priorSales = periods.slice(0, idx).map((pp) => series.values.find((x) => x.period === pp)?.sales ?? null);
    const forecast = predictNext(priorSales);
    let yoy: number | null = null;
    if (forecast != null) {
      const lastActual = priorSales.filter((s): s is number => s != null).pop();
      yoy = lastActual && lastActual > 0 ? ((forecast - lastActual) / lastActual) * 100 : null;
    }
    return { period: p, actual, forecast, yoy };
  });
}

function CompactCrossPeriodTable({ data }: { data: MainBusinessHistoryResponse }) {
  // Build cells per series. Each cell may be actual or forecast.
  const allCells = data.series.map((s) => buildPeriodCells(s, data.periods));

  // Drop the last column entirely if no series has actual or forecast for it.
  const lastPeriodHasAny = allCells.some(
    (cells) => cells[cells.length - 1]?.actual != null || cells[cells.length - 1]?.forecast != null,
  );
  const visiblePeriods = lastPeriodHasAny ? data.periods : data.periods.slice(0, -1);

  // Compute max for bar normalization (actual + forecast, so the predicted column
  // is visually comparable to the actuals).
  let maxSales = 0;
  for (const cells of allCells) {
    for (const c of cells) {
      const v = c.actual ?? c.forecast;
      if (v != null && v > maxSales) maxSales = v;
    }
  }

  // Identify the forecast-only column (the last visible period that has no actuals in any row).
  const forecastPeriods = new Set<string>();
  for (const cells of allCells) {
    for (const c of cells) {
      if (c.actual == null && c.forecast != null) forecastPeriods.add(c.period);
    }
  }

  // Compute gross totals (sum of actual across all series + sum of forecast for the forecast year).
  const grossTotals = visiblePeriods.map((p) => {
    let sum = 0;
    let any = false;
    for (const cells of allCells) {
      const c = cells.find((x) => x.period === p);
      const v = c?.actual ?? c?.forecast;
      if (v != null) {
        sum += v;
        any = true;
      }
    }
    return any ? sum : null;
  });

  return (
    <div className="overflow-x-auto -mx-3 sm:mx-0 px-3 sm:px-0">
      <table className="w-full text-sm min-w-[520px] sm:min-w-0">
        <thead>
          <tr className="border-b border-vt-ink-700">
            <th className="text-left py-1.5 px-2 vt-tab text-[10px]">产 品</th>
            {visiblePeriods.map((p) => (
              <th key={p} className="text-right py-1.5 px-2 vt-tab text-[10px]">
                {p.slice(0, 4)}
                {forecastPeriods.has(p) && <span className="text-vt-brass-300 ml-0.5">(预)</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.series.map((s, rowIdx) => {
            const cells = allCells[rowIdx];
            return (
              <tr key={s.item} className="border-b border-vt-ink-700/40">
                <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs text-vt-parchment truncate max-w-0">
                  {s.item}
                </td>
                {visiblePeriods.map((p) => {
                  const c = cells.find((x) => x.period === p);
                  if (!c) return <td key={p}></td>;
                  const v = c.actual ?? c.forecast;
                  const isForecast = c.actual == null && c.forecast != null;
                  const heightPct = v != null ? (v / maxSales) * 100 : 0;
                  return (
                    <td key={p} className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Thin bar: 4px wide, 24px tall max */}
                        <div className="w-1 h-6 flex items-end justify-end" aria-hidden>
                          <div
                            className={`w-1 rounded-sm ${
                              isForecast
                                ? "bg-vt-brass-300/60 border-l border-r border-dashed border-vt-brass-300"
                                : "bg-vt-brass-400"
                            }`}
                            style={{ height: `${heightPct}%`, minHeight: v != null ? "2px" : "0" }}
                            title={v != null ? formatYiYuan(v) : NA}
                          />
                        </div>
                        <span className={`${isForecast ? "text-vt-brass-300 italic" : "text-vt-parchment"} tabular-nums`}>
                          {v != null ? `${(v / 1e8).toFixed(0)}` : NA}
                        </span>
                        {c.yoy != null && (
                          <span className={`${pctColorClass(c.yoy)} text-[9px] tabular-nums`}>
                            {formatPct(c.yoy, true)}
                          </span>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
          {/* Subtotal row: 毛收入合计 (gross, not net) */}
          <tr className="border-t-2 border-vt-brass-500/60">
            <td className="py-1.5 px-2 font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
              毛收入合计
            </td>
            {grossTotals.map((t, i) => {
              const prev = i > 0 ? grossTotals[i - 1] : null;
              const yoy = t != null && prev != null && prev > 0 ? ((t - prev) / prev) * 100 : null;
              const isForecast = forecastPeriods.has(visiblePeriods[i]);
              return (
                <td key={visiblePeriods[i]} className="py-1.5 px-2 text-right font-[var(--font-geist-mono)] text-xs font-semibold text-vt-brass-300">
                  <div className="flex items-center justify-end gap-1.5">
                    <span className={`tabular-nums ${isForecast ? "italic" : ""}`}>
                      {t != null ? `${(t / 1e8).toFixed(0)}` : NA}
                    </span>
                    {yoy != null && (
                      <span className={`${pctColorClass(yoy)} text-[9px] tabular-nums`}>
                        {formatPct(yoy, true)}
                      </span>
                    )}
                  </div>
                </td>
              );
            })}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function CrossPeriodSection({ data, loading }: { data: MainBusinessHistoryResponse | null; loading: boolean }) {
  if (loading && !data) return <Skeleton rows={3} cols={5} />;
  if (!data || data.series.length === 0) {
    return <div className="text-xs text-vt-parchment-dim py-2">暂无跨期数据</div>;
  }

  // Hide section if fewer than 2 non-null periods.
  const nonNullPeriods = new Set<string>();
  for (const s of data.series) {
    for (const v of s.values) {
      if (v.sales != null) nonNullPeriods.add(v.period);
    }
  }
  if (nonNullPeriods.size < 2) {
    return <div className="text-xs text-vt-parchment-dim py-2">历史数据不足，跳过跨期对比</div>;
  }

  return (
    <div>
      <div className="vt-engraved not-italic text-[10px] tracking-wider text-vt-parchment-dim mb-2">
        紧凑柱状表:每行 = 一条产品线,每列 = 一年。柱高 = 收入(亿元),<span className="italic text-vt-brass-300">(预)</span> = 用历史 YoY 均值外推的预测值。最下方"毛收入合计"扣除内部抵销后为净收入。
      </div>
      <CompactCrossPeriodTable data={data} />
    </div>
  );
}

export default function MainBusinessPanel({
  product,
  region,
  industry,
  history,
  loading,
  error,
  hasDistinctIndustry,
}: MainBusinessPanelProps) {
  // Compute overall state.
  const allEmpty =
    !loading.p && !loading.d && !loading.h &&
    (!product || product.rows.length === 0) &&
    (!region || region.rows.length === 0) &&
    (!industry || industry.rows.length === 0) &&
    (!history || history.series.length === 0);

  return (
    <section className="vt-panel p-3 sm:p-4">
      <h2 className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-parchment uppercase mb-4">
        <span className="text-vt-brass-400">❖</span> 主 营 业 务 构 成
      </h2>

      {/* Error state — surface only when P fetch failed AND data is missing. */}
      {error && !product && (
        <div className="text-center text-vt-brass-400 text-xs py-3 vt-engraved">
          {error}
        </div>
      )}

      {/* Empty state — all 4 sources empty/null AND not loading. */}
      {!error && allEmpty && (
        <div className="text-center text-vt-parchment-dim text-xs py-3 vt-engraved">
          暂无主营业务构成数据
        </div>
      )}

      {/* By product — always render if P has data or is loading. */}
      {(product || loading.p) && (product?.rows.length || loading.p) ? (
        <>
          <SectionHeader caption={`${product?.period ?? ""} · 按产品`}>按 产 品 (P)</SectionHeader>
          <ByProductSection data={product} loading={loading.p} />
        </>
      ) : null}

      {/* By region — only if has rows. */}
      {region && region.rows.length > 0 && (
        <>
          <SectionHeader caption={`${region.period ?? ""} · 按地区`}>按 地 区 (D)</SectionHeader>
          <ByRegionSection data={region} loading={loading.d} />
        </>
      )}

      {/* By industry — only if has distinct items. */}
      {hasDistinctIndustry && industry && industry.rows.length > 0 && (
        <>
          <SectionHeader caption={`${industry.period ?? ""} · 按行业`}>按 行 业 (I)</SectionHeader>
          <ByIndustrySection data={industry} loading={loading.i} />
        </>
      )}

      {/* Cross-period — always render if history has data or is loading. */}
      {(history || loading.h) && (history?.series.length || loading.h) ? (
        <>
          <SectionHeader caption="近 4 年 · 跨期对比">跨 期 对 比</SectionHeader>
          <CrossPeriodSection data={history} loading={loading.h} />
        </>
      ) : null}
    </section>
  );
}
