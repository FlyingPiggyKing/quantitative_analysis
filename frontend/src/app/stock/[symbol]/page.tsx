"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import StockChart from "@/components/StockChart";
import IndicatorPanel from "@/components/IndicatorPanel";
import TrendAnalysisPanel from "@/components/TrendAnalysisPanel";
import PETrendSparkline from "@/components/PETrendSparkline";
import MoneyFlowSparkline from "@/components/MoneyFlowSparkline";
import AuthModal from "@/components/AuthModal";
import { checkWatchlist, addToWatchlist, removeFromWatchlist } from "@/services/watchlist";
import { getTrendPrediction, TrendPrediction, runForcedSingleAnalysis, getCooldownEndTime, setCooldownEndTime } from "@/services/trendPrediction";
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

interface MoneyFlowRecord {
  date: string;
  flow: number | null;
  net_5d_total?: number | null;
}

interface MoneyFlowResponse {
  symbol: string;
  market: string;
  data?: Array<{ trade_date?: string; date?: string; buy_lg_amount?: number; main_in_flow?: number }>;
  net_5d_total?: number | null;
  error?: string;
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
  const [moneyFlowHistory, setMoneyFlowHistory] = useState<MoneyFlowRecord[]>([]);
  const [moneyFlowLoading, setMoneyFlowLoading] = useState(false);
  const [moneyFlowMarket, setMoneyFlowMarket] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [trendPrediction, setTrendPrediction] = useState<TrendPrediction | null>(null);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [cooldownEndTime, setCooldownEndTimeState] = useState<number | null>(null);
  const [cooldownRemaining, setCooldownRemaining] = useState<string | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authModalMessage, setAuthModalMessage] = useState("");

  // Allow guest access - no redirect to login

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
            : infoData.error.includes("Rate limited")
            ? `数据源请求过于频繁，请稍后再试`
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

  // Fetch money flow data (non-blocking, separate from main data load)
  useEffect(() => {
    if (!symbol) return;

    const fetchMoneyFlow = async () => {
      setMoneyFlowLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/stock/${symbol}/moneyflow?days=30`);
        const data: MoneyFlowResponse = await res.json();
        if (!data.error && data.data) {
          // Determine flow field based on market
          const flowField = data.market === "A-share" ? "buy_lg_amount" : "main_in_flow";
          setMoneyFlowMarket(data.market);
          setMoneyFlowHistory(
            data.data.map((r) => ({
              date: r.trade_date || r.date || "",
              flow: (r[flowField] as number) ?? null,
              net_5d_total: data.net_5d_total ?? null,
            }))
          );
        }
      } catch (err) {
        console.error("Failed to fetch money flow:", err);
      } finally {
        setMoneyFlowLoading(false);
      }
    };

    fetchMoneyFlow();
  }, [symbol]);

  // Fetch existing trend prediction (non-force, just to display cached data)
  useEffect(() => {
    if (!symbol) return;

    const fetchTrend = async () => {
      try {
        const pred = await getTrendPrediction(symbol);
        if (pred) {
          setTrendPrediction(pred);
        }
      } catch (err) {
        console.error("Failed to fetch trend:", err);
      }
    };

    fetchTrend();
  }, [symbol]);

  // Check watchlist status (only for authenticated users)
  useEffect(() => {
    if (!symbol || !stockInfo || !user) return;

    const checkStatus = async () => {
      try {
        const result = await checkWatchlist(symbol);
        setIsInWatchlist(result !== null);
      } catch (err) {
        console.error("Failed to check watchlist:", err);
      }
    };

    checkStatus();
  }, [symbol, stockInfo, user]);

  // Initialize cooldown state from localStorage
  useEffect(() => {
    if (!symbol || !user) return;

    const storedEndTime = getCooldownEndTime(String(user.id), symbol);
    if (storedEndTime && storedEndTime > Date.now()) {
      setCooldownEndTimeState(storedEndTime);
    } else if (storedEndTime && storedEndTime <= Date.now()) {
      // Cooldown expired, clear it
      setCooldownEndTime(String(user.id), symbol, 0);
    }
  }, [symbol, user]);

  // Update countdown every second when cooldown is active
  useEffect(() => {
    if (!cooldownEndTime) {
      setCooldownRemaining(null);
      return;
    }

    const updateCountdown = () => {
      const remaining = cooldownEndTime - Date.now();
      if (remaining <= 0) {
        setCooldownRemaining(null);
        setCooldownEndTimeState(null);
        return;
      }
      const minutes = Math.floor(remaining / 60000);
      const seconds = Math.floor((remaining % 60000) / 1000);
      setCooldownRemaining(`${minutes}:${seconds.toString().padStart(2, "0")}`);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [cooldownEndTime]);

  const handleWatchlistToggle = async () => {
    if (!stockInfo) return;

    // Show auth modal for guests
    if (!user) {
      setAuthModalMessage("登录后即可添加自选股");
      setShowAuthModal(true);
      return;
    }

    setWatchlistLoading(true);
    try {
      if (isInWatchlist) {
        await removeFromWatchlist(symbol);
        setIsInWatchlist(false);
      } else {
        await addToWatchlist(symbol, stockInfo.name || symbol, stockInfo.market as "A" | "US" || "A");
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
    // Show auth modal for guests
    if (!user) {
      setAuthModalMessage("登录后即可使用趋势分析功能");
      setShowAuthModal(true);
      return;
    }

    setAnalysisRunning(true);
    setAnalysisError(null);
    try {
      const result = await runForcedSingleAnalysis(symbol);
      setTrendPrediction(result);
      // Set cooldown for 1 hour after successful trigger
      if (user) {
        const endTime = Date.now() + 60 * 60 * 1000;
        setCooldownEndTime(String(user.id), symbol, endTime);
        setCooldownEndTimeState(endTime);
      }
    } catch (err) {
      console.error("Failed to run analysis:", err);
      const error = err as Error & { retryAfter?: number };
      if (error.retryAfter) {
        // Handle rate limit error
        const endTime = Date.now() + error.retryAfter * 1000;
        if (user) {
          setCooldownEndTime(String(user.id), symbol, endTime);
          setCooldownEndTimeState(endTime);
        }
        setAnalysisError(`操作过于频繁，请在 ${error.retryAfter} 秒后重试`);
      } else {
        setAnalysisError(err instanceof Error ? err.message : "分析失败");
      }
    } finally {
      setAnalysisRunning(false);
    }
  };

  // Determine if US stock based on symbol pattern
  const isUSStock = !symbol.match(/^\d{6}$/);
  const loadingMessage = isUSStock
    ? "美股数据刷新偏慢，请耐心等待，如数据不全，请再次刷新\n加载中..."
    : "加载中...";

  if (loading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="vt-engraved text-lg whitespace-pre-line text-center">{loadingMessage}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <div className="text-vt-oxblood-400 text-lg mb-4 font-[var(--font-playfair)] italic tracking-wide">{error}</div>
        <Link href="/" className="vt-btn-secondary px-5 py-2 text-xs">
          返 回 首 页
        </Link>
      </div>
    );
  }

  const latestPrice = klineData.length > 0 ? klineData[klineData.length - 1].close : 0;
  const latestChange = klineData.length > 0 ? klineData[klineData.length - 1].change_pct || 0 : 0;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header
        className="px-4 py-3 sm:py-4 border-b"
        style={{
          background:
            "linear-gradient(180deg, rgba(34,28,20,0.95) 0%, rgba(20,17,13,0.95) 100%)",
          borderBottomColor: "var(--vt-brass-700)",
          boxShadow:
            "inset 0 1px 0 rgba(241,214,138,0.08), 0 4px 12px rgba(0,0,0,0.5)",
        }}
      >
        <div className="max-w-6xl mx-auto">
          {/* Back link and title row */}
          <div className="flex items-center gap-3 mb-3">
            <Link href="/" className="vt-engraved not-italic text-vt-parchment-dim hover:text-vt-brass-300 active:scale-95 transition-all">
              ← 返回
            </Link>
            <div className="flex-1 min-w-0">
              <h1 className="vt-emboss text-2xl sm:text-3xl truncate leading-tight">
                {stockInfo?.name || symbol}{" "}
                <span className="text-vt-brass-400 font-[var(--font-geist-mono)] text-xl sm:text-2xl tracking-widest" style={{ WebkitTextFillColor: "currentColor", background: "none" }}>
                  ({symbol})
                </span>
              </h1>
              {stockInfo?.sector && (
                <p className="vt-engraved text-xs sm:text-sm hidden sm:block">{stockInfo.sector}</p>
              )}
            </div>
            <button
              onClick={handleWatchlistToggle}
              disabled={watchlistLoading}
              className={`px-4 py-2 text-xs disabled:opacity-50 min-h-[44px] min-w-[44px] flex items-center justify-center ${
                isInWatchlist ? "vt-btn-secondary" : "vt-btn-primary"
              }`}
              style={isInWatchlist ? { color: "var(--vt-oxblood-400)" } : undefined}
            >
              {watchlistLoading
                ? "…"
                : isInWatchlist
                ? "移 除"
                : "自 选"}
            </button>
          </div>

          {/* Price row */}
          {klineData.length > 0 && (
            <div className="flex items-baseline gap-3">
              <div
                className="text-3xl sm:text-4xl font-[var(--font-playfair)] font-bold text-vt-parchment"
                style={{ textShadow: "0 1px 0 rgba(241,214,138,0.18), 0 2px 4px rgba(0,0,0,0.6)" }}
              >
                {latestPrice.toFixed(2)}
              </div>
              <div
                className={`text-base sm:text-lg font-[var(--font-geist-mono)] font-bold tracking-wide ${
                  latestChange >= 0 ? "text-vt-oxblood-400" : "text-vt-emerald-400"
                }`}
                style={{ textShadow: "0 0 8px currentColor, 0 1px 0 rgba(0,0,0,0.6)" }}
              >
                {latestChange >= 0 ? "+" : ""}
                {latestChange.toFixed(2)}%
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-3 sm:px-4 py-4 sm:py-6 space-y-4 sm:space-y-6">
        {/* Chart + Indicators */}
        <section className="vt-panel p-3 sm:p-4">
          <div className="flex items-center justify-between lg:justify-start gap-2 lg:gap-5 mb-3 sm:mb-4">
            <h2 className="font-[var(--font-playfair)] text-base sm:text-lg tracking-[0.18em] text-vt-parchment uppercase shrink-0">
              <span className="text-vt-brass-400">❖</span> K 线 图
            </h2>
            {valuation && (
              <div className="flex flex-wrap lg:flex-nowrap justify-end lg:justify-start items-center gap-x-3 gap-y-1 sm:gap-x-4 lg:gap-x-5 text-xs">
                <div className="flex items-center gap-1">
                  <span className="vt-prediction-label" style={{ fontSize: "0.6rem" }}>PE</span>
                  <span className="text-vt-parchment font-[var(--font-geist-mono)] font-medium">
                    {valuation.pe_ttm != null ? valuation.pe_ttm.toFixed(2) : "N/A"}
                  </span>
                  <PETrendSparkline
                    peHistory={valuationHistory.map((v) => ({ date: v.trade_date, pe: v.pe_ttm }))}
                    loading={false}
                    mobile
                  />
                </div>
                <div className="flex items-center gap-1">
                  <span className="vt-prediction-label" style={{ fontSize: "0.6rem" }}>主力(5日)</span>
                  {moneyFlowHistory.length > 0 && moneyFlowHistory[0].net_5d_total != null ? (
                    <span
                      className={`font-[var(--font-geist-mono)] font-medium ${
                        moneyFlowHistory[0].net_5d_total! >= 0 ? "text-vt-oxblood-400" : "text-vt-emerald-400"
                      }`}
                    >
                      {moneyFlowHistory[0].net_5d_total! >= 0 ? "+" : "-"}
                      {moneyFlowMarket === "A-share"
                        ? (Math.abs(moneyFlowHistory[0].net_5d_total!) / 10000).toFixed(2)
                        : (Math.abs(moneyFlowHistory[0].net_5d_total!) / 1e8).toFixed(2)}
                      {moneyFlowMarket === "HK" ? "亿HKD" : moneyFlowMarket === "US" ? "亿USD" : "亿"}
                    </span>
                  ) : (
                    <span className="text-vt-parchment font-[var(--font-geist-mono)] font-medium">
                      {moneyFlowLoading ? "..." : "N/A"}
                    </span>
                  )}
                  <MoneyFlowSparkline
                    flowHistory={moneyFlowHistory}
                    loading={moneyFlowLoading}
                    mobile
                  />
                </div>
                <div className="flex items-center gap-1">
                  <span className="vt-prediction-label" style={{ fontSize: "0.6rem" }}>PB</span>
                  <span className="text-vt-parchment font-[var(--font-geist-mono)] font-medium">
                    {valuation.pb != null ? valuation.pb.toFixed(2) : "N/A"}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="vt-prediction-label" style={{ fontSize: "0.6rem" }}>换手</span>
                  <span className="text-vt-parchment font-[var(--font-geist-mono)] font-medium">
                    {valuation.turnover_rate != null
                      ? /^\d{6}$/.test(symbol)
                        ? `${valuation.turnover_rate.toFixed(2)}%`
                        : `${(valuation.turnover_rate * 100).toFixed(2)}%`
                      : "N/A"}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="vt-prediction-label" style={{ fontSize: "0.6rem" }}>市值</span>
                  <span className="text-vt-parchment font-[var(--font-geist-mono)] font-medium">
                    {valuation.total_mv != null
                      ? /^\d{6}$/.test(symbol)
                        ? `${(valuation.total_mv / 10000).toFixed(0)}亿`
                        : /^\d{4,5}$/.test(symbol)
                        ? `${(valuation.total_mv / 1e8).toFixed(0)}亿HKD`
                        : `${(valuation.total_mv / 1e8).toFixed(0)}亿美元`
                      : "N/A"}
                  </span>
                </div>
              </div>
            )}
          </div>
          {klineData.length > 0 ? (
            <StockChart
              data={klineData}
              peData={valuationHistory.map((v) => ({ date: v.trade_date, value: v.pe_ttm }))}
              pbData={valuationHistory.map((v) => ({ date: v.trade_date, value: v.pb }))}
            />
          ) : (
            <div className="h-[250px] sm:h-[400px] flex items-center justify-center vt-engraved">
              暂无数据
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-vt-brass-500/20">
            <IndicatorPanel indicators={indicators} loading={false} />
          </div>
        </section>

        {/* Trend Analysis */}
        <section className="vt-panel relative p-3 sm:p-4 vt-ornament-tl vt-ornament-tr vt-ornament-bl vt-ornament-br">
          <div className="flex items-center mb-4">
            <h2 className="vt-pred-col-header text-base sm:text-lg" style={{ fontSize: "1rem", letterSpacing: "0.22em" }}>
              AI 趋 势 分 析
            </h2>
          </div>

          {/* Force Analysis button - top right corner */}
          <button
            onClick={handleRunAnalysis}
            disabled={analysisRunning || cooldownRemaining !== null}
            className="vt-btn-primary absolute top-3 right-3 sm:top-4 sm:right-4 px-3 py-2 sm:px-4 sm:py-2 text-xs disabled:opacity-50 min-h-[44px]"
          >
            {analysisRunning ? "分 析 中…" : cooldownRemaining ? `剩余 ${cooldownRemaining}` : "立 刻 分 析"}
          </button>

          {analysisRunning ? (
            <div className="vt-engraved text-center py-6">
              <div className="vt-pulse inline-block px-4 py-2 rounded">分析进行中，请稍候…</div>
            </div>
          ) : analysisError ? (
            <div className="text-vt-oxblood-400 font-[var(--font-playfair)] italic tracking-wide text-center py-4">
              {analysisError}
            </div>
          ) : trendPrediction ? (
            <div className="space-y-4">
              {/* HERO Prediction display - large and eye-catching */}
              <div
                className="flex flex-wrap items-center justify-center gap-4 sm:gap-8 py-5 px-3 rounded-md"
                style={{
                  background:
                    "radial-gradient(ellipse at center, rgba(200,156,58,0.10) 0%, rgba(0,0,0,0) 65%)",
                  borderTop: "1px solid rgba(200,156,58,0.25)",
                  borderBottom: "1px solid rgba(200,156,58,0.25)",
                }}
              >
                <div className="flex flex-col items-center gap-1">
                  <span className="vt-prediction-label">预 测 方 向</span>
                  <TrendDirectionBadge direction={trendPrediction.trend_direction} />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="vt-prediction-label">置 信 度</span>
                  <span
                    className="font-[var(--font-playfair)] font-extrabold text-3xl sm:text-4xl text-vt-brass-300"
                    style={{
                      textShadow:
                        "0 0 12px rgba(229,193,99,0.55), 0 1px 0 rgba(0,0,0,0.6), 0 -1px 0 rgba(255,220,140,0.15)",
                      letterSpacing: "0.02em",
                    }}
                  >
                    {trendPrediction.confidence}
                    <span className="text-xl sm:text-2xl text-vt-brass-400 ml-1">%</span>
                  </span>
                </div>
              </div>

              {/* Use extended analysis panel if available */}
              {(trendPrediction.情绪分析 || trendPrediction.技术分析 || trendPrediction.趋势判断) ? (
                <TrendAnalysisPanel prediction={trendPrediction} />
              ) : (
                <div>
                  <p className="vt-prediction-label mb-2">分 析 摘 要</p>
                  <p className="text-vt-parchment text-sm leading-relaxed">{trendPrediction.summary}</p>
                </div>
              )}

              <div className="vt-engraved text-xs">
                分析时间: {new Date(trendPrediction.analyzed_at).toLocaleString("zh-CN")}
              </div>
            </div>
          ) : (
            <div className="vt-engraved text-center py-4">
              暂无分析数据
            </div>
          )}
        </section>

        {/* Data Table */}
        {klineData.length > 0 && (
          <section className="vt-panel p-3 sm:p-4">
            <h2 className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-parchment uppercase mb-4">
              <span className="text-vt-brass-400">❖</span> 近 期 行 情
            </h2>
            <div className="overflow-x-auto -mx-3 sm:mx-0 px-3 sm:px-0">
              <table className="w-full text-sm min-w-[600px] sm:min-w-0">
                <thead>
                  <tr className="border-b border-vt-ink-700">
                    <th className="text-left py-2 px-3 vt-tab text-xs">日期</th>
                    <th className="text-right py-2 px-3 vt-tab text-xs">开盘</th>
                    <th className="text-right py-2 px-3 vt-tab text-xs">收盘</th>
                    <th className="text-right py-2 px-3 vt-tab text-xs">最高</th>
                    <th className="text-right py-2 px-3 vt-tab text-xs">最低</th>
                    <th className="text-right py-2 px-3 vt-tab text-xs">成交量</th>
                    <th className="text-right py-2 px-3 vt-tab text-xs">涨跌幅</th>
                  </tr>
                </thead>
                <tbody>
                  {klineData.slice(-10).reverse().map((row, idx) => (
                    <tr key={idx} className="text-vt-parchment border-b border-vt-ink-700/60 hover:bg-vt-ink-600/30 transition-colors">
                      <td className="py-2 px-3 font-[var(--font-geist-mono)] text-vt-parchment-dim">{row.date}</td>
                      <td className="text-right py-2 px-3 font-[var(--font-geist-mono)]">{row.open.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-[var(--font-geist-mono)]">{row.close.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-[var(--font-geist-mono)]">{row.high.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-[var(--font-geist-mono)]">{row.low.toFixed(2)}</td>
                      <td className="text-right py-2 px-3 font-[var(--font-geist-mono)]">{(row.volume / 10000).toFixed(2)}万</td>
                      <td className={`text-right py-2 px-3 font-[var(--font-geist-mono)] font-bold ${row.change_pct! >= 0 ? "text-vt-oxblood-400" : "text-vt-emerald-400"}`}>
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

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        message={authModalMessage}
      />
    </div>
  );
}

function TrendDirectionBadge({ direction }: { direction: string }) {
  if (direction === "up") {
    return (
      <span
        className="vt-pred-up vt-pulse"
        style={{ fontSize: "1.5rem", padding: "0.4rem 1rem" }}
      >
        <span className="text-2xl leading-none">▲</span>
        看 涨
      </span>
    );
  } else if (direction === "down") {
    return (
      <span
        className="vt-pred-down vt-pulse"
        style={{ fontSize: "1.5rem", padding: "0.4rem 1rem" }}
      >
        <span className="text-2xl leading-none">▼</span>
        看 跌
      </span>
    );
  } else {
    return (
      <span
        className="vt-pred-flat"
        style={{ fontSize: "1.5rem", padding: "0.4rem 1rem" }}
      >
        <span className="text-2xl leading-none">◆</span>
        中 性
      </span>
    );
  }
}
