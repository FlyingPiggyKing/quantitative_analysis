"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import StockChart from "@/components/StockChart";
import IndicatorPanel from "@/components/IndicatorPanel";
import FinancialIndicatorsPanel from "@/components/FinancialIndicatorsPanel";
import CompanyInfoPanel from "@/components/CompanyInfoPanel";
import MainBusinessPanel from "@/components/MainBusinessPanel";
import ShareholdersPanel from "@/components/ShareholdersPanel";
import TrendAnalysisPanel from "@/components/TrendAnalysisPanel";
import PETrendSparkline from "@/components/PETrendSparkline";
import MoneyFlowSparkline from "@/components/MoneyFlowSparkline";
import AuthModal from "@/components/AuthModal";
import { checkWatchlist, addToWatchlist, removeFromWatchlist } from "@/services/watchlist";
import { getTrendPrediction, TrendPrediction, runForcedSingleAnalysis, runForcedSingleAnalysisAsync, pollTaskStatus, getCooldownEndTime, setCooldownEndTime, clearCooldownEndTime } from "@/services/trendPrediction";
import { fetchStockValuation, ValuationRecord } from "@/services/stock";
import { getCompanyInfo, CompanyInfo } from "@/services/companyInfo";
import { getMainBusiness, getMainBusinessHistory, getFutuMainBusiness, getFutuMainBusinessHistory, MainBusinessResponse, MainBusinessHistoryResponse, FutuMainBusinessResponse, FutuMainBusinessHistoryResponse } from "@/services/mainBusiness";
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
  const [fundamentals, setFundamentals] = useState<{ data: Record<string, unknown> | null; error: string | null } | null>(null);
  const [fundamentalsLoading, setFundamentalsLoading] = useState(false);
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo | null>(null);
  const [companyInfoLoading, setCompanyInfoLoading] = useState(false);
  const [companyInfoError, setCompanyInfoError] = useState<string | null>(null);

  // Main business composition: 4 parallel data sources (P, D, I, history) — each with its own
  // loading state so the section skeletons render independently.
  const [mainBizProduct, setMainBizProduct] = useState<MainBusinessResponse | null>(null);
  const [mainBizRegion, setMainBizRegion] = useState<MainBusinessResponse | null>(null);
  const [mainBizIndustry, setMainBizIndustry] = useState<MainBusinessResponse | null>(null);
  const [mainBizHistory, setMainBizHistory] = useState<MainBusinessHistoryResponse | null>(null);

  // HK / US main business composition (Futu). All four dimensions come in one
  // payload (product / region / industry / business), so we cache the whole
  // response and re-use it for the section sub-props.
  const [futuMainBiz, setFutuMainBiz] = useState<FutuMainBusinessResponse | null>(null);
  const [futuMainBizHistory, setFutuMainBizHistory] = useState<FutuMainBusinessHistoryResponse | null>(null);
  const [futuMainBizLoading, setFutuMainBizLoading] = useState({ p: false, h: false });
  const [futuMainBizError, setFutuMainBizError] = useState<string | null>(null);
  const [mainBizLoading, setMainBizLoading] = useState({ p: false, d: false, i: false, h: false });
  const [mainBizError, setMainBizError] = useState<string | null>(null);
  const [hasDistinctIndustry, setHasDistinctIndustry] = useState(false);

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

  // Fetch financial fundamentals (A-share only, non-blocking)
  useEffect(() => {
    if (!symbol) return;
    // Only fetch for A-share stocks (6-digit symbols)
    if (!/^\d{6}$/.test(symbol)) return;

    const fetchFundamentals = async () => {
      setFundamentalsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/stock/${symbol}/fundamentals`);
        const data = await res.json();
        if (data.error) {
          setFundamentals({ data: null, error: data.error });
        } else if (data.data) {
          setFundamentals({ data: data.data, error: null });
        } else {
          setFundamentals({ data: null, error: "暂无数据" });
        }
      } catch (err) {
        console.error("Failed to fetch fundamentals:", err);
        setFundamentals({ data: null, error: "数据加载失败" });
      } finally {
        setFundamentalsLoading(false);
      }
    };

    fetchFundamentals();
  }, [symbol]);

  // Fetch company basic info for all markets (A-share, HK, US). The panel
  // branches on `data.market` to pick the layout — A-share gets the Tushare
  // schema, HK/US gets the Futu profile_labels + executives schema.
  useEffect(() => {
    if (!symbol) return;

    const fetchCompany = async () => {
      setCompanyInfoLoading(true);
      setCompanyInfoError(null);
      try {
        const res = await getCompanyInfo(symbol);
        if (res.error) {
          setCompanyInfo(null);
          setCompanyInfoError(res.error);
        } else {
          setCompanyInfo(res.data);
        }
      } catch (err) {
        console.error("Failed to fetch company info:", err);
        setCompanyInfo(null);
        setCompanyInfoError("数据加载失败");
      } finally {
        setCompanyInfoLoading(false);
      }
    };

    fetchCompany();
  }, [symbol]);

  // Fetch HK / US main business composition via Futu
  // `get_financials_revenue_breakdown` (proto 3228). Two parallel calls:
  // one for the latest-period payload (all 4 dimensions) and one for the
  // 4-year cross-period history. Skipped for A-share (6-digit) symbols.
  useEffect(() => {
    if (!symbol) return;
    // Only HK (4-5 digit / HK.XXXXX) and US (1-5 letters / US.XXXXX) symbols.
    const isHk = /^(\d{4,5}|HK\.\d{4,5})$/.test(symbol);
    const isUs = /^([A-Z]{1,5}|US\.[A-Z]{1,5})$/.test(symbol);
    if (!isHk && !isUs) return;

    let cancelled = false;
    setFutuMainBizError(null);
    setFutuMainBiz(null);
    setFutuMainBizHistory(null);
    setFutuMainBizLoading({ p: true, h: true });

    const run = async () => {
      const [latest, history] = await Promise.all([
        getFutuMainBusiness(symbol),
        getFutuMainBusinessHistory(symbol, 4),
      ]);
      if (cancelled) return;
      if (latest === null && history === null) {
        setFutuMainBizError("数据加载失败，请稍后重试");
      }
      setFutuMainBiz(latest);
      setFutuMainBizHistory(history);
      setFutuMainBizLoading({ p: false, h: false });
    };

    run().catch((err) => {
      console.error("[MainBiz-Futu] fetch failed:", err);
      if (!cancelled) {
        setFutuMainBizError("数据加载失败，请稍后重试");
        setFutuMainBizLoading({ p: false, h: false });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [symbol]);

  // Fetch main business composition (A-share only, non-blocking).
  // 4 parallel calls (P / D / I / history); each with its own loading state.
  useEffect(() => {
    if (!symbol) return;
    if (!/^\d{6}$/.test(symbol)) return;

    let cancelled = false;
    setMainBizError(null);
    setMainBizProduct(null);
    setMainBizRegion(null);
    setMainBizIndustry(null);
    setMainBizHistory(null);
    setHasDistinctIndustry(false);

    const fetchOne = async <T,>(
      type: "p" | "d" | "i" | "h",
      fn: () => Promise<T>,
      setter: (v: T) => void,
    ) => {
      setMainBizLoading((s) => ({ ...s, [type]: true }));
      try {
        const data = await fn();
        if (!cancelled) setter(data);
      } catch (err) {
        console.error(`[MainBiz] ${type} fetch failed:`, err);
        if (!cancelled && type === "p") {
          // Surface a single error on the panel; the rest stay null and render skeletons.
          setMainBizError("数据加载失败，请稍后重试");
        }
      } finally {
        if (!cancelled) setMainBizLoading((s) => ({ ...s, [type]: false }));
      }
    };

    fetchOne("p", () => getMainBusiness(symbol, "P"), setMainBizProduct);
    fetchOne("d", () => getMainBusiness(symbol, "D"), setMainBizRegion);
    fetchOne("i", () => getMainBusiness(symbol, "I"), setMainBizIndustry);
    fetchOne("h", () => getMainBusinessHistory(symbol, "P", 3), setMainBizHistory);

    return () => {
      cancelled = true;
    };
  }, [symbol]);

  // Compute hasDistinctIndustry client-side: true if any I row's item is not in P.
  useEffect(() => {
    if (!mainBizProduct || !mainBizIndustry) return;
    const productItems = new Set(mainBizProduct.rows.map((r) => r.item));
    const industryItems = new Set(mainBizIndustry.rows.map((r) => r.item));
    setHasDistinctIndustry(industryItems.size > 0 && ![...industryItems].every((i) => productItems.has(i)));
  }, [mainBizProduct, mainBizIndustry]);

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

    const userId = String(user.id);
    const storedEndTime = getCooldownEndTime(userId, symbol);
    console.log("[Cooldown] Loading cooldown:", { userId, symbol, storedEndTime, now: Date.now() });
    if (storedEndTime && storedEndTime > Date.now()) {
      console.log("[Cooldown] Setting active cooldown, ends at:", storedEndTime);
      setCooldownEndTimeState(storedEndTime);
    } else if (storedEndTime && storedEndTime <= Date.now()) {
      // Cooldown expired, clear it
      console.log("[Cooldown] Cooldown expired, clearing");
      clearCooldownEndTime(String(user.id), symbol);
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
      // Set cooldown immediately when user clicks (before API call)
      // This ensures cooldown is active even if user refreshes page during analysis
      if (user) {
        const endTime = Date.now() + 60 * 60 * 1000;
        console.log("[Cooldown] Setting cooldown immediately on click:", { userId: String(user.id), symbol, endTime });
        setCooldownEndTime(String(user.id), symbol, endTime);
        setCooldownEndTimeState(endTime);
      }

      // Submit to background queue and get task_id
      const { task_id } = await runForcedSingleAnalysisAsync(symbol);

      // Poll for task completion
      const finalStatus = await pollTaskStatus(task_id);

      if (finalStatus.status === "completed" && finalStatus.results && finalStatus.results.length > 0) {
        setTrendPrediction(finalStatus.results[0]);
      } else if (finalStatus.status === "failed") {
        // Analysis failed, but cooldown was already set on click
        // User will need to wait for cooldown to expire
        setAnalysisError(finalStatus.error || "分析失败");
      }
    } catch (err) {
      console.error("Failed to run analysis:", err);
      const error = err as Error & { retryAfter?: number };
      if (error.retryAfter) {
        // 429 Rate limit - user is already in cooldown from previous analysis
        // Keep the cooldown we set on click, just show error message
        setAnalysisError(`操作过于频繁，请在 ${error.retryAfter} 秒后重试`);
      } else {
        // Network error or other failure - clear cooldown so user can retry
        if (user) {
          clearCooldownEndTime(String(user.id), symbol);
          setCooldownEndTimeState(null);
        }
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
          <div className="flex items-stretch justify-between gap-3">
            {/* Left: back link on top, name/code at bottom */}
            <div className="flex flex-col justify-between gap-2 min-w-0 flex-1">
              <Link href="/" className="vt-engraved not-italic text-vt-parchment-dim hover:text-vt-brass-300 active:scale-95 transition-all self-start">
                ← 返回
              </Link>
              <div className="min-w-0">
                <h1 className="vt-emboss text-2xl sm:text-3xl truncate leading-tight">
                  {stockInfo?.name || symbol}{" "}
                  <span className="text-vt-brass-400 font-[var(--font-geist-mono)] text-xl sm:text-2xl tracking-widest" style={{ WebkitTextFillColor: "currentColor", background: "none" }}>
                    ({symbol})
                  </span>
                </h1>
                {stockInfo?.sector && stockInfo.sector !== "未知" && (
                  <p className="vt-engraved text-xs sm:text-sm hidden sm:block">{stockInfo.sector}</p>
                )}
              </div>
            </div>

            {/* Right: watchlist button on top, price at bottom */}
            <div className="flex flex-col justify-between items-end gap-2 shrink-0">
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
              {klineData.length > 0 && (
                <div className="flex items-baseline gap-2 justify-end">
                  <div
                    className="text-2xl sm:text-3xl font-[var(--font-playfair)] font-bold text-vt-parchment leading-none"
                    style={{ textShadow: "0 1px 0 rgba(241,214,138,0.18), 0 2px 4px rgba(0,0,0,0.6)" }}
                  >
                    {latestPrice.toFixed(2)}
                  </div>
                  <div
                    className={`text-sm sm:text-base font-[var(--font-geist-mono)] font-bold tracking-wide leading-none ${
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
          </div>
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

        {/* Financial Indicators - A-share only */}
        {/^\d{6}$/.test(symbol) && (
          <section className="vt-panel p-3 sm:p-4">
            <FinancialIndicatorsPanel
              data={fundamentals?.data ?? null}
              error={fundamentals?.error ?? null}
              loading={fundamentalsLoading}
            />
          </section>
        )}

        {/* Company info panel — renders for all markets. Panel branches on
            `data.market`: A-share gets Tushare fields, HK/US gets Futu fields.
            The trailing "近期行情" quotes table was redundant with the K-line
            chart and is removed for all markets. */}
        <CompanyInfoPanel
          data={companyInfo}
          loading={companyInfoLoading}
          error={companyInfoError}
        />

        {/* Main business composition — renders for all markets. The panel
            branches on the `market` prop: A-share uses Tushare fina_mainbz
            (full columns: 毛利率 / 利润占比 / 跨期对比 YoY), HK and US use
            Futu get_financials_revenue_breakdown (revenue-only columns). */}
        <MainBusinessPanel
          market={
            /^\d{6}$/.test(symbol)
              ? "A"
              : companyInfo?.market === "HK"
              ? "HK"
              : companyInfo?.market === "US"
              ? "US"
              : "A"
          }
          product={mainBizProduct}
          region={mainBizRegion}
          industry={mainBizIndustry}
          history={mainBizHistory}
          loading={mainBizLoading}
          error={mainBizError}
          hasDistinctIndustry={hasDistinctIndustry}
          futuProduct={futuMainBiz}
          futuRegion={futuMainBiz}
          futuIndustry={futuMainBiz}
          futuBusiness={futuMainBiz}
          futuHistory={futuMainBizHistory}
          futuLoading={futuMainBizLoading}
          futuError={futuMainBizError}
        />

        {/* Shareholder research — rendered for HK and US markets only. A-share
            (6-digit) pages skip this section entirely; no fetches fire. */}
        {(companyInfo?.market === "HK" || companyInfo?.market === "US") && (
          <ShareholdersPanel
            market={companyInfo?.market as "HK" | "US"}
            symbol={symbol}
          />
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
