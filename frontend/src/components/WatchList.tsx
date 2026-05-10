"use client";

import { useState, useEffect, ReactNode } from "react";
import Link from "next/link";
import { getWatchlist, WatchlistItem } from "@/services/watchlist";
import { getTrendPredictions, TrendPrediction } from "@/services/trendPrediction";
import PETrendSparkline from "./PETrendSparkline";
import MoneyFlowSparkline from "./MoneyFlowSparkline";
import StockMarketTabs from "./StockMarketTabs";

interface ValuationData {
  pe: number | null;
  pb: number | null;
  turnover_rate: number | null;
  pe_history: Array<{ date: string; pe: number | null }>;
}

interface MoneyFlowData {
  flow_history: Array<{ date: string; flow: number | null }>;
  net_5d_total: number | null;
}

interface WatchListProps {
  refreshTrigger?: number;
  activeTab?: "A" | "US" | "HK";
  onTabChange?: (tab: "A" | "US" | "HK") => void;
}

interface StockTableProps {
  items: WatchlistItem[];
  valuations: Record<string, ValuationData>;
  moneyflows: Record<string, MoneyFlowData>;
  predictions: Record<string, TrendPrediction>;
}

function TrendIndicator({ prediction }: { prediction: TrendPrediction }) {
  const { trend_direction, confidence } = prediction;

  if (trend_direction === "up") {
    return (
      <span className="vt-pred-up vt-pulse">
        <span className="text-lg leading-none">▲</span>
        {confidence}%
      </span>
    );
  } else if (trend_direction === "down") {
    return (
      <span className="vt-pred-down vt-pulse">
        <span className="text-lg leading-none">▼</span>
        {confidence}%
      </span>
    );
  } else {
    return (
      <span className="vt-pred-flat">
        <span className="text-lg leading-none">◆</span>
        {confidence}%
      </span>
    );
  }
}

