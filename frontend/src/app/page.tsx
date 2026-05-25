"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import WatchList from "@/components/WatchList";
import ModuleTabs from "@/components/ModuleTabs";
import SubModuleTabs from "@/components/SubModuleTabs";
import { ASharePresetList, USPresetList, HKPresetList } from "@/components/PresetStockList";
import DragonTigerList from "@/components/DragonTigerList";
import SectorMoneyFlowSankey from "@/components/SectorMoneyFlowSankey";
import IndexMetricsPanel from "@/components/IndexMetricsPanel";
import AnalysisProgressBar from "@/components/AnalysisProgressBar";

function GuestWatchlistHeader() {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="font-[var(--font-playfair)] text-xl tracking-[0.18em] text-vt-parchment uppercase">
        <span className="text-vt-brass-400">❖</span> 热 门 股 <span className="text-vt-brass-400">❖</span>
      </h2>
      <span className="vt-engraved text-sm">游客预览</span>
    </div>
  );
}
import { getTaskStatus, runBatchAnalysisAsync, TaskStatusResponse } from "@/services/trendPrediction";
import { useAuth } from "@/services/auth";

const TASK_ID_STORAGE_KEY = "active_analysis_task_id";
const DISMISSED_STORAGE_KEY = "progress_bar_dismissed";

type ModuleType = "watchlist" | "analysis";
type MarketType = "A" | "US" | "HK";
type AnalysisSubModuleType = "dragonTiger";

