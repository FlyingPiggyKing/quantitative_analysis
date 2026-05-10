"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { PRESET_STOCKS, US_PRESET_STOCKS, HK_PRESET_STOCKS } from "@/config/presetStocks";
import { TrendPrediction, getTrendPredictions, fetchWithTimeout } from "@/services/trendPrediction";
import PETrendSparkline from "./PETrendSparkline";
import MoneyFlowSparkline from "./MoneyFlowSparkline";
import StockMarketTabs from "./StockMarketTabs";

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
  pe_history: Array<{ date: string; pe: number | null }>;
}

interface MoneyFlowData {
  flow_history: Array<{ date: string; flow: number | null }>;
  net_5d_total: number | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

interface PresetTableProps {
  stocks: Array<{ symbol: string; name: string }>;
  infoMap: Record<string, StockInfo>;
  valMap: Record<string, ValuationData>;
  flowMap: Record<string, MoneyFlowData>;
  predictions: Record<string, TrendPrediction>;
}

function PresetTable({ stocks, infoMap, valMap, flowMap, predictions }: PresetTableProps) {
  return (
    <>
      {/* Desktop View */}
      <div className="hidden sm:block">
        <div className="grid grid-cols-12 gap-3 py-2 px-3 border-b border-vt-ink-700 text-xs">
          <div className="col-span-3 vt-tab text-left">股票</div>
          <div className="col-span-3 vt-tab text-left">PE趋势</div>
          <div className="col-span-3 vt-tab text-left">主力资金</div>
          <div className="col-span-3 vt-pred-col-header text-center">AI下周预测</div>
        </div>
        <div>
          {stocks.map((stock) => {
            const info = infoMap[stock.symbol] || { symbol: stock.symbol, name: stock.name };
            const val = valMap[stock.symbol];
            const flow = flowMap[stock.symbol];
            return (
              <div
                key={stock.symbol}
                className="grid grid-cols-12 gap-3 py-2 px-3 border-b border-vt-ink-700/60 hover:bg-vt-ink-600/30 transition-colors text-vt-parchment text-sm"
              >
                {/* Left: Symbol + Name + PE/PB/换手率 stacked at bottom */}
                <div className="col-span-3 flex flex-col justify-between">
                  <div>
                    <Link
                      href={`/stock/${info.symbol}`}
                      className="text-vt-brass-300 hover:text-vt-brass-400 tracking-wider font-[var(--font-geist-mono)] block"
                    >
                      {info.symbol}
                    </Link>
                    <Link
                      href={`/stock/${info.symbol}`}
                      className="text-vt-parchment hover:text-vt-brass-300 transition-colors text-xs"
                    >
                      {info.name || info.symbol}
                    </Link>
                  </div>
                  <div className="flex items-center gap-3 text-[0.7rem] mt-2 font-[var(--font-geist-mono)]">
                    <span>
                      <span className="text-vt-parchment-dim">PE </span>
                      {val?.pe != null ? val.pe.toFixed(2) : "-"}
                    </span>
                    <span>
                      <span className="text-vt-parchment-dim">PB </span>
                      {val?.pb != null ? val.pb.toFixed(2) : "-"}
                    </span>
                    <span>
                      <span className="text-vt-parchment-dim">换手 </span>
                      {val?.turnover_rate != null ? `${val.turnover_rate.toFixed(2)}%` : "-"}
                    </span>
                  </div>
                </div>

                {/* PE Sparkline aligned to top */}
                <div className="col-span-3 flex items-start pt-1">
                  <PETrendSparkline peHistory={val?.pe_history ?? []} />
                </div>

                {/* Money Flow Sparkline aligned to top */}
                <div className="col-span-3 flex items-start pt-1">
                  <MoneyFlowSparkline flowHistory={flow?.flow_history ?? []} />
                </div>

                {/* AI Prediction aligned to top */}
                <div className="col-span-3 flex items-start justify-center pt-1">
                  {predictions[stock.symbol] ? (
                    <TrendIndicator prediction={predictions[stock.symbol]} />
                  ) : (
                    <span className="text-vt-parchment-dim">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Mobile Card View */}
      <div className="sm:hidden space-y-3">
        {stocks.map((stock) => {
          const info = infoMap[stock.symbol] || { symbol: stock.symbol, name: stock.name };
          const val = valMap[stock.symbol];
          const flow = flowMap[stock.symbol];
          return (
            <Link
              key={stock.symbol}
              href={`/stock/${info.symbol}`}
              className="vt-card block p-3 min-h-[44px] active:opacity-80 transition-opacity"
            >
              <div className="flex justify-between items-center mb-2">
                <div>
                  <span className="text-vt-brass-300 font-[var(--font-geist-mono)] tracking-wider">{info.symbol}</span>
                  <span className="text-vt-parchment ml-2">{info.name || info.symbol}</span>
                </div>
                <div className="vt-pred-col-header text-[0.6rem]">AI下周走势</div>
              </div>
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <PETrendSparkline peHistory={val?.pe_history ?? []} mobile />
                    <span className="text-vt-parchment-dim text-xs tracking-wider">PE</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <MoneyFlowSparkline flowHistory={flow?.flow_history ?? []} mobile />
                    <span className="text-vt-parchment-dim text-xs tracking-wider">主力</span>
                  </div>
                </div>
                {predictions[stock.symbol] ? (
                  <TrendIndicator prediction={predictions[stock.symbol]} />
                ) : (
                  <span className="text-vt-parchment-dim text-sm">—</span>
                )}
              </div>
              <div className="flex items-center gap-4 text-xs font-[var(--font-geist-mono)]">
                <span>
                  <span className="text-vt-parchment">{val?.pe != null ? val.pe.toFixed(2) : "-"}</span>
                  <span className="text-vt-parchment-dim ml-1">PE</span>
                </span>
                <span>
                  <span className="text-vt-parchment">{val?.pb != null ? val.pb.toFixed(2) : "-"}</span>
                  <span className="text-vt-parchment-dim ml-1">PB</span>
                </span>
                <span>
                  <span className="text-vt-parchment">{val?.turnover_rate != null ? `${val.turnover_rate.toFixed(2)}%` : "-"}</span>
                  <span className="text-vt-parchment-dim ml-1">换手</span>
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </>
  );
}

async function fetchMoneyFlowBatch(symbols: string[]): Promise<Record<string, MoneyFlowData>> {
  const flowMap: Record<string, MoneyFlowData> = {};
  const promises = symbols.map(async (symbol) => {
    try {
      const res = await fetch(`${API_BASE}/api/stock/${symbol}/moneyflow?days=30`);
      const data = await res.json();
      if (!data.error && data.data) {
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
  return flowMap;
}

interface PresetListImplProps {
  stocks: ReadonlyArray<{ symbol: string; name: string }>;
  loadingMessage?: string;
  loadingClassName?: string;
}

function PresetListImpl({ stocks, loadingMessage = "加载中…", loadingClassName = "vt-engraved text-center py-4" }: PresetListImplProps) {
  const [infoMap, setInfoMap] = useState<Record<string, StockInfo>>({});
  const [valMap, setValMap] = useState<Record<string, ValuationData>>({});
  const [flowMap, setFlowMap] = useState<Record<string, MoneyFlowData>>({});
  const [infoLoading, setInfoLoading] = useState(true);
  const [valLoading, setValLoading] = useState(true);
  const [predictions, setPredictions] = useState<Record<string, TrendPrediction>>({});
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const fetchData = async () => {
      try {
        const symbols = stocks.map((s) => s.symbol).join(",");
        const symbolList = stocks.map((s) => s.symbol);

        const infoRes = await fetch(`${API_BASE}/api/stock/batch/info?symbols=${symbols}`);
        const valRes = await fetch(`${API_BASE}/api/stock/batch/valuation?symbols=${symbols}&days=90`);

        if (infoRes.ok) {
          const infoData = await infoRes.json();
          const iMap: Record<string, StockInfo> = {};
          for (const item of infoData.results || []) {
            iMap[item.symbol] = item;
          }
          setInfoMap(iMap);
        }
        setInfoLoading(false);

        if (valRes.ok) {
          const valData = await valRes.json();
          const vMap: Record<string, ValuationData> = {};
          for (const item of valData.results || []) {
            if (item.latest) {
              vMap[item.symbol] = {
                pe: item.latest.pe_ttm,
                pb: item.latest.pb,
                turnover_rate: item.latest.turnover_rate,
                pe_history: (item.data || []).map((r: { trade_date: string; pe_ttm: number | null }) => ({
                  date: r.trade_date,
                  pe: r.pe_ttm,
                })),
              };
            }
          }
          setValMap(vMap);
        }
        setValLoading(false);

        // Fetch money flow data (non-blocking for initial render)
        fetchMoneyFlowBatch(symbolList).then(setFlowMap);

        // Fetch predictions with timeout (non-blocking)
        const predRes = await fetchWithTimeout(getTrendPredictions(), 5000);
        if (predRes) {
          const predMap: Record<string, TrendPrediction> = {};
          for (const pred of predRes) {
            predMap[pred.symbol] = pred;
          }
          setPredictions(predMap);
        }
      } catch (err) {
        console.error("Failed to fetch preset stocks:", err);
        setInfoLoading(false);
        setValLoading(false);
      }
    };

    fetchData();
  }, [stocks]);

  const isDataLoading = infoLoading || valLoading;

  if (isDataLoading) {
    return <div className={loadingClassName}>{loadingMessage}</div>;
  }

  return (
    <PresetTable
      stocks={stocks as Array<{ symbol: string; name: string }>}
      infoMap={infoMap}
      valMap={valMap}
      flowMap={flowMap}
      predictions={predictions}
    />
  );
}

export function ASharePresetList() {
  return <PresetListImpl stocks={PRESET_STOCKS} />;
}

export function USPresetList() {
  return (
    <PresetListImpl
      stocks={US_PRESET_STOCKS}
      loadingMessage={"美股数据刷新偏慢，请耐心等待，如数据不全，请再次刷新\n加载中…"}
      loadingClassName="vt-engraved text-center py-4 whitespace-pre-line"
    />
  );
}

export function HKPresetList() {
  return <PresetListImpl stocks={HK_PRESET_STOCKS} />;
}

export default function PresetStockList() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-[var(--font-playfair)] text-xl tracking-[0.18em] text-vt-parchment uppercase">
          <span className="text-vt-brass-400">❖</span> 推 荐 股 票 <span className="text-vt-brass-400">❖</span>
        </h2>
        <span className="vt-engraved text-sm">游客预览</span>
      </div>
      <StockMarketTabs
        aShareContent={<ASharePresetList />}
        usContent={<USPresetList />}
        hkContent={<HKPresetList />}
      />
    </div>
  );
}
