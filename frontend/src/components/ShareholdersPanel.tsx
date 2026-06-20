"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import CollapsibleHeader from "@/components/CollapsibleHeader";
import {
  getShareholdersOverview,
  getShareholdersInstitutional,
  getShareholdersHolderDetail,
  getShareholdersHoldingChanges,
  ShareholdersOverviewResponse,
  ShareholdersInstitutionalResponse,
  ShareholdersHolderDetailResponse,
  ShareholdersHoldingChangesResponse,
  ShareholderRow,
} from "@/services/shareholders";

interface ShareholdersPanelProps {
  market: "HK" | "US";
  symbol: string;
}



const NA = "—";

function currencySuffix(market: "HK" | "US"): string {
  return market === "HK" ? "亿HKD" : "亿美元";
}

function formatYiShares(val: number | null | undefined, market: "HK" | "US"): string {
  if (val == null) return NA;
  const yi = val / 1e8;
  if (Math.abs(yi) >= 1) return `${yi.toFixed(2)} 亿股`;
  const wan = val / 1e4;
  return `${wan.toFixed(2)} 万股`;
}

function formatYiSharesWithCurrency(val: number | null | undefined, market: "HK" | "US"): string {
  if (val == null) return NA;
  const yi = val / 1e8;
  return `${yi.toFixed(2)} ${currencySuffix(market)}`;
}

function formatPct(val: number | null | undefined, withSign = false, digits = 2): string {
  if (val == null) return NA;
  const rounded = val.toFixed(digits);
  if (!withSign) return `${rounded}%`;
  return val >= 0 ? `+${rounded}%` : `${rounded}%`;
}

function formatSignedChange(val: number | null | undefined): string {
  if (val == null) return NA;
  const sign = val >= 0 ? "+" : "";
  if (Math.abs(val) >= 1e8) return `${sign}${(val / 1e8).toFixed(2)} 亿股`;
  if (Math.abs(val) >= 1e4) return `${sign}${(val / 1e4).toFixed(2)} 万股`;
  return `${sign}${val.toFixed(0)} 股`;
}

function formatSignedPrice(val: number | null | undefined, market: "HK" | "US"): string {
  if (val == null) return NA;
  const sign = val >= 0 ? "+" : "";
  const absYi = Math.abs(val) / 1e8;
  return `${sign}${absYi.toFixed(2)} ${currencySuffix(market)}`;
}

// ---------------------------------------------------------------------------
// Skeletons + placeholders (vintage brass tone, matches MainBusinessPanel)
// ---------------------------------------------------------------------------
function VintageSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-3 bg-vt-brass-700/30 rounded w-full" />
      ))}
    </div>
  );
}

function EmptyPlaceholder({ text = "暂无持股数据" }: { text?: string }) {
  return (
    <div className="text-center text-vt-parchment-dim text-xs py-3 vt-engraved">
      {text}
    </div>
  );
}

