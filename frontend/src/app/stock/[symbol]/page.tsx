"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import StockChart from "@/components/StockChart";
import IndicatorPanel from "@/components/IndicatorPanel";
import { checkWatchlist, addToWatchlist, removeFromWatchlist } from "@/services/watchlist";
import { getTrendPrediction, TrendPrediction, runBatchAnalysisAsync, pollTaskStatus, TaskStatusResponse } from "@/services/trendPrediction";

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
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [trendPrediction, setTrendPrediction] = useState<TrendPrediction | null>(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [taskProgress, setTaskProgress] = useState<string | null>(null);

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

  // Fetch trend prediction
  useEffect(() => {
    if (!symbol) return;

    const fetchTrend = async () => {
      setTrendLoading(true);
      try {
        const pred = await getTrendPrediction(symbol);
        setTrendPrediction(pred);
      } catch (err) {
        console.error("Failed to fetch trend:", err);
      } finally {
        setTrendLoading(false);
      }
    };

    fetchTrend();
  }, [symbol]);

  // Check watchlist status
  useEffect(() => {
    if (!symbol || !stockInfo) return;

    const checkStatus = async () => {
      try {
        const result = await checkWatchlist(symbol);
        setIsInWatchlist(result !== null);
      } catch (err) {
        console.error("Failed to check watchlist:", err);
      }
    };

    checkStatus();
  }, [symbol, stockInfo]);

  const handleWatchlistToggle = async () => {
    if (!stockInfo) return;

    setWatchlistLoading(true);
    try {
      if (isInWatchlist) {
        await removeFromWatchlist(symbol);
        setIsInWatchlist(false);
      } else {
        await addToWatchlist(symbol, stockInfo.name || symbol);
        setIsInWatchlist(true);
      }
    } catch (err) {
      console.error("Failed to toggle watchlist:", err);
      alert(err instanceof Error ? err.message : "操作失败");
    } finally {
      setWatchlistLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!stockInfo) return;

    setAnalysisRunning(true);
    setTaskProgress(null);
    try {
      const response = await runBatchAnalysisAsync();
      if (!response.task_id) {
        alert("没有股票需要分析");
        setAnalysisRunning(false);
        return;
      }

      // Store task ID for progress bar on index page - do this immediately
      // so user can navigate to index and see progress
      localStorage.setItem("active_analysis_task_id", response.task_id);
      localStorage.removeItem("progress_bar_dismissed");

      // Poll status and update button progress
      pollTaskStatus(
        response.task_id,
        (status: TaskStatusResponse) => {
          setTaskProgress(status.progress);
        },
        2000
      ).then(() => {
        // Refresh trend prediction after completion
        getTrendPrediction(symbol).then(setTrendPrediction);
      }).catch((err) => {
        console.error("Analysis failed:", err);
      }).finally(() => {
        // Clear running state when polling completes
        setAnalysisRunning(false);
        setTaskProgress(null);
        // Clear the stored task ID since analysis is done
        localStorage.removeItem("active_analysis_task_id");
      });
    } catch (err) {
      console.error("Failed to run analysis:", err);
      alert(err instanceof Error ? err.message : "分析失败");
      setAnalysisRunning(false);
    }
  };

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

          <div className="flex items-center gap-4">
            {klineData.length > 0 && (
              <div className="text-right">
                <div className="text-2xl font-bold text-white">{latestPrice.toFixed(2)}</div>
                <div className={`text-sm ${latestChange >= 0 ? "text-red-400" : "text-green-400"}`}>
                  {latestChange >= 0 ? "+" : ""}
                  {latestChange.toFixed(2)}%
                </div>
              </div>
            )}

            <button
              onClick={handleWatchlistToggle}
              disabled={watchlistLoading}
              className={`px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 ${
                isInWatchlist
                  ? "bg-red-600 hover:bg-red-700 text-white"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              {watchlistLoading
                ? "处理中..."
                : isInWatchlist
                ? "移除自选"
                : "加入自选"}
            </button>
          </div>
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

        {/* Trend Analysis */}
        <section className="bg-slate-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-white">趋势分析</h2>
            {!trendPrediction && !trendLoading && (
              <button
                onClick={handleRunAnalysis}
                disabled={analysisRunning}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg disabled:opacity-50"
              >
                {analysisRunning ? (taskProgress ? `分析中... ${taskProgress}` : "分析中...") : "运行分析"}
              </button>
            )}
          </div>

          {trendLoading ? (
            <div className="text-slate-400 text-center py-4">加载中...</div>
          ) : trendPrediction ? (
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 text-sm">预测方向:</span>
                  <TrendDirectionBadge direction={trendPrediction.trend_direction} />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 text-sm">置信度:</span>
                  <span className="text-white font-medium">{trendPrediction.confidence}%</span>
                </div>
              </div>
              <div>
                <p className="text-slate-400 text-sm mb-1">分析摘要:</p>
                <p className="text-white text-sm">{trendPrediction.summary}</p>
              </div>
              <div className="text-slate-500 text-xs">
                分析时间: {new Date(trendPrediction.analyzed_at).toLocaleString("zh-CN")}
              </div>
            </div>
          ) : (
            <div className="text-slate-400 text-center py-4">
              暂无分析数据
            </div>
          )}
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

function TrendDirectionBadge({ direction }: { direction: string }) {
  if (direction === "up") {
    return (
      <span className="inline-flex items-center px-2 py-1 bg-emerald-500/20 text-emerald-400 text-sm rounded">
        ↑ 上涨
      </span>
    );
  } else if (direction === "down") {
    return (
      <span className="inline-flex items-center px-2 py-1 bg-red-500/20 text-red-400 text-sm rounded">
        ↓ 下跌
      </span>
    );
  } else {
    return (
      <span className="inline-flex items-center px-2 py-1 bg-slate-500/20 text-slate-400 text-sm rounded">
        - 中性
      </span>
    );
  }
}
