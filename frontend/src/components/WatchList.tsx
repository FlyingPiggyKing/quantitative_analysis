"use client";

import { useState, useEffect, ReactNode } from "react";
import Link from "next/link";
import { getWatchlist, WatchlistItem } from "@/services/watchlist";
import { getTrendPredictions, TrendPrediction } from "@/services/trendPrediction";
import PETrendSparkline from "./PETrendSparkline";
import StockMarketTabs from "./StockMarketTabs";

interface ValuationData {
  pe: number | null;
  pb: number | null;
  turnover_rate: number | null;
  pe_history: Array<{ date: string; pe: number | null }>;
}

interface WatchListProps {
  refreshTrigger?: number;
  activeTab?: "A" | "US";
  onTabChange?: (tab: "A" | "US") => void;
}

interface StockTableProps {
  items: WatchlistItem[];
  valuations: Record<string, ValuationData>;
  predictions: Record<string, TrendPrediction>;
}

function TrendIndicator({ prediction }: { prediction: TrendPrediction }) {
  const { trend_direction, confidence } = prediction;

  if (trend_direction === "up") {
    return (
      <span className="text-emerald-400">
        ↑ {confidence}%
      </span>
    );
  } else if (trend_direction === "down") {
    return (
      <span className="text-red-400">
        ↓ {confidence}%
      </span>
    );
  } else {
    return (
      <span className="text-slate-400">
        - {confidence}%
      </span>
    );
  }
}

