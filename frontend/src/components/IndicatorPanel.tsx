"use client";

import { useState } from "react";

interface Indicators {
  macd: {
    dif: number;
    dea: number;
    hist: number;
  };
  rsi: {
    rsi6: number;
    rsi12: number;
    rsi24: number;
  };
  ma: {
    ma5: number;
    ma10: number;
    ma20: number;
    ma60: number | null;
  };
}

interface IndicatorPanelProps {
  indicators: Indicators | null;
  loading: boolean;
}

export default function IndicatorPanel({ indicators, loading }: IndicatorPanelProps) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-700 rounded w-1/4"></div>
          <div className="h-4 bg-slate-700 rounded w-1/3"></div>
          <div className="h-4 bg-slate-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!indicators) {
    return null;
  }

  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    macd: false,
    rsi: false,
    ma: false,
  });

  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const IndicatorCard = ({
    title,
    children,
    sectionKey,
  }: {
    title: string;
    children: React.ReactNode;
    sectionKey: string;
  }) => {
    const isCollapsed = collapsedSections[sectionKey];
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <button
          onClick={() => toggleSection(sectionKey)}
          className="w-full flex justify-between items-center min-h-[44px] active:opacity-70"
        >
          <h3 className="text-lg font-medium text-white">{title}</h3>
          <span className="text-slate-400 text-xl">{isCollapsed ? "+" : "−"}</span>
        </button>
        <div className={`space-y-2 text-sm ${isCollapsed ? "hidden" : "block"}`}>
          {children}
        </div>
      </div>
    );
  };

  const IndicatorRow = ({ label, value, color }: { label: string; value: number | null; color?: string }) => (
    <div className="flex justify-between items-center">
      <span className="text-slate-400">{label}</span>
      <span className={`font-mono ${color || "text-white"}`}>
        {value !== null ? value.toFixed(2) : "--"}
      </span>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <IndicatorCard title="MACD (12,26,9)" sectionKey="macd">
        <IndicatorRow label="DIF" value={indicators.macd.dif} />
        <IndicatorRow label="DEA" value={indicators.macd.dea} />
        <IndicatorRow
          label="MACD"
          value={indicators.macd.hist}
          color={indicators.macd.hist >= 0 ? "text-red-400" : "text-green-400"}
        />
      </IndicatorCard>

      <IndicatorCard title="RSI (6,12,24)" sectionKey="rsi">
        <IndicatorRow
          label="RSI(6)"
          value={indicators.rsi.rsi6}
          color={indicators.rsi.rsi6 > 70 ? "text-red-400" : indicators.rsi.rsi6 < 30 ? "text-green-400" : "text-white"}
        />
        <IndicatorRow
          label="RSI(12)"
          value={indicators.rsi.rsi12}
          color={indicators.rsi.rsi12 > 70 ? "text-red-400" : indicators.rsi.rsi12 < 30 ? "text-green-400" : "text-white"}
        />
        <IndicatorRow
          label="RSI(24)"
          value={indicators.rsi.rsi24}
          color={indicators.rsi.rsi24 > 70 ? "text-red-400" : indicators.rsi.rsi24 < 30 ? "text-green-400" : "text-white"}
        />
      </IndicatorCard>

      <IndicatorCard title="MA (移动平均线)" sectionKey="ma">
        <IndicatorRow label="MA5" value={indicators.ma.ma5} />
        <IndicatorRow label="MA10" value={indicators.ma.ma10} />
        <IndicatorRow label="MA20" value={indicators.ma.ma20} />
        <IndicatorRow label="MA60" value={indicators.ma.ma60} />
      </IndicatorCard>
    </div>
  );
}
