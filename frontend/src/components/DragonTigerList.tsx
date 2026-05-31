"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getInstitutionalPrediction, InstitutionalTrendPrediction } from "@/services/institutionalTradingAnalysis";

interface DragonTigerItem {
  trade_date: string;
  ts_code: string;
  name: string;
  industry?: string;
  close: number | null;
  pct_change: number | null;
  net_amount: number | null;
  reason: string;
  appear_count: number;
  pe_ttm: number | null;
  total_mv_yi: number | null;
}

interface DragonTigerData {
  net_buy: DragonTigerItem[];
  net_sell: DragonTigerItem[];
  error: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchDragonTigerList(): Promise<DragonTigerData> {
  try {
    const res = await fetch(`${API_BASE}/api/stock/dragon-tiger-list`);
    if (!res.ok) {
      return { net_buy: [], net_sell: [], error: "API request failed" };
    }
    const data = await res.json();
    return {
      net_buy: data.net_buy || [],
      net_sell: data.net_sell || [],
      error: data.error || null,
    };
  } catch (err) {
    console.error("Failed to fetch dragon tiger list:", err);
    return { net_buy: [], net_sell: [], error: String(err) };
  }
}

function formatNetAmount(value: number | null, isBuy: boolean): string {
  if (value === null) return "-";
  const inYi = value / 1e8;
  const sign = isBuy ? "+" : "-";
  return `${sign}${Math.abs(inYi).toFixed(2)}亿`;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  if (dateStr.length === 8 && /^\d{8}$/.test(dateStr)) {
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
  }
  return dateStr;
}

function formatPctChange(value: number | null): string {
  if (value === null) return "-";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

interface AIPredictionCellProps {
  symbol: string;
  asLink?: boolean;
}

function AIPredictionCell({ symbol, asLink = true }: AIPredictionCellProps) {
  const [prediction, setPrediction] = useState<InstitutionalTrendPrediction | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getInstitutionalPrediction(symbol)
      .then(setPrediction)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [symbol]);

  if (loading) {
    return <span className="text-xs text-vt-parchment-dim">-</span>;
  }

  if (prediction) {
    const direction = prediction.trend_direction;
    const confidence = prediction.confidence;

    const content = (
      <span className="text-xs">
        <span className="text-lg leading-none">
          {direction === "up" ? "▲" : direction === "down" ? "▼" : "◆"}
        </span>
        {confidence}%
      </span>
    );

    const className = direction === "up"
      ? "vt-pred-up vt-pulse"
      : direction === "down"
      ? "vt-pred-down vt-pulse"
      : "vt-pred-flat";

    if (!asLink) {
      return <span className={className}>{content}</span>;
    }

    return (
      <Link
        href={`/stock/dragon-tiger/${symbol}`}
        className={className}
        title={prediction.summary}
      >
        {content}
      </Link>
    );
  }

  return <span className="text-xs text-vt-parchment-dim">-</span>;
}

interface DragonTigerRowProps {
  item: DragonTigerItem;
  isBuy: boolean;
}

function DragonTigerRow({ item, isBuy }: DragonTigerRowProps) {
  const symbol = item.ts_code.replace(".SH", "").replace(".SZ", "");

  return (
    <div className="flex items-center gap-4 py-2 px-3 border-b border-vt-ink-700/60 hover:bg-vt-ink-600/30 transition-colors text-sm">
      <div className="w-28 shrink-0">
        <Link
          href={`/stock/dragon-tiger/${symbol}`}
          className="block"
        >
          <div className="text-vt-brass-300 hover:text-vt-brass-400 tracking-wider font-[var(--font-geist-mono)] text-xs">
            {item.ts_code}
          </div>
          <div className="text-vt-parchment hover:text-vt-brass-300 transition-colors text-xs">
            {item.name}
            {item.appear_count > 1 && <span className="text-vt-parchment-dim ml-1">({item.appear_count}次)</span>}
          </div>
          {item.industry && (
            <div className="text-vt-parchment-dim text-[0.65rem]">{item.industry}</div>
          )}
        </Link>
      </div>
      <div className="w-16 text-right font-[var(--font-geist-mono)] text-xs shrink-0">
        {item.total_mv_yi != null ? item.total_mv_yi.toFixed(2) : "-"}
      </div>
      <div className="w-16 text-right font-[var(--font-geist-mono)] text-xs shrink-0">
        {item.pe_ttm != null ? item.pe_ttm.toFixed(1) : "-"}
      </div>
      <div className={`w-20 text-right font-[var(--font-geist-mono)] text-xs shrink-0 ${item.pct_change != null && item.pct_change >= 0 ? "text-vt-pred-up" : "text-vt-pred-down"}`}>
        {formatPctChange(item.pct_change)}
      </div>
      <div className={`w-24 text-right font-[var(--font-geist-mono)] text-xs shrink-0 ${isBuy ? "text-vt-pred-up" : "text-vt-pred-down"}`}>
        {formatNetAmount(item.net_amount, isBuy)}
      </div>
      <div className="w-20 text-right font-[var(--font-geist-mono)] text-xs shrink-0 text-vt-parchment-dim">
        {formatDate(item.trade_date)}
      </div>
      <div className="flex-1 flex justify-end pr-4">
        <AIPredictionCell symbol={symbol} />
      </div>
    </div>
  );
}

interface DragonTigerListProps {
  showHeader?: boolean;
  onDateChange?: (date: string) => void;
}

interface DragonTigerTableProps {
  data: DragonTigerItem[];
  isBuy: boolean;
}

function DragonTigerTable({ data, isBuy }: DragonTigerTableProps) {
  if (data.length === 0) {
    return (
      <div className="vt-engraved text-center py-8 text-sm">
        暂无数据
      </div>
    );
  }

  return (
    <div className="hidden sm:block">
      <div className="flex items-center gap-4 py-2 px-3 border-b border-vt-ink-700 text-xs">
        <div className="w-28 shrink-0 vt-tab text-left">股票</div>
        <div className="w-16 shrink-0 vt-tab text-right">市值(亿)</div>
        <div className="w-16 shrink-0 vt-tab text-right">PE TTM</div>
        <div className="w-20 shrink-0 vt-tab text-right">涨跌幅</div>
        <div className="w-24 shrink-0 vt-tab text-right">{isBuy ? "净买入" : "净卖出"}</div>
        <div className="w-20 shrink-0 vt-tab text-right">上榜时间</div>
        <div className="flex-1 flex justify-end vt-pred-col-header text-right pr-4">
          AI龙虎预测
        </div>
      </div>
      {data.map((item, idx) => (
        <DragonTigerRow key={`${item.ts_code}-${idx}`} item={item} isBuy={isBuy} />
      ))}
    </div>
  );
}

interface MobileCardProps {
  item: DragonTigerItem;
  isBuy: boolean;
}

function MobileCard({ item, isBuy }: MobileCardProps) {
  const symbol = item.ts_code.replace(".SH", "").replace(".SZ", "");

  return (
    <Link href={`/stock/dragon-tiger/${symbol}`} className="vt-card block p-3 min-h-[44px] active:opacity-80 transition-opacity">
      <div className="flex items-center gap-3">
        {/* Left: 4 stacked rows */}
        <div className="flex flex-col gap-1.5 min-w-0 flex-1">
          {/* Row 1: Title */}
          <div className="flex items-center flex-wrap gap-x-2">
            <span className="text-vt-brass-300 font-[var(--font-geist-mono)] tracking-wider">{item.ts_code}</span>
            <span className="text-vt-parchment">{item.name}</span>
            {item.appear_count > 1 && <span className="text-vt-parchment-dim text-xs">({item.appear_count}次)</span>}
          </div>
          {/* Row 2: Market Cap, PE */}
          <div className="flex items-center gap-x-4 text-xs">
            <span className="flex items-baseline gap-1">
              <span className="text-vt-parchment-dim tracking-wider">市值</span>
              <span className="text-vt-parchment font-[var(--font-geist-mono)]">
                {item.total_mv_yi != null ? item.total_mv_yi.toFixed(2) : "-"}
              </span>
              <span className="text-vt-parchment-dim">亿</span>
            </span>
            <span className="flex items-baseline gap-1">
              <span className="text-vt-parchment-dim tracking-wider">PE</span>
              <span className="text-vt-parchment font-[var(--font-geist-mono)]">
                {item.pe_ttm != null ? item.pe_ttm.toFixed(1) : "-"}
              </span>
            </span>
          </div>
          {/* Row 3: Net amount, PctChange */}
          <div className="flex items-center gap-x-4 text-xs">
            <span className="flex items-baseline gap-1">
              <span className="text-vt-parchment-dim tracking-wider">{isBuy ? "净买入" : "净卖出"}</span>
              <span className={`font-[var(--font-geist-mono)] ${isBuy ? "text-vt-pred-up" : "text-vt-pred-down"}`}>
                {formatNetAmount(item.net_amount, isBuy)}
              </span>
            </span>
            <span className="flex items-baseline gap-1">
              <span className="text-vt-parchment-dim tracking-wider">涨跌</span>
              <span className={`font-[var(--font-geist-mono)] ${item.pct_change != null && item.pct_change >= 0 ? "text-vt-pred-up" : "text-vt-pred-down"}`}>
                {formatPctChange(item.pct_change)}
              </span>
            </span>
          </div>
          {/* Row 4: Industry, Date */}
          <div className="flex items-center gap-x-4 text-xs">
            {item.industry && (
              <span className="text-vt-parchment font-semibold">{item.industry}</span>
            )}
            <span className="text-vt-parchment-dim font-[var(--font-geist-mono)]">{formatDate(item.trade_date)}</span>
          </div>
        </div>
        {/* Right: AI龙虎 (position unchanged) */}
        <div className="flex flex-col items-center gap-1 shrink-0 pl-3 border-l border-vt-ink-700/60">
          <div className="vt-pred-col-header text-[0.6rem]">AI龙虎</div>
          <AIPredictionCell symbol={symbol} asLink={false} />
        </div>
      </div>
    </Link>
  );
}

export default function DragonTigerList({ showHeader = true, onDateChange }: DragonTigerListProps) {
  const [data, setData] = useState<DragonTigerData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      const result = await fetchDragonTigerList();
      setData(result);
      setLoading(false);
    };
    fetchData();
  }, []);

  // Find the most recent trade date across all items (not just the first one)
  const displayDate = (() => {
    if (!data) return "";
    const allItems = [...(data.net_buy || []), ...(data.net_sell || [])];
    if (allItems.length === 0) return "";
    const dates = allItems.map(item => item.trade_date).filter(Boolean).sort();
    return dates.length > 0 ? formatDate(dates[dates.length - 1]) : "";
  })();

  // Notify parent of date change
  useEffect(() => {
    if (displayDate && onDateChange) {
      onDateChange(displayDate);
    }
  }, [displayDate, onDateChange]);

  return (
    <div className={showHeader ? "" : ""}>
      {/* Content */}
      {loading ? (
        <div className="vt-engraved text-center py-8 text-sm">加载中...</div>
      ) : data?.error ? (
        <div className="vt-engraved text-center py-8 text-sm text-vt-pred-down">数据加载失败</div>
      ) : (
        <>
          {/* Net Buy Section */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-vt-pred-up text-sm">▲</span>
              <span className="vt-tab text-sm">净买入</span>
            </div>
            <DragonTigerTable data={data?.net_buy || []} isBuy={true} />
            <div className="sm:hidden space-y-3">
              {(data?.net_buy || []).length === 0 ? (
                <div className="vt-engraved text-center py-4 text-sm">暂无数据</div>
              ) : (
                (data?.net_buy || []).map((item, idx) => (
                  <MobileCard key={`buy-${item.ts_code}-${idx}`} item={item} isBuy={true} />
                ))
              )}
            </div>
          </div>

          {/* Net Sell Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-vt-pred-down text-sm">▼</span>
              <span className="vt-tab text-sm">净卖出</span>
            </div>
            <DragonTigerTable data={data?.net_sell || []} isBuy={false} />
            <div className="sm:hidden space-y-3">
              {(data?.net_sell || []).length === 0 ? (
                <div className="vt-engraved text-center py-4 text-sm">暂无数据</div>
              ) : (
                (data?.net_sell || []).map((item, idx) => (
                  <MobileCard key={`sell-${item.ts_code}-${idx}`} item={item} isBuy={false} />
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