function StockTable({ items, valuations, predictions }: StockTableProps) {
  if (items.length === 0) {
    return (
      <div className="text-slate-400 text-center py-8">
        暂无自选股票，搜索股票后点击"加入自选"
      </div>
    );
  }

  return (
    <>
      {/* Desktop Table View - hidden on mobile */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-700">
              <th className="text-left py-2 px-3">股票代码</th>
              <th className="text-left py-2 px-3">股票名称</th>
              <th className="text-left py-2 px-3">PE趋势</th>
              <th className="text-right py-2 px-3">市盈率(PE)</th>
              <th className="text-right py-2 px-3">市净率(PB)</th>
              <th className="text-right py-2 px-3">换手率</th>
              <th className="text-left py-2 px-3">AI下周预测</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const val = valuations[item.symbol];
              return (
                <tr
                  key={item.symbol}
                  className="text-white border-b border-slate-700/50 hover:bg-slate-700/30"
                >
                  <td className="py-2 px-3">
                    <Link
                      href={`/stock/${item.symbol}`}
                      className="text-blue-400 hover:text-blue-300"
                    >
                      {item.symbol}
                    </Link>
                  </td>
                  <td className="py-2 px-3">
                    <Link
                      href={`/stock/${item.symbol}`}
                      className="hover:text-blue-300"
                    >
                      {item.name}
                    </Link>
                  </td>
                  <td className="py-2 px-3">
                    <PETrendSparkline peHistory={val?.pe_history ?? []} />
                  </td>
                  <td className="py-2 px-3 text-right">
                    {val?.pe != null ? val.pe.toFixed(2) : "-"}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {val?.pb != null ? val.pb.toFixed(2) : "-"}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {val?.turnover_rate != null ? `${val.turnover_rate.toFixed(2)}%` : "-"}
                  </td>
                  <td className="py-2 px-3">
                    {predictions[item.symbol] ? (
                      <TrendIndicator prediction={predictions[item.symbol]} />
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View - visible only on mobile */}
      <div className="sm:hidden space-y-3">
        {items.map((item) => {
          const val = valuations[item.symbol];
          return (
            <Link
              key={item.symbol}
              href={`/stock/${item.symbol}`}
              className="block bg-slate-700/50 rounded-lg p-3 min-h-[44px] active:opacity-70 transition-opacity"
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="text-blue-400 font-medium">{item.symbol}</span>
                  <span className="text-white ml-2">{item.name}</span>
                </div>
                {predictions[item.symbol] ? (
                  <TrendIndicator prediction={predictions[item.symbol]} />
                ) : (
                  <span className="text-slate-500 text-sm">-</span>
                )}
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <PETrendSparkline peHistory={val?.pe_history ?? []} mobile />
                  <span className="text-slate-400 text-xs">PE趋势</span>
                </div>
                <div className="text-slate-400">
                  <span className="text-white">{val?.pe != null ? val.pe.toFixed(2) : "-"}</span>
                  <span className="text-slate-500 text-xs ml-1">PE</span>
                </div>
                <div className="text-slate-400">
                  <span className="text-white">{val?.pb != null ? val.pb.toFixed(2) : "-"}</span>
                  <span className="text-slate-500 text-xs ml-1">PB</span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </>
  );
}

interface PaginationProps {
  page: number;
  pageSize: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

function Pagination({ page, pageSize, totalPages, onPageChange, onPageSizeChange }: PaginationProps) {
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between mt-4 gap-3">
      <div className="flex items-center gap-2">
        <span className="text-slate-400 text-sm">每页显示:</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="bg-slate-700 text-white text-sm rounded px-2 py-1 border border-slate-600"
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={30}>30</option>
        </select>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page === 1}
          className="px-3 py-1 bg-slate-700 text-white text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600 active:scale-95 transition-transform min-h-[36px] min-w-[44px]"
        >
          上一页
        </button>
        <span className="text-slate-400 text-sm">
          第 {page} / {totalPages} 页
        </span>
        <button
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          className="px-3 py-1 bg-slate-700 text-white text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600 active:scale-95 transition-transform min-h-[36px] min-w-[44px]"
        >
          下一页
        </button>
      </div>
    </div>
  );
}

interface MarketWatchlistProps {
  market: "A" | "US";
  page: number;
  pageSize: number;
  totalPages: number;
  items: WatchlistItem[];
  valuations: Record<string, ValuationData>;
  predictions: Record<string, TrendPrediction>;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

function MarketWatchlist({
  market,
  page,
  pageSize,
  totalPages,
  items,
  valuations,
  predictions,
  onPageChange,
  onPageSizeChange,
}: MarketWatchlistProps) {
  // Filter items by market
  const marketItems = items.filter(item => item.market === market);

  return (
    <div>
      <StockTable
        items={marketItems}
        valuations={valuations}
        predictions={predictions}
      />
      {marketItems.length > 0 && (
        <Pagination
          page={page}
          pageSize={pageSize}
          totalPages={totalPages}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      )}
    </div>
  );
}

export default function WatchList({ refreshTrigger = 0, activeTab, onTabChange }: WatchListProps) {
  const [aShareItems, setAShareItems] = useState<WatchlistItem[]>([]);
  const [usItems, setUsItems] = useState<WatchlistItem[]>([]);
  const [predictions, setPredictions] = useState<Record<string, TrendPrediction>>({});
  const [valuations, setValuations] = useState<Record<string, ValuationData>>({});
  const [loading, setLoading] = useState(true);
  const [aSharePage, setASharePage] = useState(1);
  const [usPage, setUsPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [aShareTotalPages, setAShareTotalPages] = useState(1);
  const [usTotalPages, setUsTotalPages] = useState(1);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch A-share and US watchlists in parallel
        const [aShareData, usData] = await Promise.all([
          getWatchlist(aSharePage, pageSize, "A"),
          getWatchlist(usPage, pageSize, "US"),
        ]);

        setAShareItems(aShareData.items);
        setAShareTotalPages(aShareData.total_pages);
        setUsItems(usData.items);
        setUsTotalPages(usData.total_pages);

        // Fetch trend predictions
        try {
          const preds = await getTrendPredictions();
          const predMap: Record<string, TrendPrediction> = {};
          preds.forEach((p) => {
            predMap[p.symbol] = p;
          });
          setPredictions(predMap);
        } catch (err) {
          console.error("Failed to fetch predictions:", err);
        }

        // Fetch all symbols for batch valuation
        const allSymbols = [...aShareData.items, ...usData.items].map(item => item.symbol);
        if (allSymbols.length > 0) {
          const valMap: Record<string, ValuationData> = {};
          try {
            const res = await fetch(`${API_BASE}/api/stock/batch/valuation?symbols=${allSymbols.join(",")}&days=90`);
            const batchData = await res.json();
            for (const valData of batchData.results || []) {
              if (valData.latest) {
                valMap[valData.symbol] = {
                  pe: valData.latest.pe_ttm,
                  pb: valData.latest.pb,
                  turnover_rate: valData.latest.turnover_rate,
                  pe_history: (valData.data || []).map((r: { trade_date: string; pe_ttm: number | null }) => ({
                    date: r.trade_date,
                    pe: r.pe_ttm,
                  })),
                };
              }
            }
            if (batchData.errors && batchData.errors.length > 0) {
              console.warn("Some valuations failed to load:", batchData.errors);
            }
          } catch (err) {
            console.error("Failed to fetch batch valuation:", err);
          }
          setValuations(valMap);
        }
      } catch (err) {
        console.error("Failed to fetch watchlist:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [aSharePage, usPage, pageSize, refreshTrigger]);

  const handleASharePageChange = (page: number) => {
    setASharePage(page);
  };

  const handleUsPageChange = (page: number) => {
    setUsPage(page);
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setASharePage(1);
    setUsPage(1);
  };

  if (loading) {
    const loadingMessage = activeTab === "US"
      ? "美股数据刷新偏慢，请耐心等待，如数据不全，请再次刷新\n加载中..."
      : "加载中...";
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="text-slate-400 text-center">{loadingMessage}</div>
      </div>
    );
  }

  const aShareContent = (
    <MarketWatchlist
      market="A"
      page={aSharePage}
      pageSize={pageSize}
      totalPages={aShareTotalPages}
      items={aShareItems}
      valuations={valuations}
      predictions={predictions}
      onPageChange={handleASharePageChange}
      onPageSizeChange={handlePageSizeChange}
    />
  );

  const usContent = (
    <MarketWatchlist
      market="US"
      page={usPage}
      pageSize={pageSize}
      totalPages={usTotalPages}
      items={usItems}
      valuations={valuations}
      predictions={predictions}
      onPageChange={handleUsPageChange}
      onPageSizeChange={handlePageSizeChange}
    />
  );

  return (
    <div>
      <h2 className="text-lg font-medium text-white mb-4">我的自选</h2>
      <StockMarketTabs
        aShareContent={aShareContent}
        usContent={usContent}
        activeTab={activeTab}
        onTabChange={onTabChange}
      />
    </div>
  );
}
