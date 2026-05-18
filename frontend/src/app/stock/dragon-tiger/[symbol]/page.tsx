"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import InstitutionalAnalysisPanel from "@/components/InstitutionalAnalysisPanel";
import AuthModal from "@/components/AuthModal";
import {
  getInstitutionalPrediction,
  runInstitutionalAnalysisAsync,
  pollInstitutionalAnalysisTaskStatus,
  InstitutionalTrendPrediction,
} from "@/services/institutionalTradingAnalysis";
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
  change_pct?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DragonTigerStockDetailPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = params.symbol as string;
  const { user, isLoading } = useAuth();

  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [klineData, setKlineData] = useState<KLineData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<InstitutionalTrendPrediction | null>(null);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [cooldownEndTime, setCooldownEndTimeState] = useState<number | null>(null);
  const [cooldownRemaining, setCooldownRemaining] = useState<string | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authModalMessage, setAuthModalMessage] = useState("");

  // Fetch stock data
  useEffect(() => {
    const fetchData = async () => {
      if (!symbol) return;

      setLoading(true);
      setError(null);

      try {
        const [infoRes, klineRes] = await Promise.all([
          fetch(`${API_BASE}/api/stock/${symbol}`),
          fetch(`${API_BASE}/api/stock/${symbol}/kline?days=100`),
        ]);

        const infoData = await infoRes.json();
        const klineDataResult = await klineRes.json();

        if (infoData.error) {
          setError(`股票 ${symbol} 未找到`);
          setLoading(false);
          return;
        }

        setStockInfo(infoData);
        setKlineData(klineDataResult.data || []);
      } catch (err) {
        setError("数据加载失败，请确保后端服务已启动");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol]);

  // Fetch existing prediction
  useEffect(() => {
    if (!symbol) return;

    const fetchPrediction = async () => {
      try {
        const pred = await getInstitutionalPrediction(symbol);
        if (pred) {
          setPrediction(pred);
        }
      } catch (err) {
        console.error("Failed to fetch prediction:", err);
      }
    };

    fetchPrediction();
  }, [symbol]);

  // Initialize cooldown from localStorage
  useEffect(() => {
    if (!symbol || !user) return;

    const userId = String(user.id);
    const key = `institutional_analysis_cooldown_${userId}_${symbol}`;
    const storedEndTime = localStorage.getItem(key);
    if (storedEndTime) {
      const endTime = parseInt(storedEndTime, 10);
      if (endTime > Date.now()) {
        setCooldownEndTimeState(endTime);
      } else {
        localStorage.removeItem(key);
      }
    }
  }, [symbol, user]);

  // Update countdown
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

  const handleRunAnalysis = async () => {
    if (!user) {
      setAuthModalMessage("登录后即可使用趋势分析功能");
      setShowAuthModal(true);
      return;
    }

    setAnalysisRunning(true);
    setAnalysisError(null);

    try {
      const userId = String(user.id);
      const key = `institutional_analysis_cooldown_${userId}_${symbol}`;
      const endTime = Date.now() + 60 * 60 * 1000;
      localStorage.setItem(key, endTime.toString());
      setCooldownEndTimeState(endTime);

      const { task_id } = await runInstitutionalAnalysisAsync(symbol);
      const finalStatus = await pollInstitutionalAnalysisTaskStatus(task_id);

      if (finalStatus.status === "completed" && finalStatus.results && finalStatus.results.length > 0) {
        setPrediction(finalStatus.results[0]);
      } else if (finalStatus.status === "failed") {
        setAnalysisError(finalStatus.error || "分析失败");
      }
    } catch (err) {
      console.error("Failed to run analysis:", err);
      const error = err as Error & { retryAfter?: number };
      if (error.retryAfter) {
        setAnalysisError(`操作过于频繁，请在 ${error.retryAfter} 秒后重试`);
      } else {
        if (user) {
          const userId = String(user.id);
          const key = `institutional_analysis_cooldown_${userId}_${symbol}`;
          localStorage.removeItem(key);
          setCooldownEndTimeState(null);
        }
        setAnalysisError(err instanceof Error ? err.message : "分析失败");
      }
    } finally {
      setAnalysisRunning(false);
    }
  };

  if (loading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="vt-engraved text-lg">加载中...</div>
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
          background: "linear-gradient(180deg, rgba(34,28,20,0.95) 0%, rgba(20,17,13,0.95) 100%)",
          borderBottomColor: "var(--vt-brass-700)",
          boxShadow: "inset 0 1px 0 rgba(241,214,138,0.08), 0 4px 12px rgba(0,0,0,0.5)",
        }}
      >
        <div className="max-w-6xl mx-auto">
          <div className="flex items-stretch justify-between gap-3">
            <div className="flex flex-col justify-between gap-2 min-w-0 flex-1">
              <Link
                href="/"
                className="vt-engraved not-italic text-vt-parchment-dim hover:text-vt-brass-300 active:scale-95 transition-all self-start"
              >
                ← 返回
              </Link>
              <div className="min-w-0">
                <h1 className="vt-emboss text-2xl sm:text-3xl truncate leading-tight">
                  {stockInfo?.name || symbol}{" "}
                  <span
                    className="text-vt-brass-400 font-[var(--font-geist-mono)] text-xl sm:text-2xl tracking-widest"
                    style={{ WebkitTextFillColor: "currentColor", background: "none" }}
                  >
                    ({symbol})
                  </span>
                </h1>
                {stockInfo?.sector && stockInfo.sector !== "未知" && (
                  <p className="vt-engraved text-xs sm:text-sm hidden sm:block">{stockInfo.sector}</p>
                )}
              </div>
            </div>

            <div className="flex flex-col justify-between items-end gap-2 shrink-0">
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
        {/* AI 趋势分析 */}
        <section className="vt-panel relative p-3 sm:p-4 vt-ornament-tl vt-ornament-tr vt-ornament-bl vt-ornament-br">
          <div className="flex items-center mb-4">
            <h2
              className="vt-pred-col-header text-base sm:text-lg"
              style={{ fontSize: "1rem", letterSpacing: "0.22em" }}
            >
              AI 趋 势 分 析
            </h2>
          </div>

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
          ) : prediction ? (
            <div className="space-y-4">
              {/* Hero Prediction */}
              <div
                className="flex flex-wrap items-center justify-center gap-4 sm:gap-8 py-5 px-3 rounded-md"
                style={{
                  background: "radial-gradient(ellipse at center, rgba(200,156,58,0.10) 0%, rgba(0,0,0,0) 65%)",
                  borderTop: "1px solid rgba(200,156,58,0.25)",
                  borderBottom: "1px solid rgba(200,156,58,0.25)",
                }}
              >
                <div className="flex flex-col items-center gap-1">
                  <span className="vt-prediction-label">预 测 方 向</span>
                  <TrendDirectionBadge direction={prediction.trend_direction} />
                </div>
                <div className="flex flex-col items-center gap-1">
                  <span className="vt-prediction-label">置 信 度</span>
                  <span
                    className="font-[var(--font-playfair)] font-extrabold text-3xl sm:text-4xl text-vt-brass-300"
                    style={{
                      textShadow: "0 0 12px rgba(229,193,99,0.55), 0 1px 0 rgba(0,0,0,0.6), 0 -1px 0 rgba(255,220,140,0.15)",
                      letterSpacing: "0.02em",
                    }}
                  >
                    {prediction.confidence}
                    <span className="text-xl sm:text-2xl text-vt-brass-400 ml-1">%</span>
                  </span>
                </div>
              </div>

              {/* 六维双轮分析 */}
              {(prediction.宏观产业周期 || prediction.波段操作执行 || prediction.综合判断) ? (
                <InstitutionalAnalysisPanel prediction={prediction} />
              ) : (
                <div>
                  <p className="vt-prediction-label mb-2">分 析 摘 要</p>
                  <p className="text-vt-parchment text-sm leading-relaxed">{prediction.summary}</p>
                </div>
              )}

              <div className="vt-engraved text-xs">
                分析时间: {new Date(prediction.analyzed_at).toLocaleString("zh-CN")}
              </div>
            </div>
          ) : (
            <div className="vt-engraved text-center py-4">暂无分析数据</div>
          )}
        </section>
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
      <span className="vt-pred-up vt-pulse" style={{ fontSize: "1.5rem", padding: "0.4rem 1rem" }}>
        <span className="text-2xl leading-none">▲</span>
        看 涨
      </span>
    );
  } else if (direction === "down") {
    return (
      <span className="vt-pred-down vt-pulse" style={{ fontSize: "1.5rem", padding: "0.4rem 1rem" }}>
        <span className="text-2xl leading-none">▼</span>
        看 跌
      </span>
    );
  } else {
    return (
      <span className="vt-pred-flat" style={{ fontSize: "1.5rem", padding: "0.4rem 1rem" }}>
        <span className="text-2xl leading-none">◆</span>
        中 性
      </span>
    );
  }
}
