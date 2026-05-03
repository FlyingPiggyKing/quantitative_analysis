"use client";

import { useState, useEffect, useRef, ReactNode } from "react";
import Link from "next/link";
import { PRESET_STOCKS, US_PRESET_STOCKS } from "@/config/presetStocks";
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
        className="block bg-slate-700/50 rounded-lg p-3 min-h-[44px] active:opacity-70 transition-opacity"
      >
        <div className="flex justify-between items-start mb-2">
          <div>
            <span className="text-blue-400 font-medium">{info.symbol}</span>
            <span className="text-white ml-2">{info.name || info.symbol}</span>
          </div>
          <div className="text-right">
            <div className="text-slate-500 text-xs mb-1">AI下周走势</div>
            {prediction ? (
              <TrendIndicator prediction={prediction} />
            ) : (
              <span className="text-slate-500 text-sm">-</span>
            )}
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
    );
  }

  return (
    <tr
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
      <td className="py-2 px-3 text-right">
        {prediction ? (
          <TrendIndicator prediction={prediction} />
        ) : (
          <span className="text-slate-500">-</span>
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
            <tr className="text-slate-400 border-b border-slate-700">
              <th className="text-left py-2 px-3">股票代码</th>
              <th className="text-left py-2 px-3">股票名称</th>
              <th className="text-right py-2 px-3">市盈率(PE)</th>
              <th className="text-right py-2 px-3">市净率(PB)</th>
              <th className="text-right py-2 px-3">换手率</th>
              <th className="text-right py-2 px-3">AI下周预测</th>
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
    return <div className="text-slate-400 text-center py-4">加载中...</div>;
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
    return <div className="text-slate-400 text-center py-4">加载中...</div>;
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

export default function PresetStockList() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-white">推荐股票</h2>
        <span className="text-slate-500 text-sm">游客预览</span>
      </div>
      <StockMarketTabs
        aShareContent={<ASharePresetList />}
        usContent={<USPresetList />}
      />
    </div>
  );
}
