"use client";

import { useEffect, useState } from "react";
import { fetchSectorTopStocks, SectorTopStocksResponse } from "@/services/sectorTopStocks";

interface Props {
  sector: string;
  dates: string[]; // YYYY-MM-DD, newest first
  top_n?: number;
}

function formatNetInflow(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}亿`;
}

function formatMarketCap(value: number | null): string {
  if (value == null) return "—";
  // ≥10000亿 → display as 万亿
  if (Math.abs(value) >= 10000) {
    return `${(value / 10000).toFixed(2)}万亿`;
  }
  return `${value.toFixed(2)}亿`;
}

export default function SectorTopStocksPanel({ sector, dates, top_n = 5 }: Props) {
  const [result, setResult] = useState<SectorTopStocksResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await fetchSectorTopStocks(sector, dates, top_n);
        if (!cancelled) setResult(data);
      } catch (e) {
        if (!cancelled) setResult({ sector, index_code: null, matched_name: null, by_date: {}, error: String(e) });
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [sector, dates.join(","), top_n]);

  if (loading) {
    return (
      <div className="mt-2 p-3 text-xs text-vt-parchment-soft border border-vt-ink-700 rounded bg-vt-ink-900/50">
        加载中…
      </div>
    );
  }

  if (!result) return null;

  if (result.error || !result.index_code) {
    return (
      <div className="mt-2 p-3 text-xs text-vt-oxblood-400 border border-vt-ink-700 rounded bg-vt-ink-900/50">
        {result.error || "无法匹配到申万行业成分股"}
      </div>
    );
  }

  const { by_date } = result;
  const dateKeys = Object.keys(by_date).sort().reverse();

  if (dateKeys.length === 0) {
    return (
      <div className="mt-2 p-3 text-xs text-vt-parchment-soft border border-vt-ink-700 rounded bg-vt-ink-900/50">
        暂无成分股数据
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-3">
      {dateKeys.map(date => {
        const stocks = by_date[date];
        return (
          <div key={date} className="border border-vt-ink-700 rounded overflow-hidden bg-vt-ink-900/30">
            <div className="px-3 py-1.5 bg-vt-ink-800/60 border-b border-vt-ink-700 text-xs text-vt-brass-400 font-mono">
              {date}
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-vt-parchment-soft/60 border-b border-vt-ink-700">
                  <th className="w-8 pl-3 py-1 text-left">#</th>
                  <th className="pl-2 py-1 text-left hidden sm:table-cell">名称</th>
                  <th className="pl-2 py-1 text-left">代码/名称</th>
                  <th className="pr-3 py-1 text-right">PE(TTM)</th>
                  <th className="pr-3 py-1 text-right">市值(亿)</th>
                  <th className="pr-3 py-1 text-right">主力净流入</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((stock, i) => {
                  const isPositive = stock.net_inflow >= 0;
                  const inflowColor = isPositive ? "text-vt-emerald-400" : "text-vt-oxblood-400";
                  const peStr = stock.pe_ttm != null ? stock.pe_ttm.toFixed(1) : "—";
                  const mvDisplay = formatMarketCap(stock.total_mv_yi);
                  return (
                    <tr key={stock.ts_code} className="border-b border-vt-ink-800 last:border-0 hover:bg-vt-ink-800/30">
                      <td className="pl-3 py-1 text-vt-parchment-soft/50 font-mono align-top">{i + 1}</td>
                      {/* Mobile: name + code stacked, Desktop: name inline */}
                      <td className="pl-2 py-1 text-vt-parchment-soft align-top hidden sm:table-cell">{stock.name}</td>
                      <td className="pl-2 py-1 align-top">
                        <span className="text-vt-parchment-soft sm:hidden">{stock.name}</span>
                        <span className="text-vt-parchment-soft/60 font-mono text-xs block sm:inline sm:ml-0">{stock.ts_code}</span>
                      </td>
                      <td className="pr-3 py-1 text-right font-mono tabular-nums text-vt-parchment-soft/80 align-top">{peStr}</td>
                      <td className="pr-3 py-1 text-right font-mono tabular-nums text-vt-parchment-soft/80 align-top">{mvDisplay}</td>
                      <td className={`pr-3 py-1 text-right font-mono tabular-nums ${inflowColor} align-top`}>
                        {formatNetInflow(stock.net_inflow)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}