function StockTable({ items, valuations, moneyflows, predictions }: StockTableProps) {
  if (items.length === 0) {
    return (
      <div className="vt-engraved text-center py-8">
        暂无自选股票，搜索股票后点击&ldquo;加入自选&rdquo;
      </div>
    );
  }

  return (
    <>
      {/* Desktop Table View - hidden on mobile */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-vt-ink-700">
              <th className="text-left py-2 px-3 vt-tab text-xs">股票代码</th>
              <th className="text-left py-2 px-3 vt-tab text-xs">股票名称</th>
              <th className="text-left py-2 px-3 vt-tab text-xs">PE趋势</th>
              <th className="text-left py-2 px-3 vt-tab text-xs">主力资金</th>
              <th className="text-right py-2 px-3 vt-tab text-xs">市盈率(PE)</th>
              <th className="text-right py-2 px-3 vt-tab text-xs">市净率(PB)</th>
              <th className="text-right py-2 px-3 vt-tab text-xs">换手率</th>
              <th className="text-center py-2 px-3 vt-pred-col-header">AI下周预测</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const val = valuations[item.symbol];
              const flow = moneyflows[item.symbol];
              return (
                <tr
                  key={item.symbol}
                  className="text-vt-parchment border-b border-vt-ink-700/60 hover:bg-vt-ink-600/30 transition-colors"
                >
                  <td className="py-2 px-3 font-[var(--font-geist-mono)]">
                    <Link
                      href={`/stock/${item.symbol}`}
                      className="text-vt-brass-300 hover:text-vt-brass-400 tracking-wider"
                    >
                      {item.symbol}
                    </Link>
                  </td>
                  <td className="py-2 px-3">
                    <Link
                      href={`/stock/${item.symbol}`}
                      className="text-vt-parchment hover:text-vt-brass-300 transition-colors"
                    >
                      {item.name}
                    </Link>
                  </td>
                  <td className="py-2 px-3">
                    <PETrendSparkline peHistory={val?.pe_history ?? []} />
                  </td>
                  <td className="py-2 px-3">
                    <MoneyFlowSparkline flowHistory={flow?.flow_history ?? []} />
                  </td>
                  <td className="py-2 px-3 text-right font-[var(--font-geist-mono)]">
                    {val?.pe != null ? val.pe.toFixed(2) : "-"}
                  </td>
                  <td className="py-2 px-3 text-right font-[var(--font-geist-mono)]">
                    {val?.pb != null ? val.pb.toFixed(2) : "-"}
                  </td>
                  <td className="py-2 px-3 text-right font-[var(--font-geist-mono)]">
                    {val?.turnover_rate != null ? `${val.turnover_rate.toFixed(2)}%` : "-"}
                  </td>
                  <td className="py-2 px-3 text-center">
                    {predictions[item.symbol] ? (
                      <TrendIndicator prediction={predictions[item.symbol]} />
                    ) : (
                      <span className="text-vt-parchment-dim">—</span>
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
          const flow = moneyflows[item.symbol];
          return (
            <Link
              key={item.symbol}
              href={`/stock/${item.symbol}`}
              className="vt-card block p-3 min-h-[44px] active:opacity-80 transition-opacity"
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="text-vt-brass-300 font-[var(--font-geist-mono)] tracking-wider">{item.symbol}</span>
                  <span className="text-vt-parchment ml-2">{item.name}</span>
                </div>
                <div className="text-right">
                  <div className="vt-pred-col-header text-[0.6rem] mb-1">AI预测</div>
                  {predictions[item.symbol] ? (
                    <TrendIndicator prediction={predictions[item.symbol]} />
                  ) : (
                    <span className="text-vt-parchment-dim text-sm">—</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <PETrendSparkline peHistory={val?.pe_history ?? []} mobile />
                  <span className="text-vt-parchment-dim text-xs tracking-wider">PE</span>
                </div>
                <div className="flex items-center gap-1">
                  <MoneyFlowSparkline flowHistory={flow?.flow_history ?? []} mobile />
                  <span className="text-vt-parchment-dim text-xs tracking-wider">主力</span>
                </div>
                <div>
                  <span className="text-vt-parchment font-[var(--font-geist-mono)]">{val?.pe != null ? val.pe.toFixed(2) : "-"}</span>
                  <span className="text-vt-parchment-dim text-xs ml-1">PE</span>
                </div>
                <div>
                  <span className="text-vt-parchment font-[var(--font-geist-mono)]">{val?.pb != null ? val.pb.toFixed(2) : "-"}</span>
                  <span className="text-vt-parchment-dim text-xs ml-1">PB</span>
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
        <label htmlFor="page-size" className="vt-engraved text-sm">每页显示:</label>
        <select
          id="page-size"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="vt-select"
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
          className="vt-btn-secondary px-3 py-1 text-xs disabled:opacity-40 disabled:cursor-not-allowed min-h-[36px] min-w-[44px]"
        >
          上 一 页
        </button>
        <span className="vt-engraved text-sm">
          第 <span className="text-vt-brass-300 font-[var(--font-geist-mono)] not-italic">{page}</span> / <span className="text-vt-brass-300 font-[var(--font-geist-mono)] not-italic">{totalPages}</span> 页
        </span>
        <button
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          className="vt-btn-secondary px-3 py-1 text-xs disabled:opacity-40 disabled:cursor-not-allowed min-h-[36px] min-w-[44px]"
        >
          下 一 页
        </button>
      </div>
    </div>
  );
}

interface MarketWatchlistProps {
  market: "A" | "US" | "HK";
  loading: boolean;
  page: number;
  pageSize: number;
  totalPages: number;
  items: WatchlistItem[];
  valuations: Record<string, ValuationData>;
  moneyflows: Record<string, MoneyFlowData>;
  predictions: Record<string, TrendPrediction>;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

async function fetchValuationByMarket(
  apiBase: string,
  symbols: string[]
): Promise<Record<string, ValuationData>> {
  if (symbols.length === 0) return {};
  const valMap: Record<string, ValuationData> = {};
  console.log(`[Valuation] Sending request for ${symbols.join(",")} at`, new Date().toISOString());
  try {
    const res = await fetch(`${apiBase}/api/stock/batch/valuation?symbols=${symbols.join(",")}&days=90`);
    console.log(`[Valuation] Received response for ${symbols.join(",")} at`, new Date().toISOString());
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
    console.error("Failed to fetch valuation:", err);
  }
  return valMap;
}

async function fetchMoneyFlowByMarket(
  apiBase: string,
  symbols: string[]
): Promise<Record<string, MoneyFlowData>> {
  if (symbols.length === 0) return {};
  const flowMap: Record<string, MoneyFlowData> = {};
  try {
    // Fetch moneyflow for each symbol individually since there's no batch endpoint yet
    const promises = symbols.map(async (symbol) => {
      try {
        const res = await fetch(`${apiBase}/api/stock/${symbol}/moneyflow?days=30`);
        const data = await res.json();
        if (!data.error && data.data) {
          // Determine flow field based on market
          const flowField = data.market === "A-share" ? "buy_lg_amount" : "main_in_flow";
          flowMap[symbol] = {
            flow_history: data.data.map((r: { trade_date?: string; date?: string; [key: string]: unknown }) => ({
              date: r.trade_date || r.date,
              flow: r[flowField] as number | null,
            })),
            net_5d_total: data.net_5d_total,
          };
        }
      } catch (err) {
        console.error(`Failed to fetch moneyflow for ${symbol}:`, err);
      }
    });
    await Promise.all(promises);
  } catch (err) {
    console.error("Failed to fetch moneyflow:", err);
  }
  return flowMap;
}

function MarketWatchlist({
  market,
  loading,
  page,
  pageSize,
  totalPages,
  items,
  valuations,
  moneyflows,
  predictions,
  onPageChange,
  onPageSizeChange,
}: MarketWatchlistProps) {
  // Filter items by market
  const marketItems = items.filter(item => item.market === market);

  if (loading) {
    const loadingMessage = market === "US"
      ? "美股数据刷新偏慢，请耐心等待，如数据不全，请再次刷新\n加载中..."
      : "加载中...";
    return (
      <div className="vt-card p-4">
        <div className="vt-engraved text-center whitespace-pre-line">{loadingMessage}</div>
      </div>
    );
  }

  return (
    <div>
      <StockTable
        items={marketItems}
        valuations={valuations}
        moneyflows={moneyflows}
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
  const [hkItems, setHkItems] = useState<WatchlistItem[]>([]);
  const [aSharePredictions, setASharePredictions] = useState<Record<string, TrendPrediction>>({});
  const [usPredictions, setUsPredictions] = useState<Record<string, TrendPrediction>>({});
  const [hkPredictions, setHkPredictions] = useState<Record<string, TrendPrediction>>({});
  const [aShareValuations, setAShareValuations] = useState<Record<string, ValuationData>>({});
  const [usValuations, setUsValuations] = useState<Record<string, ValuationData>>({});
  const [hkValuations, setHkValuations] = useState<Record<string, ValuationData>>({});
  const [aShareMoneyflows, setAShareMoneyflows] = useState<Record<string, MoneyFlowData>>({});
  const [usMoneyflows, setUsMoneyflows] = useState<Record<string, MoneyFlowData>>({});
  const [hkMoneyflows, setHkMoneyflows] = useState<Record<string, MoneyFlowData>>({});
  const [aShareLoading, setAShareLoading] = useState(true);
  const [usLoading, setUsLoading] = useState(true);
  const [hkLoading, setHkLoading] = useState(true);
  const [aSharePage, setASharePage] = useState(1);
  const [usPage, setUsPage] = useState(1);
  const [hkPage, setHkPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [aShareTotalPages, setAShareTotalPages] = useState(1);
  const [usTotalPages, setUsTotalPages] = useState(1);
  const [hkTotalPages, setHkTotalPages] = useState(1);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch A-share data independently
  useEffect(() => {
    let cancelled = false;
    const fetchAShareData = async () => {
      setAShareLoading(true);
      try {
        const aShareData = await getWatchlist(aSharePage, pageSize, "A");
        console.log("[A-Share] Watchlist items:", aShareData.items.map(i => i.symbol), "at", new Date().toISOString());
        if (cancelled) return;
        setAShareItems(aShareData.items);
        setAShareTotalPages(aShareData.total_pages);

        const aShareSymbols = aShareData.items.map(item => item.symbol);
        console.log("[A-Share] Calling fetchValuationByMarket at", new Date().toISOString());
        const aShareVal = await fetchValuationByMarket(API_BASE, aShareSymbols);
        console.log("[A-Share] fetchValuationByMarket returned at", new Date().toISOString());
        if (cancelled) return;
        setAShareValuations(aShareVal);

        // Fetch moneyflow data
        console.log("[A-Share] Calling fetchMoneyFlowByMarket at", new Date().toISOString());
        const aShareFlow = await fetchMoneyFlowByMarket(API_BASE, aShareSymbols);
        console.log("[A-Share] fetchMoneyFlowByMarket returned at", new Date().toISOString());
        if (cancelled) return;
        setAShareMoneyflows(aShareFlow);
      } catch (err) {
        console.error("Failed to fetch A-share watchlist:", err);
      } finally {
        if (!cancelled) {
          setAShareLoading(false);
        }
      }
    };

    fetchAShareData();
    return () => { cancelled = true; };
  }, [aSharePage, pageSize, refreshTrigger, API_BASE]);

  // Fetch US data independently
  useEffect(() => {
    let cancelled = false;
    const fetchUsData = async () => {
      setUsLoading(true);
      try {
        const usData = await getWatchlist(usPage, pageSize, "US");
        console.log("[US] Watchlist items:", usData.items.map(i => i.symbol), "at", new Date().toISOString());
        if (cancelled) return;
        setUsItems(usData.items);
        setUsTotalPages(usData.total_pages);

        const usSymbols = usData.items.map(item => item.symbol);
        console.log("[US] Calling fetchValuationByMarket at", new Date().toISOString());
        const usVal = await fetchValuationByMarket(API_BASE, usSymbols);
        console.log("[US] fetchValuationByMarket returned at", new Date().toISOString());
        if (cancelled) return;
        setUsValuations(usVal);

        // Fetch moneyflow data
        console.log("[US] Calling fetchMoneyFlowByMarket at", new Date().toISOString());
        const usFlow = await fetchMoneyFlowByMarket(API_BASE, usSymbols);
        console.log("[US] fetchMoneyFlowByMarket returned at", new Date().toISOString());
        if (cancelled) return;
        setUsMoneyflows(usFlow);
      } catch (err) {
        console.error("Failed to fetch US watchlist:", err);
      } finally {
        if (!cancelled) {
          setUsLoading(false);
        }
      }
    };

    fetchUsData();
    return () => { cancelled = true; };
  }, [usPage, pageSize, refreshTrigger, API_BASE]);

  // Fetch HK data independently
  useEffect(() => {
    let cancelled = false;
    const fetchHkData = async () => {
      setHkLoading(true);
      try {
        const hkData = await getWatchlist(hkPage, pageSize, "HK");
        console.log("[HK] Watchlist items:", hkData.items.map(i => i.symbol), "at", new Date().toISOString());
        if (cancelled) return;
        setHkItems(hkData.items);
        setHkTotalPages(hkData.total_pages);

        const hkSymbols = hkData.items.map(item => item.symbol);
        console.log("[HK] Calling fetchValuationByMarket at", new Date().toISOString());
        const hkVal = await fetchValuationByMarket(API_BASE, hkSymbols);
        console.log("[HK] fetchValuationByMarket returned at", new Date().toISOString());
        if (cancelled) return;
        setHkValuations(hkVal);

        // Fetch moneyflow data
        console.log("[HK] Calling fetchMoneyFlowByMarket at", new Date().toISOString());
        const hkFlow = await fetchMoneyFlowByMarket(API_BASE, hkSymbols);
        console.log("[HK] fetchMoneyFlowByMarket returned at", new Date().toISOString());
        if (cancelled) return;
        setHkMoneyflows(hkFlow);
      } catch (err) {
        console.error("Failed to fetch HK watchlist:", err);
      } finally {
        if (!cancelled) {
          setHkLoading(false);
        }
      }
    };

    fetchHkData();
    return () => { cancelled = true; };
  }, [hkPage, pageSize, refreshTrigger, API_BASE]);

  // Fetch predictions (non-blocking, shared across markets)
  useEffect(() => {
    const fetchPredictions = async () => {
      try {
        const allPreds = await getTrendPredictions();
        const aSharePredMap: Record<string, TrendPrediction> = {};
        const usPredMap: Record<string, TrendPrediction> = {};
        const hkPredMap: Record<string, TrendPrediction> = {};
        const aShareSet = new Set(aShareItems.map(i => i.symbol));
        const usSet = new Set(usItems.map(i => i.symbol));
        const hkSet = new Set(hkItems.map(i => i.symbol));
        allPreds.forEach((p) => {
          if (aShareSet.has(p.symbol)) {
            aSharePredMap[p.symbol] = p;
          }
          if (usSet.has(p.symbol)) {
            usPredMap[p.symbol] = p;
          }
          if (hkSet.has(p.symbol)) {
            hkPredMap[p.symbol] = p;
          }
        });
        setASharePredictions(aSharePredMap);
        setUsPredictions(usPredMap);
        setHkPredictions(hkPredMap);
      } catch (err) {
        console.error("Failed to fetch predictions:", err);
      }
    };

    fetchPredictions();
  }, [aShareItems, usItems, hkItems]);

  const handleASharePageChange = (page: number) => {
    setASharePage(page);
  };

  const handleUsPageChange = (page: number) => {
    setUsPage(page);
  };

  const handleHkPageChange = (page: number) => {
    setHkPage(page);
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setASharePage(1);
    setUsPage(1);
    setHkPage(1);
  };

  const aShareContent = (
    <MarketWatchlist
      market="A"
      loading={aShareLoading}
      page={aSharePage}
      pageSize={pageSize}
      totalPages={aShareTotalPages}
      items={aShareItems}
      valuations={aShareValuations}
      moneyflows={aShareMoneyflows}
      predictions={aSharePredictions}
      onPageChange={handleASharePageChange}
      onPageSizeChange={handlePageSizeChange}
    />
  );

  const usContent = (
    <MarketWatchlist
      market="US"
      loading={usLoading}
      page={usPage}
      pageSize={pageSize}
      totalPages={usTotalPages}
      items={usItems}
      valuations={usValuations}
      moneyflows={usMoneyflows}
      predictions={usPredictions}
      onPageChange={handleUsPageChange}
      onPageSizeChange={handlePageSizeChange}
    />
  );

  const hkContent = (
    <MarketWatchlist
      market="HK"
      loading={hkLoading}
      page={hkPage}
      pageSize={pageSize}
      totalPages={hkTotalPages}
      items={hkItems}
      valuations={hkValuations}
      moneyflows={hkMoneyflows}
      predictions={hkPredictions}
      onPageChange={handleHkPageChange}
      onPageSizeChange={handlePageSizeChange}
    />
  );

  return (
    <div>
      <h2 className="font-[var(--font-playfair)] text-xl tracking-[0.18em] text-vt-parchment mb-4 uppercase">
        <span className="text-vt-brass-400">❖</span> 我 的 自 选 <span className="text-vt-brass-400">❖</span>
      </h2>
      <StockMarketTabs
        aShareContent={aShareContent}
        usContent={usContent}
        hkContent={hkContent}
        activeTab={activeTab}
        onTabChange={onTabChange}
      />
    </div>
  );
}
