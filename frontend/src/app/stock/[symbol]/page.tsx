"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import StockChart from "@/components/StockChart";
import IndicatorPanel from "@/components/IndicatorPanel";
import TrendAnalysisPanel from "@/components/TrendAnalysisPanel";
import PETrendSparkline from "@/components/PETrendSparkline";
import { checkWatchlist, addToWatchlist, removeFromWatchlist } from "@/services/watchlist";
import { getTrendPrediction, TrendPrediction, runBatchAnalysisAsync, pollTaskStatus, TaskStatusResponse } from "@/services/trendPrediction";
import { fetchStockValuation, ValuationRecord } from "@/services/stock";
import { useAuth } from "@/services/auth";

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
  const router = useRouter();
  const symbol = params.symbol as string;
  const { user, isLoading } = useAuth();

  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [klineData, setKlineData] = useState<KLineData[]>([]);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [valuation, setValuation] = useState<ValuationRecord | null>(null);
  const [valuationHistory, setValuationHistory] = useState<ValuationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [trendPrediction, setTrendPrediction] = useState<TrendPrediction | null>(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [taskProgress, setTaskProgress] = useState<string | null>(null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [user, isLoading, router]);

  useEffect(() => {
    const fetchData = async () => {
      if (!symbol) return;

      setLoading(true);
      setError(null);

      try {
        // Fetch stock info, kline data, indicators, and valuation in parallel
        const [infoRes, klineRes, indicatorsRes, valuationResult] = await Promise.all([
          fetch(`${API_BASE}/api/stock/${symbol}`),
          fetch(`${API_BASE}/api/stock/${symbol}/kline?days=100`),
          fetch(`${API_BASE}/api/stock/${symbol}/indicators?days=100`),
          fetchStockValuation(symbol, 100),
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
        if (valuationResult.latest) {
          setValuation(valuationResult.latest);
        }
        if (valuationResult.data) {
          setValuationHistory(valuationResult.data);
        }
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

  if (loading || isLoading) {
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
      <header className="bg-slate-800 border-b border-slate-700 px-4 py-3 sm:py-4">
        <div className="max-w-6xl mx-auto">
          {/* Back link and title row */}
          <div className="flex items-center gap-3 mb-3">
            <Link href="/" className="text-slate-400 hover:text-white active:scale-95 transition-transform">
              ← 返回
            </Link>
            <div className="flex-1 min-w-0">
              <h1 className="text-lg sm:text-xl font-bold text-white truncate">
                {stockInfo?.name || symbol} ({symbol})
              </h1>
              {stockInfo?.sector && (
                <p className="text-slate-400 text-xs sm:text-sm hidden sm:block">{stockInfo.sector}</p>
              )}
            </div>
            <button
              onClick={handleWatchlistToggle}
              disabled={watchlistLoading}
              className={`px-3 py-2 sm:px-4 sm:py-2 rounded-lg font-medium transition-colors active:scale-95 disabled:opacity-50 min-h-[44px] min-w-[44px] flex items-center justify-center ${
                isInWatchlist
                  ? "bg-red-600 hover:bg-red-700 text-white"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              {watchlistLoading
                ? "..."
                : isInWatchlist
                ? "移除"
                : "自选"}
            </button>
          </div>

          {/* Price and valuation row - stacks on mobile */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            {klineData.length > 0 && (
              <div className="flex items-baseline gap-3">
                <div className="text-2xl sm:text-3xl font-bold text-white">{latestPrice.toFixed(2)}</div>
                <div className={`text-base sm:text-lg ${latestChange >= 0 ? "text-red-400" : "text-green-400"}`}>
                  {latestChange >= 0 ? "+" : ""}
                  {latestChange.toFixed(2)}%
                </div>
              </div>
            )}

            {valuation && (
              <div className="grid grid-cols-2 sm:flex sm:items-center gap-2 sm:gap-4 text-sm border-t sm:border-t-0 border-slate-700 pt-3 sm:pt-0">
                <div>
                  <div className="text-slate-400 text-xs">PE(TTM)</div>
                  <div className="flex items-center gap-1">
                    <span className="text-white font-medium">{valuation.pe_ttm != null ? valuation.pe_ttm.toFixed(2) : "N/A"}</span>
                    <PETrendSparkline
                      peHistory={valuationHistory.map((v) => ({ date: v.trade_date, pe: v.pe_ttm }))}
                      loading={false}
                      mobile
                    />
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-xs">PB</div>
                  <span className="text-white font-medium">{valuation.pb != null ? valuation.pb.toFixed(2) : "N/A"}</span>
                </div>
                <div>
                  <div className="text-slate-400 text-xs">换手率</div>
                  <span className="text-white font-medium">{valuation.turnover_rate != null ? `${valuation.turnover_rate.toFixed(2)}%` : "N/A"}</span>
                </div>
                <div>
                  <div className="text-slate-400 text-xs">总市值</div>
                  <span className="text-white font-medium">{valuation.total_mv != null ? `${(valuation.total_mv / 10000).toFixed(0)}亿` : "N/A"}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-3 sm:px-4 py-4 sm:py-6 space-y-4 sm:space-y-6">
        {/* Chart */}
        <section className="bg-slate-800 rounded-lg p-3 sm:p-4">
          <h2 className="text-lg font-medium text-white mb-4">K线图</h2>
          {klineData.length > 0 ? (
            <StockChart
              data={klineData}
              peData={valuationHistory.map((v) => ({ date: v.trade_date, value: v.pe_ttm }))}
              pbData={valuationHistory.map((v) => ({ date: v.trade_date, value: v.pb }))}
            />
          ) : (
            <div className="h-[250px] sm:h-[400px] flex items-center justify-center text-slate-400">
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
        <section className="bg-slate-800 rounded-lg p-3 sm:p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-white">趋势分析</h2>
            {!trendPrediction && !trendLoading && (
              <button
                onClick={handleRunAnalysis}
                disabled={analysisRunning}
                className="px-3 py-2 sm:px-4 sm:py-2 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-sm rounded-lg disabled:opacity-50 min-h-[44px]"
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

              {/* Use extended analysis panel if available */}
              {(trendPrediction.情绪分析 || trendPrediction.技术分析 || trendPrediction.趋势判断) ? (
                <TrendAnalysisPanel prediction={trendPrediction} />
              ) : (
                <div>
                  <p className="text-slate-400 text-sm mb-1">分析摘要:</p>
                  <p className="text-white text-sm">{trendPrediction.summary}</p>
                </div>
              )}

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
          <section className="bg-slate-800 rounded-lg p-3 sm:p-4">
            <h2 className="text-lg font-medium text-white mb-4">近期行情</h2>
            <div className="overflow-x-auto -mx-3 sm:mx-0 px-3 sm:px-0">
              <table className="w-full text-sm min-w-[600px] sm:min-w-0">
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