function SectionHeader({ children, caption }: { children: ReactNode; caption?: string }) {
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

// ---------------------------------------------------------------------------
// Overview: top-5 holders enhanced bar (with 持股数 / 本期变动 / 占比) +
// top-5 trend chart + institutional aggregate + 近期变动 sub-sections +
// single-holder drill-down drawer.
// ---------------------------------------------------------------------------
function OverviewTab({ symbol, market }: { symbol: string; market: "HK" | "US" }) {
  const [data, setData] = useState<ShareholdersOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [trend, setTrend] = useState<HolderTrendSeries[]>([]);
  const [trendLoading, setTrendLoading] = useState(true);
  const [instData, setInstData] = useState<ShareholdersInstitutionalResponse | null>(null);
  const [instLoading, setInstLoading] = useState(true);
  const [incData, setIncData] = useState<ShareholdersHoldingChangesResponse | null>(null);
  const [decData, setDecData] = useState<ShareholdersHoldingChangesResponse | null>(null);
  const [changesLoading, setChangesLoading] = useState(true);
  const [drillHolder, setDrillHolder] = useState<{
    holder_id: number;
    name: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setData(null);
    getShareholdersOverview(symbol).then((d) => {
      if (cancelled) return;
      setData(d);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  // Institutional aggregate — fetched in parallel with overview/trend so
  // the bottom sub-block renders as soon as the data lands.
  useEffect(() => {
    let cancelled = false;
    setInstLoading(true);
    setInstData(null);
    getShareholdersInstitutional(symbol, 30).then((d) => {
      if (cancelled) return;
      setInstData(d);
      setInstLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  // Latest-period holding changes — two parallel fetches (increases +
  // decreases). Drives the bottom 增持榜 / 减持榜 sub-section.
  useEffect(() => {
    let cancelled = false;
    setChangesLoading(true);
    setIncData(null);
    setDecData(null);
    Promise.all([
      getShareholdersHoldingChanges(symbol, 1),
      getShareholdersHoldingChanges(symbol, 2),
    ]).then(([a, b]) => {
      if (cancelled) return;
      setIncData(a);
      setDecData(b);
      setChangesLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  // Top-5 holders by latest holder_pct, excluding the synthetic "Other" row.
  const topHolders = useMemo(() => {
    if (!data) return [];
    return (data.main_holder || [])
      .filter((r) => r.holder_id !== null)
      .sort((a, b) => b.holder_pct - a.holder_pct)
      .slice(0, 5);
  }, [data]);

  // Fetch each top holder's cross-period history in parallel (5 calls).
  // Each returns up to ~20 quarters; we plot all of them on a single
  // multi-line chart so the user can see Prosus reductions, BlackRock
  // accumulation, etc. at a glance.
  useEffect(() => {
    if (topHolders.length === 0) {
      setTrend([]);
      setTrendLoading(false);
      return;
    }
    let cancelled = false;
    setTrendLoading(true);
    setTrend([]);
    Promise.all(
      topHolders.map((h) =>
        getShareholdersHolderDetail(symbol, {
          holder_id: h.holder_id as number,
          num: 50,
        }).then(
          (d): HolderTrendSeries | null => {
            if (!d) return null;
            // Backend returns latest-first; flip to chronological for plotting.
            // Cap at the last 5 years (~20 quarters) so the chart stays readable
            // — Prosus etc. go back to ~2013 and the early period would compress
            // the recent quarters into a flat strip at the bottom.
            const periods = [...d.rows]
              .reverse()
              .slice(-20)
              .map((r) => ({
                period_text: r.period_text,
                holder_pct: r.holder_pct,
                holder_quantity: r.holder_quantity,
                holding_date_str: r.holding_date_str,
              }));
            return {
              holder_id: h.holder_id as number,
              name: h.name,
              periods,
              // Latest row keeps the latest 持股数 / 本期变动 / etc. for the
              // enhanced bar row (avoids an extra fetch when displaying).
              latest: d.rows[0] ?? null,
            };
          },
        ),
      ),
    ).then((series) => {
      if (cancelled) return;
      setTrend(series.filter((s): s is HolderTrendSeries => s !== null));
      setTrendLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [symbol, topHolders]);

  if (loading) {
    return <VintageSkeleton rows={5} />;
  }
  if (!data) return <EmptyPlaceholder />;

  const holderTypes = (data.holder_type || [])
    .filter((r) => r.holder_pct > 0)
    .sort((a, b) => b.holder_pct - a.holder_pct);

  const latestStaticDate = data.main_holder?.[0]?.static_date_str || "—";

  return (
    <div className="space-y-4">
      {/* 股东概览 — parent section header for both cards below (the
          holder-type donut and the Top-5 progress bar). Each card carries
          its own inner sub-title so the two views are labeled clearly. */}
      <SectionHeader caption={`截至 ${latestStaticDate} · 类 别 分 布`}>
        股 东 概 览
      </SectionHeader>

      <div className="bg-black/20 border border-vt-brass-700/30 rounded p-3">
        <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-2">
          股 东 类 型 分 布
        </div>
        {holderTypes.length === 0 ? (
          <EmptyPlaceholder />
        ) : (
          <div className="flex items-center gap-4">
            <DonutChart rows={holderTypes} />
            <div className="flex-1 space-y-1 text-xs">
              {holderTypes.slice(0, 6).map((t, i) => (
                <div key={`${t.name}-${i}`} className="flex items-center gap-2">
                  <span
                    className="inline-block w-2 h-2 rounded-sm shrink-0"
                    style={{ background: DONUT_PALETTE[i % DONUT_PALETTE.length] }}
                  />
                  <span className="text-vt-parchment truncate flex-1">{t.name}</span>
                  <span className="font-[var(--font-geist-mono)] text-vt-brass-300">
                    {t.holder_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Top-5 holders enhanced progress bar — name + 持股数 + 本期变动 + 占比.
          Each row is clickable to open the drill-down drawer for that
          holder's cross-period trajectory (the trend fetch already ran
          for the bar, so the drawer is a cache-hit re-fetch). */}
      <div className="bg-black/20 border border-vt-brass-700/30 rounded p-3">
        <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-2">
          top5 股 东 分 析
        </div>
          {topHolders.length === 0 ? (
            <EmptyPlaceholder />
          ) : (
            <div className="space-y-1.5">
              {topHolders.map((h, i) => {
                const series = trend.find(
                  (s) => s.holder_id === h.holder_id,
                );
                const latestRow = series?.latest ?? null;
                const changeTone =
                  latestRow && (latestRow.holder_pct_change || 0) >= 0
                    ? "text-vt-oxblood-400"
                    : "text-vt-emerald-400";
                const changeArrow =
                  latestRow && (latestRow.holder_pct_change || 0) >= 0
                    ? "▲"
                    : "▼";
                return (
                  <div
                    key={`${h.holder_id ?? "x"}-${i}`}
                    className="text-xs cursor-pointer hover:bg-vt-brass-700/10 rounded px-1 -mx-1 py-0.5"
                    onClick={() => {
                      if (h.holder_id != null) {
                        setDrillHolder({
                          holder_id: h.holder_id,
                          name: h.name,
                        });
                      }
                    }}
                  >
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span
                        className="text-vt-parchment truncate min-w-0 flex-1"
                        style={{
                          borderLeft: `3px solid ${TREND_PALETTE[i % TREND_PALETTE.length]}`,
                          paddingLeft: 6,
                        }}
                      >
                        {h.name}
                      </span>
                      <span className="font-[var(--font-geist-mono)] text-vt-brass-300 shrink-0 text-[11px]">
                        {latestRow
                          ? formatYiShares(latestRow.holder_quantity, market)
                          : NA}
                      </span>
                      <span
                        className={`font-[var(--font-geist-mono)] shrink-0 text-[11px] ${changeTone}`}
                      >
                        {latestRow && Number.isFinite(latestRow.holder_pct_change)
                          ? `${changeArrow} ${formatPct(Math.abs(latestRow.holder_pct_change), false, 2)}`
                          : NA}
                      </span>
                      <span className="font-[var(--font-geist-mono)] text-vt-parchment shrink-0 text-[11px]">
                        {h.holder_pct.toFixed(2)}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-vt-ink-700 rounded overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${Math.min(100, (h.holder_pct / 35) * 100)}%`,
                          background: TREND_PALETTE[i % TREND_PALETTE.length],
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      {/* Holder-type donut (latest snapshot).
          NOTE: per-type historical breakdown is not available — the
          holder_detail endpoint doesn't expose holder_type, so the type
          distribution can only be shown as a snapshot. The trend chart
          below covers the holder-name dimension (top-5 names). Placed
          here, BELOW the trend chart, so the holder-name story
          (Top-5 holders + their quarterly trajectory) reads first, and
          the holder-type breakdown reads as a second axis. */}
      {/* Holder-type donut moved above Top-5 (between the holder-type
          snapshot and the per-holder trajectory, so the type breakdown
          reads first as a higher-level "who owns this stock" summary). */}

      {/* 持股变化 + 机构持股变化 — stacked vertically (single column).
          Each chart keeps its own card frame. The outer SectionHeader
          spans the full width above the top5 card only (机构持股变化
          uses just an inner sub-title). */}
      <div className="grid grid-cols-1 gap-4">
        <div className="space-y-2">
          {(() => {
            const first = trend[0]?.periods?.[0]?.period_text ?? "";
            const last =
              trend[0]?.periods?.[trend[0].periods.length - 1]?.period_text ?? "";
            const range = first && last ? `${first} → ${last}` : "";
            return <SectionHeader caption={range}>持 股 变 化</SectionHeader>;
          })()}
          <div className="bg-black/20 border border-vt-brass-700/30 rounded p-3">
            <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-2">
              top5 持 股 变 化
            </div>
            {trendLoading ? (
              <div className="h-[240px] bg-black/10 rounded animate-pulse" />
            ) : trend.length === 0 ? (
              <EmptyPlaceholder text="无历史趋势数据" />
            ) : (
              <TopHoldersTrendChart series={trend} market={market} />
            )}
          </div>
        </div>

        <div className="space-y-2">
          <div className="bg-black/20 border border-vt-brass-700/30 rounded p-3">
            <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim mb-2">
              机 构 持 股 变 化
            </div>
            <InstitutionalBlock
              data={instData}
              loading={instLoading}
              market={market}
            />
          </div>
        </div>
      </div>

      {/* Latest-period holding changes — two side-by-side columns
          (增持榜 / 减持榜). No outer title or wrapper; each column is its
          own bordered card. */}
      <HoldingChangesBlock
        inc={incData}
        dec={decData}
        loading={changesLoading}
        market={market}
      />

      {/* Single-holder drill-down drawer — opens when a Top-5 bar row is
          clicked. The data is already cached (same key as the trend fetch). */}
      {drillHolder && (
        <HolderDrillDrawer
          symbol={symbol}
          market={market}
          holderId={drillHolder.holder_id}
          name={drillHolder.name}
          onClose={() => setDrillHolder(null)}
        />
      )}
    </div>
  );
}

// Distinct palette for the multi-line trend chart — broader contrast than
// the donut brass tones so 5 holders don't blur together.
const TREND_PALETTE = [
  "#e5c167", // brass-300 (gold leaf)
  "#d97a4e", // warm copper
  "#7fb89a", // sage green (opposite of brass on the wheel)
  "#c08bb8", // dusty violet
  "#5f8db1", // faded steel blue
];

interface HolderTrendPoint {
  period_text: string;
  holder_pct: number;
  holder_quantity: number;
  holding_date_str: string;
}

interface HolderTrendSeries {
  holder_id: number;
  name: string;
  periods: HolderTrendPoint[];
  /** Latest-period snapshot for the enhanced bar row (持股数 / 本期变动). */
  latest: ShareholdersHolderDetailResponse["rows"][number] | null;
}

function TopHoldersTrendChart({
  series,
  market,
}: {
  series: HolderTrendSeries[];
  market: "HK" | "US";
}) {
  const W = 600;
  const H = 240;
  const padL = 56; // wider left margin for "X.X 亿股" labels
  const padR = 48; // room for right Y-axis (占比 %)
  const padT = 16;
  const padB = 36;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  // Union of all periods across all series, sorted chronologically.
  // period_text format "YYYY/QN" sorts lexicographically = chronologically.
  const allPeriods = useMemo(() => {
    const set = new Set<string>();
    for (const s of series) for (const p of s.periods) set.add(p.period_text);
    return Array.from(set).sort();
  }, [series]);

  // Y-axis = 持股数 (raw share quantity), NOT 占比. Showing raw shares
  // makes real accumulation / reduction visible (e.g. Prosus's sale of
  // ~1B shares shows up as a clear downward step), whereas a 占比 chart
  // muddies it with the denominator (total outstanding shares) changing
  // at the same time.
  const qtyMax = useMemo(() => {
    let m = 1;
    for (const s of series) {
      for (const p of s.periods) {
        if ((p.holder_quantity || 0) > m) m = p.holder_quantity;
      }
    }
    return m * 1.1;
  }, [series]);

  // Right-axis scale for the dashed 占比 curves. Two curves per holder
  // (solid = 持股数, dashed = 占比) share one canvas but use independent
  // scales — left for shares, right for percentage.
  const pctMax = useMemo(() => {
    let m = 1;
    for (const s of series) {
      for (const p of s.periods) {
        if ((p.holder_pct || 0) > m) m = p.holder_pct;
      }
    }
    return m * 1.1;
  }, [series]);

  // Format an absolute share count for the Y-axis tick label.
  // Mirrors `formatYiShares` so the units are consistent with the bar
  // rows below the chart.
  const formatTickQty = (raw: number): string => {
    if (!Number.isFinite(raw) || raw <= 0) return "0";
    if (raw >= 1e8) return `${(raw / 1e8).toFixed(1)} 亿`;
    if (raw >= 1e4) return `${(raw / 1e4).toFixed(0)} 万`;
    return `${raw.toFixed(0)}`;
  };

  if (allPeriods.length === 0) {
    return <EmptyPlaceholder text="无趋势数据" />;
  }

  const xStep = allPeriods.length > 1 ? chartW / (allPeriods.length - 1) : chartW;
  const periodToX = (pt: string) => {
    const idx = allPeriods.indexOf(pt);
    return idx >= 0 ? padL + idx * xStep : padL;
  };

  // Avoid label crowding on narrow viewports.
  const labelStride = Math.max(1, Math.ceil(allPeriods.length / 6));

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block">
          {/* Left Y axis (持股数) */}
          <line
            x1={padL}
            y1={padT}
            x2={padL}
            y2={padT + chartH}
            stroke="#5a4113"
            strokeWidth={1}
          />
          {/* Right Y axis (占比) */}
          <line
            x1={padL + chartW}
            y1={padT}
            x2={padL + chartW}
            y2={padT + chartH}
            stroke="#5a4113"
            strokeWidth={1}
          />
          {/* Horizontal gridlines (4) */}
          {Array.from({ length: 5 }).map((_, i) => {
            const y = padT + (chartH / 4) * i;
            return (
              <line
                key={i}
                x1={padL}
                y1={y}
                x2={padL + chartW}
                y2={y}
                stroke="#3e2c0d"
                strokeWidth={0.5}
              />
            );
          })}
          {/* Left Y-axis labels — share count in 亿 / 万 / raw */}
          {Array.from({ length: 5 }).map((_, i) => {
            const v = ((4 - i) / 4) * qtyMax;
            const y = padT + (chartH / 4) * i;
            return (
              <text
                key={`y-${i}`}
                x={padL - 6}
                y={y + 4}
                textAnchor="end"
                className="fill-vt-parchment-dim"
                style={{ fontSize: 9, fontFamily: "var(--font-geist-mono)" }}
              >
                {formatTickQty(v)}
              </text>
            );
          })}
          {/* Right Y-axis labels — 占比 % */}
          {Array.from({ length: 5 }).map((_, i) => {
            const v = ((4 - i) / 4) * pctMax;
            const y = padT + (chartH / 4) * i;
            return (
              <text
                key={`yp-${i}`}
                x={padL + chartW + 6}
                y={y + 4}
                textAnchor="start"
                className="fill-vt-parchment-dim"
                style={{ fontSize: 9, fontFamily: "var(--font-geist-mono)" }}
              >
                {`${v.toFixed(1)}%`}
              </text>
            );
          })}
          {/* Two polylines per holder on the same canvas:
              - solid   line = 持股数 (left axis, qtyMax scale)
              - dashed  line = 占比   (right axis, pctMax scale)
              Same color so the pair visually groups together. */}
          {series.map((s, i) => {
            const color = TREND_PALETTE[i % TREND_PALETTE.length];
            const qtyPts = s.periods
              .map((p) => {
                const x = periodToX(p.period_text);
                const y = padT + chartH - ((p.holder_quantity || 0) / qtyMax) * chartH;
                return `${x},${y}`;
              })
              .join(" ");
            const pctPts = s.periods
              .map((p) => {
                const x = periodToX(p.period_text);
                const y = padT + chartH - ((p.holder_pct || 0) / pctMax) * chartH;
                return `${x},${y}`;
              })
              .join(" ");
            return (
              <g key={s.holder_id}>
                {/* 持股数 — solid */}
                <polyline
                  fill="none"
                  stroke={color}
                  strokeWidth={1.5}
                  points={qtyPts}
                  opacity={0.95}
                />
                {s.periods.map((p, j) => {
                  const x = periodToX(p.period_text);
                  const y = padT + chartH - ((p.holder_quantity || 0) / qtyMax) * chartH;
                  return (
                    <circle key={`qty-${j}`} cx={x} cy={y} r={2.2} fill={color} />
                  );
                })}
                {/* 占比 — dashed, thinner */}
                <polyline
                  fill="none"
                  stroke={color}
                  strokeWidth={1}
                  strokeDasharray="4 3"
                  strokeOpacity={0.7}
                  points={pctPts}
                />
                {s.periods.map((p, j) => {
                  const x = periodToX(p.period_text);
                  const y = padT + chartH - ((p.holder_pct || 0) / pctMax) * chartH;
                  return (
                    <circle
                      key={`pct-${j}`}
                      cx={x}
                      cy={y}
                      r={1.6}
                      fill={color}
                      fillOpacity={0.7}
                    />
                  );
                })}
              </g>
            );
          })}
          {/* X-axis labels */}
          {allPeriods.map((pt, i) => {
            if (i % labelStride !== 0 && i !== allPeriods.length - 1) return null;
            const x = padL + i * xStep;
            return (
              <text
                key={`xlbl-${i}`}
                x={x}
                y={H - 18}
                textAnchor="middle"
                className="fill-vt-parchment-dim"
                style={{ fontSize: 9, fontFamily: "var(--font-geist-mono)" }}
              >
                {pt}
              </text>
            );
          })}
        </svg>
      </div>
      {/* Legend — also acts as the row tints that line up with the progress
          bars above so the user can match a line to a bar by color. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px]">
        {/* Curve-style key so the user knows solid = 持股数, dashed = 占比 */}
        <span className="flex items-center gap-1 vt-engraved not-italic text-vt-parchment-dim">
          <span className="inline-block w-4 h-0.5 bg-vt-brass-300" />
          持
          <span className="inline-block w-4 h-0 bg-transparent border-t border-dashed border-vt-brass-300/70" style={{ borderTopStyle: "dashed" }} />
          占
        </span>
        {series.map((s, i) => {
          const color = TREND_PALETTE[i % TREND_PALETTE.length];
          const last = s.periods[s.periods.length - 1];
          return (
            <div key={s.holder_id} className="flex items-center gap-1.5 min-w-0">
              <span
                className="inline-block w-3 h-0.5 shrink-0"
                style={{ background: color }}
              />
              <span className="text-vt-parchment truncate max-w-[140px]">
                {s.name}
              </span>
              {last && (
                <>
                  <span className="font-[var(--font-geist-mono)] text-vt-brass-300 shrink-0">
                    {formatYiShares(last.holder_quantity, market)}
                  </span>
                  <span className="font-[var(--font-geist-mono)] text-vt-parchment-dim shrink-0">
                    · {(last.holder_pct || 0).toFixed(2)}%
                  </span>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const DONUT_PALETTE = [
  "#e5c167", // brass-300
  "#c89c3a", // brass-400
  "#a37a25", // brass-500
  "#7d5c1c", // brass-600
  "#5a4113", // brass-700
  "#3e2c0d", // brass-800
];

function DonutChart({ rows }: { rows: ShareholderRow[] }) {
  const total = rows.reduce((s, r) => s + (r.holder_pct || 0), 0);
  if (total <= 0) return null;
  const r = 30;
  const c = 2 * Math.PI * r;
  const size = 80;
  let acc = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      <g transform={`translate(${size / 2}, ${size / 2}) rotate(-90)`}>
        <circle r={r} fill="none" stroke="rgba(125,92,28,0.18)" strokeWidth={12} />
        {rows.map((row, i) => {
          const frac = (row.holder_pct || 0) / total;
          const dash = `${frac * c} ${c}`;
          const offset = -acc * c;
          acc += frac;
          return (
            <circle
              key={i}
              r={r}
              fill="none"
              stroke={DONUT_PALETTE[i % DONUT_PALETTE.length]}
              strokeWidth={12}
              strokeDasharray={dash}
              strokeDashoffset={offset}
            />
          );
        })}
      </g>
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="middle"
        className="fill-vt-brass-300"
        style={{ fontSize: 11, fontFamily: "var(--font-geist-mono)" }}
      >
        {rows.length}
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Institutional sub-block — renders dual-axis chart + metric strip from a
// pre-fetched institutional response. Used as the bottom section of the
// OverviewTab (no longer a standalone tab).
// ---------------------------------------------------------------------------
function InstitutionalBlock({
  data,
  loading,
  market,
}: {
  data: ShareholdersInstitutionalResponse | null;
  loading: boolean;
  market: "HK" | "US";
}) {
  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-[200px] bg-black/20 border border-vt-brass-700/30 rounded animate-pulse" />
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 bg-black/20 border border-vt-brass-700/30 rounded px-3 py-2 animate-pulse">
          <div className="h-4 w-32 bg-vt-brass-700/30 rounded" />
          <div className="h-4 w-px bg-vt-brass-700/30" />
          <div className="h-4 w-32 bg-vt-brass-700/30 rounded" />
          <div className="h-4 w-px bg-vt-brass-700/30" />
          <div className="h-4 w-24 bg-vt-brass-700/30 rounded" />
        </div>
      </div>
    );
  }
  if (!data || !data.periods || data.periods.length === 0) {
    return <EmptyPlaceholder text="暂无机构持股数据" />;
  }

  // Periods come latest-first from backend; flip to chronological for the chart.
  const periods = [...data.periods].reverse();

  const latest = data.periods[0];
  // "较 5 期 前" — net delta of holder_pct between the latest period and
  // 5 quarters ago. The backend returns periods in descending order, so
  // `data.periods[0]` = latest, `data.periods[5]` = 5 periods back.
  const fiveAgo = data.periods[5];
  const pctChange5 =
    fiveAgo && Number.isFinite(fiveAgo.holder_pct)
      ? (latest.holder_pct || 0) - (fiveAgo.holder_pct || 0)
      : null;
  const nonInstPct = Math.max(0, 100 - (latest.holder_pct || 0));

  return (
    <div className="space-y-3">
      {/* Chart — borderless; the outer card supplies the frame. */}
      <DualAxisChart periods={periods} />

      {/* Compact horizontal metric strip — borderless now; sits inside
          the same visual frame as the chart above. */}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[11px] font-[var(--font-geist-mono)]">
        <MetricInline label="机构数" value={`${latest.institution_quantity.toFixed(0)} 家`} />
        <Sep />
        <MetricInline
          label="持股数"
          value={formatYiSharesWithCurrency(latest.holder_quantity, market)}
        />
        <Sep />
        <MetricInline label="机构占比" value={formatPct(latest.holder_pct, false, 2)} highlight />
        <Sep />
        <MetricInline
          label="较 5 期 前"
          value={
            pctChange5 == null
              ? NA
              : formatPct(pctChange5, true, 2)
          }
          tone={
            pctChange5 == null
              ? undefined
              : pctChange5 >= 0
              ? "up"
              : "down"
          }
        />
        <Sep />
        <MetricInline
          label="数据时间"
          value={latest.update_time_str || NA}
          dim
        />
      </div>

      <div className="text-[10px] text-vt-parchment-dim vt-engraved leading-relaxed">
        非  机  构  持  仓 ≈ {nonInstPct.toFixed(2)}% （ 含 创 始 人 · 高 管 · 政 府 / 主 权 基 金 ·
        员 工 股 权 · 散 户 等 · 不 等 同 于 散 户 持 仓 ）
      </div>
    </div>
  );
}

function Sep() {
  return <span className="text-vt-brass-700/40 select-none">|</span>;
}

function MetricInline({
  label,
  value,
  tone,
  highlight,
  dim,
}: {
  label: string;
  value: string;
  tone?: "up" | "down";
  highlight?: boolean;
  dim?: boolean;
}) {
  const valueClass = dim
    ? "text-vt-parchment-dim"
    : tone === "up"
    ? "text-vt-oxblood-400 font-semibold"
    : tone === "down"
    ? "text-vt-emerald-400 font-semibold"
    : highlight
    ? "text-vt-brass-300 font-semibold"
    : "text-vt-parchment";
  return (
    <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
      <span className="vt-engraved not-italic text-[9px] tracking-widest uppercase text-vt-parchment-dim">
        {label}
      </span>
      <span className={valueClass}>{value}</span>
    </span>
  );
}

function DualAxisChart({
  periods,
}: {
  periods: ShareholdersInstitutionalResponse["periods"];
}) {
  const W = 600;
  const H = 200;
  const padL = 40;
  const padR = 40;
  const padT = 24; // bumped so the hover tooltip has room above the chart
  const padB = 28;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const pctMax = Math.max(1, ...periods.map((p) => p.holder_pct || 0)) * 1.1;
  const qtyMax = Math.max(1, ...periods.map((p) => p.institution_quantity || 0)) * 1.1;

  const xStep = periods.length > 1 ? chartW / (periods.length - 1) : chartW;

  const linePts = periods
    .map((p, i) => {
      const x = padL + i * xStep;
      const y = padT + chartH - ((p.holder_pct || 0) / pctMax) * chartH;
      return { x, y, p };
    });

  const linePath = linePts.map(({ x, y }) => `${x},${y}`).join(" ");
  const barW = Math.max(2, Math.min(20, xStep * 0.6));

  // Choose ~5 x-axis labels to avoid overlap.
  const labelStride = Math.max(1, Math.ceil(periods.length / 5));

  // Hover state — hovering either a bar OR a line dot reveals a floating
  // tooltip with period + institution_quantity + holder_pct. Replaces the
  // prior always-on max/min labels and the right-edge pct pill.
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const hovered = hoveredIdx != null ? periods[hoveredIdx] : null;
  const hoveredX = hoveredIdx != null ? padL + hoveredIdx * xStep : 0;

  // 5-periods-ago reference marker. Anchors the "较 5 期 前" metric strip
  // cell visually so the user can see what the delta is being computed against.
  // `periods.length - 6` because `periods` is chronological (oldest first),
  // so the 5th-from-last is `len - 6` (e.g. len=30, idx=24 = 5 back).
  const refIdx = periods.length - 6;
  const hasRef = refIdx >= 0 && periods.length >= 6;
  const refP = hasRef ? periods[refIdx] : null;
  const refX = hasRef ? padL + refIdx * xStep : 0;
  const refY =
    hasRef && refP
      ? padT + chartH - ((refP.holder_pct || 0) / pctMax) * chartH
      : 0;

  return (
    <div className="overflow-x-auto">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block">
        {/* Left axis (holder_pct) */}
        <line x1={padL} y1={padT} x2={padL} y2={padT + chartH} stroke="#5a4113" strokeWidth={1} />
        {/* Right axis (institution_quantity) */}
        <line
          x1={padL + chartW}
          y1={padT}
          x2={padL + chartW}
          y2={padT + chartH}
          stroke="#5a4113"
          strokeWidth={1}
        />
        {/* Gridlines (4 horizontal) + left y-axis percentage labels.
            Without these the user can't tell that the line is at 47% vs 5%. */}
        {Array.from({ length: 5 }).map((_, i) => {
          const y = padT + (chartH / 4) * i;
          const v = ((4 - i) / 4) * pctMax;
          return (
            <g key={`grid-${i}`}>
              <line
                x1={padL}
                y1={y}
                x2={padL + chartW}
                y2={y}
                stroke="#3e2c0d"
                strokeWidth={0.5}
              />
              <text
                x={padL - 6}
                y={y + 3.5}
                textAnchor="end"
                className="fill-vt-brass-300"
                style={{ fontSize: 9, fontFamily: "var(--font-geist-mono)" }}
              >
                {`${v.toFixed(0)}%`}
              </text>
            </g>
          );
        })}

        {/* Bars (right axis: institution_quantity) — kept faint so the
            holder_pct line reads as the primary signal. Hover anywhere on
            the bar to surface the tooltip. */}
        {periods.map((p, i) => {
          const x = padL + i * xStep - barW / 2;
          const h = ((p.institution_quantity || 0) / qtyMax) * chartH;
          const y = padT + chartH - h;
          return (
            <rect
              key={`bar-${i}`}
              x={x}
              y={y}
              width={barW}
              height={h}
              fill="#7d5c1c"
              opacity={hoveredIdx === i ? 0.6 : 0.35}
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
              style={{ cursor: "pointer" }}
            />
          );
        })}

        {/* Line halo (a thicker, semi-transparent stroke beneath the main
            line so the trend pops against the bars). */}
        <polyline
          fill="none"
          stroke="#f5d97a"
          strokeOpacity={0.25}
          strokeWidth={6}
          strokeLinejoin="round"
          strokeLinecap="round"
          points={linePath}
        />
        {/* Main line (left axis: holder_pct) */}
        <polyline
          fill="none"
          stroke="#f5d97a"
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
          points={linePath}
        />
        {/* Data dots — one per period. Hover triggers the same tooltip
            as the bar below so the user can hover either. */}
        {linePts.map(({ x, y }, i) => (
          <circle
            key={`dot-${i}`}
            cx={x}
            cy={y}
            r={hoveredIdx === i ? 5 : 3.5}
            fill="#0e0a06"
            stroke="#f5d97a"
            strokeWidth={hoveredIdx === i ? 2 : 1.5}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
            style={{ cursor: "pointer" }}
          />
        ))}

        {/* 5-periods-ago reference marker — dashed vertical guideline +
            hollow ring only. The value pill that used to sit here is
            gone; the hover tooltip now carries that info. */}
        {hasRef && refP && (
          <g>
            <line
              x1={refX}
              y1={padT}
              x2={refX}
              y2={padT + chartH}
              stroke="#f5d97a"
              strokeOpacity={0.25}
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            <circle
              cx={refX}
              cy={refY}
              r={5}
              fill="none"
              stroke="#f5d97a"
              strokeOpacity={0.6}
              strokeWidth={1.5}
            />
          </g>
        )}

        {/* Hover guide line — vertical hairline at the hovered period so
            the user can see exactly which period the tooltip refers to. */}
        {hovered && (
          <line
            x1={hoveredX}
            y1={padT}
            x2={hoveredX}
            y2={padT + chartH}
            stroke="#f5d97a"
            strokeOpacity={0.5}
            strokeWidth={1}
            pointerEvents="none"
          />
        )}

        {/* Hover tooltip — floating above the chart, anchored to the
            hovered period. Shows the three numbers that used to be
            scattered as always-on pills: period_text, institution_quantity
            (家数), holder_pct (占比). */}
        {hovered && (
          (() => {
            // Width and height match the longest expected content.
            const tw = 78;
            const th = 46;
            // Anchor near the top of the chart area; clamp horizontally so
            // the tooltip stays inside the SVG even at the rightmost /
            // leftmost periods.
            const tx = Math.max(padL, Math.min(hoveredX - tw / 2, padL + chartW - tw));
            const ty = Math.max(2, padT - th - 4);
            return (
              <g pointerEvents="none">
                <rect
                  x={tx}
                  y={ty}
                  width={tw}
                  height={th}
                  rx={3}
                  fill="#1a1208"
                  stroke="#f5d97a"
                  strokeOpacity={0.7}
                  strokeWidth={1}
                />
                <text
                  x={tx + tw / 2}
                  y={ty + 12}
                  textAnchor="middle"
                  className="fill-vt-brass-300"
                  style={{ fontSize: 9, fontFamily: "var(--font-geist-mono)" }}
                >
                  {hovered.period_text || "—"}
                </text>
                <text
                  x={tx + tw / 2}
                  y={ty + 26}
                  textAnchor="middle"
                  className="fill-vt-parchment"
                  style={{ fontSize: 10, fontFamily: "var(--font-geist-mono)", fontWeight: 600 }}
                >
                  {`${(hovered.institution_quantity || 0).toFixed(0)} 家`}
                </text>
                <text
                  x={tx + tw / 2}
                  y={ty + 40}
                  textAnchor="middle"
                  className="fill-vt-parchment"
                  style={{ fontSize: 10, fontFamily: "var(--font-geist-mono)", fontWeight: 600 }}
                >
                  {`${(hovered.holder_pct || 0).toFixed(2)}%`}
                </text>
              </g>
            );
          })()
        )}

        {/* X-axis labels */}
        {periods.map((p, i) => {
          if (i % labelStride !== 0 && i !== periods.length - 1) return null;
          const x = padL + i * xStep;
          return (
            <text
              key={`xlbl-${i}`}
              x={x}
              y={H - 8}
              textAnchor="middle"
              className="fill-vt-parchment-dim"
              style={{ fontSize: 9, fontFamily: "var(--font-geist-mono)" }}
            >
              {p.period_text}
            </text>
          );
        })}

        {/* Axis labels */}
        <text
          x={padL - 6}
          y={padT + 4}
          textAnchor="end"
          className="fill-vt-brass-300"
          style={{ fontSize: 10, fontWeight: 600 }}
        >
          %
        </text>
        <text
          x={padL + chartW + 6}
          y={padT + 4}
          textAnchor="start"
          className="fill-vt-brass-400"
          style={{ fontSize: 9 }}
        >
          家
        </text>
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single-holder drill-down drawer — opens when a Top-5 bar row in the
// Overview is clicked. Fetches the holder's full cross-period history
// (cached on the same key as the bar's trend fetch, so re-clicks are
// instant).
// ---------------------------------------------------------------------------

function HolderDrillDrawer({
  symbol,
  market,
  holderId,
  name,
  onClose,
}: {
  symbol: string;
  market: "HK" | "US";
  holderId: number;
  name: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<ShareholdersHolderDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setData(null);
    getShareholdersHolderDetail(symbol, { holder_id: holderId, num: 50 }).then((d) => {
      if (cancelled) return;
      setData(d);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [symbol, holderId]);

  // Backend returns latest-first; flip to chronological for the chart.
  const periods = useMemo(
    () => (data?.rows ? [...data.rows].reverse() : []),
    [data],
  );
  const firstPct = periods[0]?.holder_pct;
  const lastPct = periods[periods.length - 1]?.holder_pct;
  const delta =
    firstPct != null && lastPct != null ? lastPct - firstPct : null;

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative w-full sm:w-[480px] max-w-full h-full bg-[var(--vt-ink-900)] border-l border-vt-brass-700 overflow-y-auto p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim">
              单 一 股 东 历 史
            </div>
            <h3 className="vt-emboss text-base text-vt-parchment mt-1 truncate">
              {name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-vt-parchment-dim hover:text-vt-brass-300 text-xl leading-none px-2"
            aria-label="关闭"
          >
            ×
          </button>
        </div>

        {loading ? (
          <VintageSkeleton rows={6} />
        ) : periods.length === 0 ? (
          <EmptyPlaceholder text="该股东无历史数据" />
        ) : (
          <div className="space-y-3">
            {delta != null && (
              <div
                className={`px-3 py-2 rounded border ${
                  delta >= 0
                    ? "border-vt-oxblood-400/40 bg-vt-oxblood-400/10"
                    : "border-vt-emerald-400/40 bg-vt-emerald-400/10"
                }`}
              >
                <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim">
                  起 始 → 本 季 持 股 变 化
                </div>
                <div
                  className={`font-[var(--font-geist-mono)] text-lg ${
                    delta >= 0 ? "text-vt-oxblood-400" : "text-vt-emerald-400"
                  }`}
                >
                  {delta >= 0 ? "▲" : "▼"} {formatPct(Math.abs(delta), false, 2)}
                </div>
              </div>
            )}

            <HolderPctLineChart periods={periods} />

            <div className="space-y-1">
              <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim">
                历 史 持 仓
              </div>
              <div className="max-h-64 overflow-y-auto border border-vt-brass-700/30 rounded">
                <table className="w-full text-[10px]">
                  <thead className="sticky top-0 bg-black/40">
                    <tr className="text-vt-parchment-dim vt-tab">
                      <th className="text-left py-1 px-1">报 告 期</th>
                      <th className="text-right py-1 px-1">持 股 数</th>
                      <th className="text-right py-1 px-1">占 比</th>
                      <th className="text-right py-1 px-1">本 期 变 动</th>
                    </tr>
                  </thead>
                  <tbody>
                    {periods.map((p, i) => {
                      // 本期变动: compute locally as the delta between
                      // consecutive rows' 占比. The API's holder_pct_change
                      // field returns 0 for non-latest rows even when 占比
                      // visibly shifts (e.g. when the holder didn't transact
                      // but the company's total outstanding shares grew →
                      // dilution). Computing locally matches what the user
                      // sees in the 占比 column. The first row has no
                      // previous so we render "—".
                      const prev = i > 0 ? periods[i - 1] : null;
                      const localDelta = prev
                        ? (p.holder_pct || 0) - (prev.holder_pct || 0)
                        : null;
                      const t =
                        localDelta == null
                          ? "text-vt-parchment-dim"
                          : localDelta >= 0
                          ? "text-vt-oxblood-400"
                          : "text-vt-emerald-400";
                      return (
                        <tr
                          key={`${p.period_text}-${i}`}
                          className="border-t border-vt-brass-700/15"
                        >
                          <td className="py-1 px-1 text-vt-parchment-dim font-[var(--font-geist-mono)]">
                            {p.period_text}
                          </td>
                          <td className="py-1 px-1 text-right font-[var(--font-geist-mono)] text-vt-brass-300">
                            {formatYiShares(p.holder_quantity, market)}
                          </td>
                          <td className="py-1 px-1 text-right font-[var(--font-geist-mono)] text-vt-parchment">
                            {formatPct(p.holder_pct, false, 2)}
                          </td>
                          <td className={`py-1 px-1 text-right font-[var(--font-geist-mono)] ${t}`}>
                            {localDelta == null ? NA : formatPct(localDelta, true, 2)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function HolderPctLineChart({
  periods,
}: {
  periods: ShareholdersHolderDetailResponse["rows"];
}) {
  const W = 440;
  const H = 160;
  const padL = 36;
  const padR = 8;
  const padT = 8;
  const padB = 22;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const pctMax = Math.max(1, ...periods.map((p) => p.holder_pct || 0)) * 1.15;
  const xStep = periods.length > 1 ? chartW / (periods.length - 1) : chartW;
  const pts = periods
    .map((p, i) => {
      const x = padL + i * xStep;
      const y = padT + chartH - ((p.holder_pct || 0) / pctMax) * chartH;
      return `${x},${y}`;
    })
    .join(" ");
  const labelStride = Math.max(1, Math.ceil(periods.length / 5));

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block">
      <line x1={padL} y1={padT} x2={padL} y2={padT + chartH} stroke="#5a4113" />
      <line x1={padL} y1={padT + chartH} x2={padL + chartW} y2={padT + chartH} stroke="#5a4113" />
      {Array.from({ length: 4 }).map((_, i) => {
        const y = padT + (chartH / 3) * i;
        return (
          <line key={i} x1={padL} y1={y} x2={padL + chartW} y2={y} stroke="#3e2c0d" strokeWidth={0.5} />
        );
      })}
      <polyline fill="none" stroke="#e5c167" strokeWidth={1.5} points={pts} />
      {periods.map((p, i) => {
        if (i % labelStride !== 0 && i !== periods.length - 1) return null;
        const x = padL + i * xStep;
        return (
          <text
            key={`xlbl-${i}`}
            x={x}
            y={H - 6}
            textAnchor="middle"
            className="fill-vt-parchment-dim"
            style={{ fontSize: 8, fontFamily: "var(--font-geist-mono)" }}
          >
            {p.period_text}
          </text>
        );
      })}
      <text x={padL - 4} y={padT + 8} textAnchor="end" className="fill-vt-brass-400" style={{ fontSize: 9 }}>
        %
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Holding changes sub-block — two parallel ranked lists (increases /
// decreases). Used inside OverviewTab as a sub-section (no longer a tab).
// Fetching is owned by the parent (OverviewTab); this component just renders.
// ---------------------------------------------------------------------------
function HoldingChangesBlock({
  inc,
  dec,
  loading,
  market,
}: {
  inc: ShareholdersHoldingChangesResponse | null;
  dec: ShareholdersHoldingChangesResponse | null;
  loading: boolean;
  market: "HK" | "US";
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-2">
          <VintageSkeleton rows={5} />
        </div>
        <div className="space-y-2">
          <VintageSkeleton rows={5} />
        </div>
      </div>
    );
  }

  // Reporting period — surfaced in column headers so the user knows this
  // is a quarterly disclosure (Futu get_shareholders_holding_changes
  // returns one period at a time; not daily, not real-time).
  const periodText = inc?.rows?.[0]?.period_text ?? dec?.rows?.[0]?.period_text ?? "";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ChangesColumn
        title="增 持 榜"
        periodText={periodText}
        data={inc}
        market={market}
        sortAsc={false}
      />
      <ChangesColumn
        title="减 持 榜"
        periodText={periodText}
        data={dec}
        market={market}
        sortAsc={true}
      />
    </div>
  );
}

function holderTypeBadge(type: string): string {
  const t = (type || "").toLowerCase();
  if (t.includes("mutual") || t.includes("fund")) return "bg-blue-900/60 text-blue-200 border-blue-700/50";
  if (t.includes("hedge")) return "bg-amber-900/60 text-amber-200 border-amber-700/50";
  if (t.includes("private") || t.includes("company")) return "bg-zinc-700/60 text-zinc-200 border-zinc-500/50";
  if (t.includes("family") || t.includes("trust")) return "bg-purple-900/60 text-purple-200 border-purple-700/50";
  if (t.includes("pension") || t.includes("insurance") || t.includes("sovereign")) return "bg-emerald-900/60 text-emerald-200 border-emerald-700/50";
  if (t.includes("bank")) return "bg-sky-900/60 text-sky-200 border-sky-700/50";
  return "bg-vt-brass-700/30 text-vt-brass-300 border-vt-brass-700/50";
}

function ChangesColumn({
  title,
  periodText,
  data,
  market,
  sortAsc,
}: {
  title: string;
  periodText: string;
  data: ShareholdersHoldingChangesResponse | null;
  market: "HK" | "US";
  sortAsc: boolean;
}) {
  // Period totals — computed from the FULL response (up to 50 rows from
  // Futu), not just the top 5 displayed. Honest label "前 50 合计" surfaces
  // the cap so the user knows it's not all reporters in the period.
  // filter_type=1 (增持) → only positive share_change_num values
  // filter_type=2 (减持) → only negative share_change_num values
  // `sortAsc` on the listing side mirrors the bucket direction.
  const periodTotal = useMemo(() => {
    if (!data || !data.rows) return 0;
    if (sortAsc) {
      // 减持 bucket: sum of negatives (returned as a negative number, signed).
      return data.rows.reduce((s, r) => {
        const v = r.share_change_num || 0;
        return v < 0 ? s + v : s;
      }, 0);
    }
    // 增持 bucket: sum of positives.
    return data.rows.reduce((s, r) => {
      const v = r.share_change_num || 0;
      return v > 0 ? s + v : s;
    }, 0);
  }, [data, sortAsc]);

  const headerSubtitle = periodText ? ` · ${periodText}` : "";

  if (!data || !data.rows || data.rows.length === 0) {
    return (
      <div className="bg-black/20 border border-vt-brass-700/30 rounded p-3">
        <div className="flex items-baseline justify-between mb-2 gap-2">
          <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim">
            {title}
            <span className="text-vt-parchment-dim/60">{headerSubtitle}</span>
          </div>
        </div>
        <EmptyPlaceholder />
      </div>
    );
  }
  const sorted = [...data.rows]
    .sort((a, b) =>
      sortAsc
        ? (a.share_change_num || 0) - (b.share_change_num || 0)
        : (b.share_change_num || 0) - (a.share_change_num || 0),
    )
    .slice(0, 5);

  const totalTone =
    periodTotal >= 0 ? "text-vt-oxblood-400" : "text-vt-emerald-400";

  return (
    <div className="bg-black/20 border border-vt-brass-700/30 rounded p-3">
      <div className="flex items-baseline justify-between mb-2 gap-2">
        <div className="vt-engraved not-italic text-[10px] tracking-widest uppercase text-vt-parchment-dim shrink-0">
          {title}
          <span className="text-vt-parchment-dim/60">{headerSubtitle}</span>
        </div>
        <div className="text-right min-w-0">
          <div className="vt-engraved not-italic text-[9px] tracking-widest uppercase text-vt-parchment-dim leading-tight">
            前 50 合 计
          </div>
          <div
            className={`font-[var(--font-geist-mono)] text-[12px] font-semibold ${totalTone} truncate`}
            title={`${periodTotal.toLocaleString("en-US")} 股`}
          >
            {formatSignedChange(periodTotal)}
          </div>
        </div>
      </div>
      <div className="space-y-1">
        {sorted.map((r, i) => {
          const tone =
            (r.share_change_num || 0) >= 0 ? "text-vt-oxblood-400" : "text-vt-emerald-400";
          return (
            <div
              key={`${r.holder_id ?? "x"}-${i}`}
              className="flex items-center gap-2 text-[11px] border-b border-vt-brass-700/15 py-1"
            >
              <span className="text-vt-parchment-dim font-[var(--font-geist-mono)] w-6 shrink-0">
                {i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-vt-parchment truncate">{r.name || NA}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span
                    className={`px-1 py-0.5 text-[9px] rounded border ${holderTypeBadge(r.holder_type)}`}
                  >
                    {r.holder_type || "未 知"}
                  </span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className={`font-[var(--font-geist-mono)] text-[11px] ${tone}`}>
                  {formatSignedChange(r.share_change_num)}
                </div>
                <div className={`font-[var(--font-geist-mono)] text-[10px] ${tone}`}>
                  {formatPct(r.share_ratio_change, true, 2)}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top-level panel
// ---------------------------------------------------------------------------
export default function ShareholdersPanel({ market, symbol }: ShareholdersPanelProps) {
  const [open, setOpen] = useState(true);
  return (
    <section className="vt-panel p-3 sm:p-4">
      <CollapsibleHeader
        title="股 东 持 仓 研 究"
        open={open}
        onToggle={() => setOpen((o) => !o)}
      />
      {open && <OverviewTab symbol={symbol} market={market} />}
    </section>
  );
}
