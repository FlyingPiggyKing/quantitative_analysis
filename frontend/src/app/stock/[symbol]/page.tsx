"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import StockChart from "@/components/StockChart";
import IndicatorPanel from "@/components/IndicatorPanel";

interface StockInfo {
  symbol: string;
  name?: string;
  sector?: string;
  market?: string;
  error?: string;
}

interface KLineData {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  amount?: number;
  change_pct?: number;
}

interface Indicators {
  macd: { dif: number; dea: number; hist: number };
  rsi: { rsi6: number; rsi12: number; rsi24: number };
  ma: { ma5: number; ma10: number; ma20: number; ma60: number | null };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function StockDetailPage() {
  const params = useParams();
  const symbol = params.symbol as string;

  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [klineData, setKlineData] = useState<KLineData[]>([]);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!symbol) return;

      setLoading(true);
      setError(null);

      try {
        // Fetch stock info and kline data in parallel
        const [infoRes, klineRes, indicatorsRes] = await Promise.all([
          fetch(`${API_BASE}/api/stock/${symbol}`),
          fetch(`${API_BASE}/api/stock/${symbol}/kline?days=100`),
          fetch(`${API_BASE}/api/stock/${symbol}/indicators?days=100`),
        ]);

        const infoData = await infoRes.json();
        const klineDataResult = await klineRes.json();
        const indicatorsData = await indicatorsRes.json();

        if (infoData.error) {
          const errorMsg = infoData.error.includes("Connection") || infoData.error.includes("Remote")
            ? `数据源连接失败，请稍后重试`
            : `股票 ${symbol} 未找到`;
          setError(errorMsg);
          setLoading(false);
          return;
        }

        setStockInfo(infoData);
        setKlineData(klineDataResult.data || []);
        setIndicators(indicatorsData.indicators || null);
      } catch (err) {
        setError("数据加载失败，请确保后端服务已启动");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center">
        <div className="text-red-400 text-lg mb-4">{error}</div>
        <Link href="/" className="text-blue-400 hover:text-blue-300">
          返回首页
        </Link>
      </div>
    );
  }

  const latestPrice = klineData.length > 0 ? klineData[klineData.length - 1].close : 0;
  const latestChange = klineData.length > 0 ? klineData[klineData.length - 1].change_pct || 0 : 0;

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-slate-400 hover:text-white">
              ← 返回
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white">
                {stockInfo?.name || symbol} ({symbol})
              </h1>
              {stockInfo?.sector && (
                <p className="text-slate-400 text-sm">{stockInfo.sector}</p>
              )}
            </div>
          </div>
          {klineData.length > 0 && (
            <div className="text-right">
              <div className="text-2xl font-bold text-white">{latestPrice.toFixed(2)}</div>
              <div className={`text-sm ${latestChange >= 0 ? "text-red-400" : "text-green-400"}`}>
                {latestChange >= 0 ? "+" : ""}
                {latestChange.toFixed(2)}%
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Chart */}
        <section className="bg-slate-800 rounded-lg p-4">
          <h2 className="text-lg font-medium text-white mb-4">K线图</h2>
          {klineData.length > 0 ? (
            <StockChart data={klineData} />
          ) : (
            <div className="h-[400px] flex items-center justify-center text-slate-400">
              暂无数据
            </div>
          )}
        </section>

        {/* Indicators */}
        <section>
          <h2 className="text-lg font-medium text-white mb-4">技术指标</h2>
          <IndicatorPanel indicators={indicators} loading={false} />
        </section>

        {/* Data Table */}
        {klineData.length > 0 && (
          <section className="bg-slate-800 rounded-lg p-4">
            <h2 className="text-lg font-medium text-white mb-4">近期行情</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-700">
                    <th className="text-left py-2 px-3">日期</th>
                    <th className="text-right py-2 px-3">开盘</th>
                    <th className="text-right py-2 px-3">收盘</th>
                    <th className="text-right py-2 px-3">最高</th>
                    <th className="text-right py-2 px-3">最低</th>
                    <th className="text-right py-2 px-3">成交量</th>
                    <th className="text-right py-2 px-3">涨跌幅</th>
                  </tr>
                </thead>
                <tbody>
                  {klineData.slice(-10).reverse().map((row, idx) => (
                    <tr key={idx} className="text-white border-b border-slate-700/50 hover:bg-slate-700/30">
                      <td className="py-2 px-3">{row.date}</td>
                      <td className="text-right py-2 px-3 font-mono">{row.open.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-mono">{row.close.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-mono">{row.high.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-mono">{row.low.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-mono">{(row.volume / 10000).toFixed(2)}万</td>
                      <td className={`text-right py-2 px-3 font-mono ${row.change_pct! >= 0 ? "text-red-400" : "text-green-400"}`}>
                        {row.change_pct!.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
