"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { PRESET_STOCKS } from "@/config/presetStocks";

interface StockInfo {
  symbol: string;
  name?: string;
  sector?: string;
  market?: string;
  error?: string;
}

interface ValuationData {
  pe: number | null;
  pb: number | null;
  turnover_rate: number | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function PresetStockList() {
  const [stocks, setStocks] = useState<
    Array<{ info: StockInfo; valuation: ValuationData | null; loading: boolean }>
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPresetStocks = async () => {
      setLoading(true);

      const results = await Promise.all(
        PRESET_STOCKS.map(async (stock) => {
          try {
            const [infoRes, valRes] = await Promise.all([
              fetch(`${API_BASE}/api/stock/${stock.symbol}`),
              fetch(`${API_BASE}/api/stock/${stock.symbol}/valuation?days=30`),
            ]);

            const infoData = await infoRes.json();
            const valData = await valRes.json();

            return {
              info: infoData,
              valuation: valData.latest
                ? {
                    pe: valData.latest.pe_ttm,
                    pb: valData.latest.pb,
                    turnover_rate: valData.latest.turnover_rate,
                  }
                : null,
              loading: false,
            };
          } catch (err) {
            console.error(`Failed to fetch ${stock.symbol}:`, err);
            return {
              info: { symbol: stock.symbol, name: stock.name, error: "数据加载失败" },
              valuation: null,
              loading: false,
            };
          }
        })
      );

      setStocks(results);
      setLoading(false);
    };

    fetchPresetStocks();
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="text-slate-400 text-center">加载中...</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg p-3 sm:p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-white">推荐股票</h2>
        <span className="text-slate-500 text-sm">游客预览</span>
      </div>

      {/* Desktop Table View */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-700">
              <th className="text-left py-2 px-3">股票代码</th>
              <th className="text-left py-2 px-3">股票名称</th>
              <th className="text-right py-2 px-3">市盈率(PE)</th>
              <th className="text-right py-2 px-3">市净率(PB)</th>
              <th className="text-right py-2 px-3">换手率</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map(({ info, valuation }) => (
              <tr
                key={info.symbol}
                className="text-white border-b border-slate-700/50 hover:bg-slate-700/30"
              >
                <td className="py-2 px-3">
                  <Link
                    href={`/stock/${info.symbol}`}
                    className="text-blue-400 hover:text-blue-300"
                  >
                    {info.symbol}
                  </Link>
                </td>
                <td className="py-2 px-3">
                  <Link
                    href={`/stock/${info.symbol}`}
                    className="hover:text-blue-300"
                  >
                    {info.name || info.symbol}
                  </Link>
                </td>
                <td className="py-2 px-3 text-right">
                  {valuation?.pe != null ? valuation.pe.toFixed(2) : "-"}
                </td>
                <td className="py-2 px-3 text-right">
                  {valuation?.pb != null ? valuation.pb.toFixed(2) : "-"}
                </td>
                <td className="py-2 px-3 text-right">
                  {valuation?.turnover_rate != null
                    ? `${valuation.turnover_rate.toFixed(2)}%`
                    : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="sm:hidden space-y-3">
        {stocks.map(({ info, valuation }) => (
          <Link
            key={info.symbol}
            href={`/stock/${info.symbol}`}
            className="block bg-slate-700/50 rounded-lg p-3 min-h-[44px] active:opacity-70 transition-opacity"
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <span className="text-blue-400 font-medium">{info.symbol}</span>
                <span className="text-white ml-2">{info.name || info.symbol}</span>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-slate-400">
              <div>
                <span className="text-white">{valuation?.pe != null ? valuation.pe.toFixed(2) : "-"}</span>
                <span className="text-slate-500 text-xs ml-1">PE</span>
              </div>
              <div>
                <span className="text-white">{valuation?.pb != null ? valuation.pb.toFixed(2) : "-"}</span>
                <span className="text-slate-500 text-xs ml-1">PB</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
