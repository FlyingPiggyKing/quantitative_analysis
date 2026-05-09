"use client";

import { useState, useEffect, useRef, ReactNode } from "react";
import Link from "next/link";
import { PRESET_STOCKS, US_PRESET_STOCKS, HK_PRESET_STOCKS } from "@/config/presetStocks";
import { TrendPrediction, getTrendPredictions, fetchWithTimeout } from "@/services/trendPrediction";
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

interface StockCardProps {
  info: StockInfo;
  valuation: ValuationData | null;
  prediction?: TrendPrediction;
  mobile?: boolean;
}

function StockRow({ info, valuation, prediction, mobile = false }: StockCardProps) {
  if (mobile) {
    return (
      <Link
        href={`/stock/${info.symbol}`}
        className="vt-card block p-3 min-h-[44px] active:opacity-80 transition-opacity"
      >
        <div className="flex justify-between items-start mb-2">
          <div>
            <span className="text-vt-brass-300 font-[var(--font-geist-mono)] tracking-wider">{info.symbol}</span>
            <span className="text-vt-parchment ml-2">{info.name || info.symbol}</span>
          </div>
          <div className="text-right">
            <div className="vt-pred-col-header text-[0.6rem] mb-1">AI下周走势</div>
            {prediction ? (
              <TrendIndicator prediction={prediction} />
            ) : (
              <span className="text-vt-parchment-dim text-sm">—</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div>
            <span className="text-vt-parchment font-[var(--font-geist-mono)]">{valuation?.pe != null ? valuation.pe.toFixed(2) : "-"}</span>
            <span className="text-vt-parchment-dim text-xs ml-1">PE</span>
          </div>
          <div>
            <span className="text-vt-parchment font-[var(--font-geist-mono)]">{valuation?.pb != null ? valuation.pb.toFixed(2) : "-"}</span>
            <span className="text-vt-parchment-dim text-xs ml-1">PB</span>
          </div>
        </div>
      </Link>
    );
  }

  return (
    <tr
      className="text-vt-parchment border-b border-vt-ink-700/60 hover:bg-vt-ink-600/30 transition-colors"
    >
      <td className="py-2 px-3 font-[var(--font-geist-mono)]">
        <Link
          href={`/stock/${info.symbol}`}
          className="text-vt-brass-300 hover:text-vt-brass-400 tracking-wider"
        >
          {info.symbol}
        </Link>
      </td>
      <td className="py-2 px-3">
        <Link
          href={`/stock/${info.symbol}`}
          className="text-vt-parchment hover:text-vt-brass-300 transition-colors"
        >
          {info.name || info.symbol}
        </Link>
      </td>
      <td className="py-2 px-3 text-right font-[var(--font-geist-mono)]">
        {valuation?.pe != null ? valuation.pe.toFixed(2) : "-"}
      </td>
      <td className="py-2 px-3 text-right font-[var(--font-geist-mono)]">
        {valuation?.pb != null ? valuation.pb.toFixed(2) : "-"}
      </td>
      <td className="py-2 px-3 text-right font-[var(--font-geist-mono)]">
        {valuation?.turnover_rate != null
          ? `${valuation.turnover_rate.toFixed(2)}%`
          : "-"}
      </td>
      <td className="py-2 px-3 text-center">
        {prediction ? (
          <TrendIndicator prediction={prediction} />
        ) : (
          <span className="text-vt-parchment-dim">—</span>
        )}
      </td>
    </tr>
  );
}

interface PresetTableProps {
  stocks: Array<{ symbol: string; name: string }>;
  infoMap: Record<string, StockInfo>;
  valMap: Record<string, any>;
  predictions: Record<string, TrendPrediction>;
}

function PresetTable({ stocks, infoMap, valMap, predictions }: PresetTableProps) {
  return (
    <>
      {/* Desktop Table View */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-vt-ink-700">
              <th className="text-left py-2 px-3 vt-tab text-xs">股票代码</th>
              <th className="text-left py-2 px-3 vt-tab text-xs">股票名称</th>
              <th className="text-right py-2 px-3 vt-tab text-xs">市盈率(PE)</th>
              <th className="text-right py-2 px-3 vt-tab text-xs">市净率(PB)</th>
              <th className="text-right py-2 px-3 vt-tab text-xs">换手率</th>
              <th className="text-center py-2 px-3 vt-pred-col-header">AI下周预测</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => {
              const info = infoMap[stock.symbol] || { symbol: stock.symbol, name: stock.name };
              const val = valMap[stock.symbol];
              return (
                <StockRow
                  key={stock.symbol}
                  info={info}
                  valuation={val?.latest ? {
                    pe: val.latest.pe_ttm,
                    pb: val.latest.pb,
                    turnover_rate: val.latest.turnover_rate,
                  } : null}
                  prediction={predictions[stock.symbol]}
                />
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="sm:hidden space-y-3">
        {stocks.map((stock) => {
          const info = infoMap[stock.symbol] || { symbol: stock.symbol, name: stock.name };
          const val = valMap[stock.symbol];
          return (
            <StockRow
              key={stock.symbol}
              info={info}
              valuation={val?.latest ? {
                pe: val.latest.pe_ttm,
                pb: val.latest.pb,
                turnover_rate: val.latest.turnover_rate,
              } : null}
              prediction={predictions[stock.symbol]}
              mobile
            />
          );
        })}
      </div>
    </>
  );
}

export function ASharePresetList() {
  const [infoMap, setInfoMap] = useState<Record<string, StockInfo>>({});
  const [valMap, setValMap] = useState<Record<string, any>>({});
  const [infoLoading, setInfoLoading] = useState(true);
  const [valLoading, setValLoading] = useState(true);
  const [predLoading, setPredLoading] = useState(true);
  const [predictions, setPredictions] = useState<Record<string, TrendPrediction>>({});
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const fetchData = async () => {
      try {
        const symbols = PRESET_STOCKS.map((s) => s.symbol).join(",");

        const infoRes = await fetch(`${API_BASE}/api/stock/batch/info?symbols=${symbols}`);
        const valRes = await fetch(`${API_BASE}/api/stock/batch/valuation?symbols=${symbols}&days=30`);

        // Process info data
        if (infoRes.ok) {
          const infoData = await infoRes.json();
          const iMap: Record<string, any> = {};
          for (const item of infoData.results || []) {
            iMap[item.symbol] = item;
          }
          for (const err of infoData.errors || []) {
            console.warn(`Failed to fetch info for ${err.symbol}:`, err.error);
          }
          setInfoMap(iMap);
        }
        setInfoLoading(false);

        // Process valuation data
        if (valRes.ok) {
          const valData = await valRes.json();
          const vMap: Record<string, any> = {};
          for (const item of valData.results || []) {
            vMap[item.symbol] = item;
          }
          for (const err of valData.errors || []) {
            console.warn(`Failed to fetch valuation for ${err.symbol}:`, err.error);
          }
          setValMap(vMap);
        }
        setValLoading(false);

        // Fetch predictions with timeout (non-blocking)
        setPredLoading(true);
        const predRes = await fetchWithTimeout(getTrendPredictions(), 5000);
        if (predRes) {
          const predMap: Record<string, TrendPrediction> = {};
          for (const pred of predRes) {
            predMap[pred.symbol] = pred;
          }
          setPredictions(predMap);
        }
        setPredLoading(false);
      } catch (err) {
        console.error("Failed to fetch A-share preset stocks:", err);
        setInfoLoading(false);
        setValLoading(false);
        setPredLoading(false);
      }
    };

    fetchData();
  }, []);

  // Display stock data when info and val are loaded, regardless of predictions
  const isDataLoading = infoLoading || valLoading;

  if (isDataLoading) {
    return <div className="vt-engraved text-center py-4">加载中…</div>;
  }

  return (
    <PresetTable
      stocks={PRESET_STOCKS as unknown as Array<{ symbol: string; name: string }>}
      infoMap={infoMap}
      valMap={valMap}
      predictions={predictions}
    />
  );
}

export function USPresetList() {
  const [infoMap, setInfoMap] = useState<Record<string, StockInfo>>({});
  const [valMap, setValMap] = useState<Record<string, any>>({});
  const [infoLoading, setInfoLoading] = useState(true);
  const [valLoading, setValLoading] = useState(true);
  const [predLoading, setPredLoading] = useState(true);
  const [predictions, setPredictions] = useState<Record<string, TrendPrediction>>({});
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const fetchData = async () => {
      try {
        const symbols = US_PRESET_STOCKS.map((s) => s.symbol).join(",");

        const infoRes = await fetch(`${API_BASE}/api/stock/batch/info?symbols=${symbols}`);
        const valRes = await fetch(`${API_BASE}/api/stock/batch/valuation?symbols=${symbols}&days=30`);

        // Process info data
        if (infoRes.ok) {
          const infoData = await infoRes.json();
          const iMap: Record<string, any> = {};
          for (const item of infoData.results || []) {
            iMap[item.symbol] = item;
          }
          for (const err of infoData.errors || []) {
            console.warn(`Failed to fetch info for ${err.symbol}:`, err.error);
          }
          setInfoMap(iMap);
        }
        setInfoLoading(false);

        // Process valuation data
        if (valRes.ok) {
          const valData = await valRes.json();
          const vMap: Record<string, any> = {};
          for (const item of valData.results || []) {
            vMap[item.symbol] = item;
          }
          for (const err of valData.errors || []) {
            console.warn(`Failed to fetch valuation for ${err.symbol}:`, err.error);
          }
          setValMap(vMap);
        }
        setValLoading(false);

        // Fetch predictions with timeout (non-blocking)
        setPredLoading(true);
        const predRes = await fetchWithTimeout(getTrendPredictions(), 5000);
        if (predRes) {
          const predMap: Record<string, TrendPrediction> = {};
          for (const pred of predRes) {
            predMap[pred.symbol] = pred;
          }
          setPredictions(predMap);
        }
        setPredLoading(false);
      } catch (err) {
        console.error("Failed to fetch US preset stocks:", err);
        setInfoLoading(false);
        setValLoading(false);
        setPredLoading(false);
      }
    };

    fetchData();
  }, []);

  // Display stock data when info and val are loaded, regardless of predictions
  const isDataLoading = infoLoading || valLoading;

  if (isDataLoading) {
    return <div className="vt-engraved text-center py-4 whitespace-pre-line">{"美股数据刷新偏慢，请耐心等待，如数据不全，请再次刷新\n加载中…"}</div>;
  }

  return (
    <PresetTable
      stocks={US_PRESET_STOCKS as unknown as Array<{ symbol: string; name: string }>}
      infoMap={infoMap}
      valMap={valMap}
      predictions={predictions}
    />
  );
}

export function HKPresetList() {
  const [infoMap, setInfoMap] = useState<Record<string, StockInfo>>({});
  const [valMap, setValMap] = useState<Record<string, any>>({});
  const [infoLoading, setInfoLoading] = useState(true);
  const [valLoading, setValLoading] = useState(true);
  const [predLoading, setPredLoading] = useState(true);
  const [predictions, setPredictions] = useState<Record<string, TrendPrediction>>({});
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    const fetchData = async () => {
      try {
        const symbols = HK_PRESET_STOCKS.map((s) => s.symbol).join(",");

        const infoRes = await fetch(`${API_BASE}/api/stock/batch/info?symbols=${symbols}`);
        const valRes = await fetch(`${API_BASE}/api/stock/batch/valuation?symbols=${symbols}&days=30`);

        // Process info data
        if (infoRes.ok) {
          const infoData = await infoRes.json();
          const iMap: Record<string, any> = {};
          for (const item of infoData.results || []) {
            iMap[item.symbol] = item;
          }
          for (const err of infoData.errors || []) {
            console.warn(`Failed to fetch info for ${err.symbol}:`, err.error);
          }
          setInfoMap(iMap);
        }
        setInfoLoading(false);

        // Process valuation data
        if (valRes.ok) {
          const valData = await valRes.json();
          const vMap: Record<string, any> = {};
          for (const item of valData.results || []) {
            vMap[item.symbol] = item;
          }
          for (const err of valData.errors || []) {
            console.warn(`Failed to fetch valuation for ${err.symbol}:`, err.error);
          }
          setValMap(vMap);
        }
        setValLoading(false);

        // Fetch predictions with timeout (non-blocking)
        setPredLoading(true);
        const predRes = await fetchWithTimeout(getTrendPredictions(), 5000);
        if (predRes) {
          const predMap: Record<string, TrendPrediction> = {};
          for (const pred of predRes) {
            predMap[pred.symbol] = pred;
          }
          setPredictions(predMap);
        }
        setPredLoading(false);
      } catch (err) {
        console.error("Failed to fetch HK preset stocks:", err);
        setInfoLoading(false);
        setValLoading(false);
        setPredLoading(false);
      }
    };

    fetchData();
  }, []);

  // Display stock data when info and val are loaded, regardless of predictions
  const isDataLoading = infoLoading || valLoading;

  if (isDataLoading) {
    return <div className="vt-engraved text-center py-4">加载中…</div>;
  }

  return (
    <PresetTable
      stocks={HK_PRESET_STOCKS as unknown as Array<{ symbol: string; name: string }>}
      infoMap={infoMap}
      valMap={valMap}
      predictions={predictions}
    />
  );
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
