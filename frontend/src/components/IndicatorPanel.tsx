"use client";

import { useState } from "react";

interface Indicators {
  macd: {
    dif: number;
    dea: number;
    hist: number;
  } | null;
  rsi: {
    rsi6: number;
    rsi12: number;
    rsi24: number;
  } | null;
  ma: {
    ma5: number;
    ma10: number;
    ma20: number;
    ma60: number | null;
  } | null;
}

interface IndicatorPanelProps {
  indicators: Indicators | { error: string } | null;
  loading: boolean;
}

export default function IndicatorPanel({ indicators, loading }: IndicatorPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (loading) {
    return (
      <div>
        <div className="font-[var(--font-playfair)] text-sm tracking-[0.16em] text-vt-brass-300 uppercase mb-2">
          技 术 指 标
        </div>
        <div className="animate-pulse space-y-2">
          <div className="h-3 bg-vt-ink-700 rounded w-1/4"></div>
          <div className="h-3 bg-vt-ink-700 rounded w-1/3"></div>
          <div className="h-3 bg-vt-ink-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!indicators || "error" in indicators) {
    return (
      <div>
        <div className="font-[var(--font-playfair)] text-sm tracking-[0.16em] text-vt-brass-300 uppercase mb-2">
          技 术 指 标
        </div>
        <div className="text-center text-vt-brass-400 text-xs py-1">
          暂无详细数据
        </div>
      </div>
    );
  }

  const Cell = ({
    label,
    value,
    color,
  }: {
    label: string;
    value: number | null;
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
        {value !== null ? value.toFixed(2) : "--"}
      </span>
    </div>
  );

  const GroupTitle = ({ children }: { children: React.ReactNode }) => (
    <div className="font-[var(--font-playfair)] text-[11px] tracking-[0.16em] text-vt-brass-300 uppercase border-b border-vt-brass-500/20 pb-1 mb-1.5">
      {children}
    </div>
  );

  const NoData = () => (
    <div className="text-center text-vt-brass-500 text-[10px] py-1">暂无</div>
  );

  return (
    <div>
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex justify-between items-center mb-2 active:opacity-80"
      >
        <h3 className="font-[var(--font-playfair)] text-sm tracking-[0.16em] text-vt-brass-300 uppercase">
          技 术 指 标
        </h3>
        <span className="text-vt-brass-400 text-lg font-[var(--font-playfair)] leading-none">
          {collapsed ? "+" : "−"}
        </span>
      </button>

      {!collapsed && (
        <div className="grid grid-cols-3 gap-x-4 gap-y-1">
          <div>
            <GroupTitle>MACD (12,26,9)</GroupTitle>
            {indicators.macd ? (
              <>
                <Cell label="DIF" value={indicators.macd.dif} />
                <Cell label="DEA" value={indicators.macd.dea} />
                <Cell
                  label="MACD"
                  value={indicators.macd.hist}
                  color={
                    indicators.macd.hist >= 0
                      ? "text-vt-oxblood-400"
                      : "text-vt-emerald-400"
                  }
                />
              </>
            ) : (
              <NoData />
            )}
          </div>

          <div>
            <GroupTitle>RSI (6,12,24)</GroupTitle>
            {indicators.rsi ? (
              <>
                <Cell
                  label="RSI(6)"
                  value={indicators.rsi.rsi6}
                  color={
                    indicators.rsi.rsi6 > 70
                      ? "text-vt-oxblood-400"
                      : indicators.rsi.rsi6 < 30
                      ? "text-vt-emerald-400"
                      : "text-vt-parchment"
                  }
                />
                <Cell
                  label="RSI(12)"
                  value={indicators.rsi.rsi12}
                  color={
                    indicators.rsi.rsi12 > 70
                      ? "text-vt-oxblood-400"
                      : indicators.rsi.rsi12 < 30
                      ? "text-vt-emerald-400"
                      : "text-vt-parchment"
                  }
                />
                <Cell
                  label="RSI(24)"
                  value={indicators.rsi.rsi24}
                  color={
                    indicators.rsi.rsi24 > 70
                      ? "text-vt-oxblood-400"
                      : indicators.rsi.rsi24 < 30
                      ? "text-vt-emerald-400"
                      : "text-vt-parchment"
                  }
                />
              </>
            ) : (
              <NoData />
            )}
          </div>

          <div>
            <GroupTitle>MA 移动平均</GroupTitle>
            {indicators.ma ? (
              <>
                <Cell label="MA5" value={indicators.ma.ma5} />
                <Cell label="MA10" value={indicators.ma.ma10} />
                <Cell label="MA20" value={indicators.ma.ma20} />
                <Cell label="MA60" value={indicators.ma.ma60} />
              </>
            ) : (
              <NoData />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
