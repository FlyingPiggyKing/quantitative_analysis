"use client";

import { useState } from "react";

interface FinancialData {
  period?: string | null;
  ann_date?: string | null;
  report_label?: string | null;
  eps?: number | null;
  bps?: number | null;
  roe?: number | null;
  roe_yearly?: number | null;
  gross_margin?: number | null;
  netprofit_margin?: number | null;
  basic_eps_yoy?: number | null;
  netprofit_yoy?: number | null;
  tr_yoy?: number | null;
  debt_to_assets?: number | null;
  current_ratio?: number | null;
  total_revenue?: number | null;
  n_income?: number | null;
}

interface FinancialIndicatorsPanelProps {
  data: FinancialData | null;
  error?: string | null;
  loading: boolean;
}

export default function FinancialIndicatorsPanel({
  data,
  error,
  loading,
}: FinancialIndicatorsPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (loading) {
    return (
      <div>
        <div className="font-[var(--font-playfair)] text-sm tracking-[0.16em] text-vt-brass-300 uppercase mb-2">
          财 务 指 标
        </div>
        <div className="animate-pulse space-y-2">
          <div className="h-3 bg-vt-ink-700 rounded w-1/4"></div>
          <div className="h-3 bg-vt-ink-700 rounded w-1/3"></div>
          <div className="h-3 bg-vt-ink-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <div className="font-[var(--font-playfair)] text-sm tracking-[0.16em] text-vt-brass-300 uppercase mb-2">
          财 务 指 标
        </div>
        <div className="text-center text-vt-brass-400 text-xs py-1">
          {error || "暂无数据"}
        </div>
      </div>
    );
  }

  const fmt = (val: number | null | undefined): string => {
    if (val == null) return "--";
    return val.toFixed(2);
  };

  const fmtPct = (val: number | null | undefined): string => {
    if (val == null) return "--";
    return `${val >= 0 ? "+" : ""}${val.toFixed(2)}%`;
  };

  const fmtYuan = (val: number | null | undefined): string => {
    if (val == null) return "--";
    if (Math.abs(val) >= 1e8) return `${(val / 1e8).toFixed(2)}亿`;
    if (Math.abs(val) >= 1e4) return `${(val / 1e4).toFixed(2)}万`;
    return val.toFixed(2);
  };

  // Format ann_date from YYYYMMDD to YYYY-MM-DD for display
  const annDateDisplay = data.ann_date
    ? `${data.ann_date.slice(0, 4)}-${data.ann_date.slice(4, 6)}-${data.ann_date.slice(6, 8)}发布`
    : null;

  const Cell = ({
    label,
    value,
    color,
  }: {
    label: string;
    value: string;
    color?: string;
  }) => (
    <div className="flex justify-between items-baseline gap-2 py-0.5">
      <span className="vt-engraved not-italic text-[10px] tracking-widest uppercase whitespace-nowrap">
        {label}
      </span>
      <span
        className={`font-[var(--font-geist-mono)] text-xs font-medium ${
          color || "text-vt-parchment"
        }`}
      >
        {value}
      </span>
    </div>
  );

  const GroupTitle = ({ children }: { children: React.ReactNode }) => (
    <div className="font-[var(--font-playfair)] text-[11px] tracking-[0.16em] text-vt-brass-300 uppercase border-b border-vt-brass-500/20 pb-1 mb-1.5">
      {children}
    </div>
  );

  return (
    <div>
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex justify-between items-center mb-2 active:opacity-80"
      >
        <h3 className="font-[var(--font-playfair)] text-sm tracking-[0.16em] text-vt-brass-300 uppercase">
          财 务 指 标
          {data.report_label && (
            <span className="text-vt-brass-500 text-[10px] tracking-normal ml-1">
              {data.report_label}
            </span>
          )}
          {annDateDisplay && (
            <span className="text-vt-brass-600 text-[10px] tracking-normal ml-1">
              {annDateDisplay}
            </span>
          )}
        </h3>
        <span className="text-vt-brass-400 text-lg font-[var(--font-playfair)] leading-none">
          {collapsed ? "+" : "−"}
        </span>
      </button>

      {!collapsed && (
        <div className="grid grid-cols-4 gap-x-4 gap-y-1">
          <div>
            <GroupTitle>每股指标</GroupTitle>
            <Cell label="EPS" value={fmt(data.eps)} />
            <Cell label="BPS" value={fmt(data.bps)} />
          </div>

          <div>
            <GroupTitle>盈利能力</GroupTitle>
            <Cell
              label="ROE"
              value={fmtPct(data.roe)}
              color={
                data.roe != null
                  ? data.roe >= 15
                    ? "text-vt-oxblood-400"
                    : data.roe < 0
                    ? "text-vt-emerald-400"
                    : "text-vt-parchment"
                  : "text-vt-parchment"
              }
            />
            <Cell label="ROE年化" value={fmtPct(data.roe_yearly)} />
            <Cell label="毛利率" value={fmtPct(data.gross_margin)} />
            <Cell label="净利率" value={fmtPct(data.netprofit_margin)} />
          </div>

          <div>
            <GroupTitle>增长 (YoY)</GroupTitle>
            <Cell
              label="EPS增长"
              value={fmtPct(data.basic_eps_yoy)}
              color={
                data.basic_eps_yoy != null
                  ? data.basic_eps_yoy >= 0
                    ? "text-vt-oxblood-400"
                    : "text-vt-emerald-400"
                  : "text-vt-parchment"
              }
            />
            <Cell
              label="净利润增长"
              value={fmtPct(data.netprofit_yoy)}
              color={
                data.netprofit_yoy != null
                  ? data.netprofit_yoy >= 0
                    ? "text-vt-oxblood-400"
                    : "text-vt-emerald-400"
                  : "text-vt-parchment"
              }
            />
            <Cell
              label="营收增长"
              value={fmtPct(data.tr_yoy)}
              color={
                data.tr_yoy != null
                  ? data.tr_yoy >= 0
                    ? "text-vt-oxblood-400"
                    : "text-vt-emerald-400"
                  : "text-vt-parchment"
              }
            />
          </div>

          <div>
            <GroupTitle>财务健康</GroupTitle>
            <Cell
              label="资产负债率"
              value={fmtPct(data.debt_to_assets)}
              color={
                data.debt_to_assets != null
                  ? data.debt_to_assets > 70
                    ? "text-vt-oxblood-400"
                    : "text-vt-parchment"
                  : "text-vt-parchment"
              }
            />
            <Cell label="流动比率" value={fmt(data.current_ratio)} />
          </div>
        </div>
      )}
    </div>
  );
}