export default function Home() {
  const [symbol, setSymbol] = useState("");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [taskProgress, setTaskProgress] = useState<TaskStatusResponse | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);
  const [activeModule, setActiveModule] = useState<ModuleType>("watchlist");
  const [watchlistMarket, setWatchlistMarket] = useState<MarketType>("A");
  const [analysisSubModule, setAnalysisSubModule] = useState<AnalysisSubModuleType>("dragonTiger");

  // For backward compatibility with search placeholder
  const stockTab = watchlistMarket;

  // Save current sub-module state when switching modules
  const handleModuleChange = (newModule: ModuleType) => {
    // Reset sub-module to default when switching modules
    if (newModule === "watchlist") {
      setWatchlistMarket("A");
    } else {
      setAnalysisSubModule("dragonTiger");
    }
    setActiveModule(newModule);
  };

  const isAnalyzing = activeTaskId !== null &&
    taskProgress !== null &&
    (taskProgress.status === "pending" || taskProgress.status === "running");
  const router = useRouter();
  const { user, isLoading } = useAuth();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbol.trim()) {
      router.push(`/stock/${symbol.trim()}`);
    }
  };

  // Check for active task on mount
  useEffect(() => {
    const storedTaskId = localStorage.getItem(TASK_ID_STORAGE_KEY);
    const storedDismissed = localStorage.getItem(DISMISSED_STORAGE_KEY);

    if (storedDismissed === "true") {
      setIsDismissed(true);
    }

    if (storedTaskId) {
      setActiveTaskId(storedTaskId);
    }
  }, []);

  // Poll task status when there's an active task
  useEffect(() => {
    if (!activeTaskId || isDismissed) {
      return;
    }

    const pollInterval = 3000; // 3 seconds

    const fetchTaskStatus = async () => {
      try {
        const status = await getTaskStatus(activeTaskId);
        setTaskProgress(status);

        // Clear task when completed or failed
        if (status.status === "completed" || status.status === "failed") {
          localStorage.removeItem(TASK_ID_STORAGE_KEY);
          setActiveTaskId(null);
        }
      } catch (err) {
        console.error("Failed to fetch task status:", err);
        // Mark as failed if we can't fetch the task
        setTaskProgress({ task_id: "", progress: "", current: 0, total: 0, status: "failed" });
      }
    };

    // Fetch immediately
    fetchTaskStatus();

    const intervalId = setInterval(fetchTaskStatus, pollInterval);
    return () => clearInterval(intervalId);
  }, [activeTaskId, isDismissed]);

  // Update localStorage when activeTaskId changes
  useEffect(() => {
    if (activeTaskId) {
      localStorage.setItem(TASK_ID_STORAGE_KEY, activeTaskId);
    }
  }, [activeTaskId]);

  const handleDismiss = useCallback(() => {
    setIsDismissed(true);
    localStorage.setItem(DISMISSED_STORAGE_KEY, "true");
  }, []);

  const handleClearTask = useCallback(() => {
    localStorage.removeItem(TASK_ID_STORAGE_KEY);
    localStorage.removeItem(DISMISSED_STORAGE_KEY);
    setActiveTaskId(null);
    setTaskProgress(null);
    setIsDismissed(false);
  }, []);

  const handleTrendAnalysis = useCallback(async () => {
    try {
      const result = await runBatchAnalysisAsync();
      if (result.task_id) {
        setActiveTaskId(result.task_id);
        setIsDismissed(false);
      }
    } catch (err) {
      console.error("Failed to start trend analysis:", err);
    }
  }, []);

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="vt-engraved text-lg">Loading…</div>
      </div>
    );
  }

  // Show progress bar if there's an active task and not dismissed
  const showProgressBar = activeTaskId && taskProgress && !isDismissed;

  return (
    <div className="min-h-screen px-4 py-4 sm:py-8">
      <div className="w-full max-w-4xl mx-auto">
        <div className="text-center mb-8 sm:mb-10">
          <h1 className="vt-emboss text-4xl sm:text-6xl mb-3 text-center sm:text-left leading-none">
            Stock Analyzer
          </h1>
          <p className="vt-engraved text-base sm:text-lg text-center sm:text-left">
            — crafted by{" "}
            <span className="text-vt-brass-300 not-italic font-semibold tracking-[0.25em]">DATA</span>{" "}
            <span className="text-vt-parchment-dim">&amp;</span>{" "}
            <span className="text-vt-brass-300 not-italic font-semibold tracking-[0.25em]">AI</span>{" "}
            —
          </p>
          <hr className="vt-rule mt-4 sm:mt-5 max-w-md mx-auto sm:mx-0" />
        </div>

        <form onSubmit={handleSearch} className="space-y-4 mb-8">
          <div className="relative">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder={
                stockTab === "A" ? "输入股票代码，如 000001" :
                stockTab === "HK" ? "输入港股代码，如 00700" :
                "输入美股代码，如 MSFT"
              }
              className="vt-input w-full px-4 py-3 text-lg"
            />
          </div>

          <button
            type="submit"
            className="vt-btn-primary w-full px-4 py-3 text-base min-h-[44px]"
          >
            查 询
          </button>

          {user && (
            <button
              type="button"
              onClick={handleTrendAnalysis}
              disabled={isAnalyzing}
              className="vt-btn-oxblood w-full px-4 py-3 text-base min-h-[44px]"
            >
              {isAnalyzing ? "分 析 中 …" : "趋 势 分 析"}
            </button>
          )}
        </form>

        <div className="mb-8">
          <ModuleTabs
            activeModule={activeModule}
            onModuleChange={handleModuleChange}
            watchlistContent={
              <div>
                {!user && <GuestWatchlistHeader />}
                <SubModuleTabs
                  activeModule="watchlist"
                  activeSubModule={watchlistMarket}
                  onSubModuleChange={(sub) => setWatchlistMarket(sub as MarketType)}
                  watchlistSubContent={{
                    aContent: user ? <WatchList key={`${refreshTrigger}-a`} activeMarket="A" /> : <ASharePresetList />,
                    usContent: user ? <WatchList key={`${refreshTrigger}-us`} activeMarket="US" /> : <USPresetList />,
                    hkContent: user ? <WatchList key={`${refreshTrigger}-hk`} activeMarket="HK" /> : <HKPresetList />,
                  }}
                />
              </div>
            }
            analysisContent={
              <SubModuleTabs
                activeModule="analysis"
                analysisSubContent={{
                  renderDragonTigerContent: (onDateChange) => (
                    <DragonTigerList showHeader={false} onDateChange={onDateChange} />
                  ),
                  renderMoneyFlowContent: () => <SectorMoneyFlowSankey />,
                  renderIndexMetricsContent: () => <IndexMetricsPanel />,
                }}
              />
            }
          />
        </div>

        {user ? (
          <div className="mt-8 pt-8 border-t border-vt-ink-700 flex justify-center">
            <button
              onClick={() => {
                localStorage.removeItem("auth_token");
                localStorage.removeItem("auth_user");
                router.push("/");
                window.location.reload();
              }}
              className="vt-btn-secondary px-5 py-2 text-xs"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="mt-8 pt-8 border-t border-vt-ink-700 text-center">
            <div className="vt-panel relative px-6 py-6 mb-6 vt-ornament-tl vt-ornament-tr vt-ornament-bl vt-ornament-br">
              <div className="flex items-center justify-center gap-2 mb-2">
                <svg className="w-5 h-5 text-vt-brass-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-parchment uppercase">
                  升 级 您 的 投 资 体 验
                </span>
              </div>
              <p className="vt-engraved text-sm">登录后可以添加自选股和查看更多功能</p>
            </div>
            <Link
              href="/login"
              className="vt-btn-primary inline-block px-10 py-3 text-sm"
            >
              登 录 / 注 册
            </Link>
          </div>
        )}
      </div>

      {showProgressBar && <AnalysisProgressBar progress={taskProgress} onDismiss={handleDismiss} onClearTask={handleClearTask} />}
    </div>
  );
}
