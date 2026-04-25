"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import WatchList from "@/components/WatchList";
import PresetStockList from "@/components/PresetStockList";
import AnalysisProgressBar from "@/components/AnalysisProgressBar";
import { getTaskStatus, runBatchAnalysisAsync, TaskStatusResponse } from "@/services/trendPrediction";
import { useAuth } from "@/services/auth";

const TASK_ID_STORAGE_KEY = "active_analysis_task_id";
const DISMISSED_STORAGE_KEY = "progress_bar_dismissed";

export default function Home() {
  const [symbol, setSymbol] = useState("");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [taskProgress, setTaskProgress] = useState<TaskStatusResponse | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);

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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  // Show progress bar if there's an active task and not dismissed
  const showProgressBar = activeTaskId && taskProgress && !isDismissed;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 px-4 py-4 sm:py-8">
      <div className="w-full max-w-4xl mx-auto">
        <div className="text-center mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-4xl font-bold text-white mb-2 text-center sm:text-left">Stock Analyzer</h1>
          <p className="text-lg sm:text-xl font-light italic tracking-wide text-center sm:text-left">
            by{" "}
            <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent font-medium">
              DATA
            </span>{" "}
            and{" "}
            <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent font-medium">
              AI
            </span>
          </p>
        </div>

        <form onSubmit={handleSearch} className="space-y-4 mb-8">
          <div className="relative">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="输入股票代码，如 000001"
              className="w-full px-4 py-3 text-lg bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white font-medium rounded-lg transition-colors min-h-[44px]"
          >
            查询
          </button>

          {user && (
            <button
              type="button"
              onClick={handleTrendAnalysis}
              disabled={isAnalyzing}
              className={`w-full px-4 py-3 font-medium rounded-lg transition-colors min-h-[44px] ${
                isAnalyzing
                  ? "bg-slate-600 text-slate-400 cursor-not-allowed opacity-50"
                  : "bg-green-600 hover:bg-green-700 active:scale-[0.98] text-white"
              }`}
            >
              {isAnalyzing ? "分析中..." : "趋势分析"}
            </button>
          )}
        </form>

        <div className="mb-8">
          {user ? (
            <WatchList key={refreshTrigger} />
          ) : (
            <PresetStockList />
          )}
        </div>

        {user ? (
          <div className="mt-8 pt-8 border-t border-slate-800 flex justify-center">
            <button
              onClick={() => {
                localStorage.removeItem("auth_token");
                localStorage.removeItem("auth_user");
                router.push("/");
                window.location.reload();
              }}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-sm rounded-lg transition-colors active:scale-95"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="mt-8 pt-8 border-t border-slate-800 text-center">
            <div className="bg-gradient-to-r from-slate-800/50 via-slate-800 to-slate-800/50 rounded-xl p-6 mb-6 border border-slate-700/50">
              <div className="flex items-center justify-center gap-2 mb-2">
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="text-lg font-medium text-white">升级您的投资体验</span>
              </div>
              <p className="text-slate-400 text-sm">登录后可以添加自选股和查看更多功能</p>
            </div>
            <Link
              href="/login"
              className="inline-block px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-all hover:shadow-lg hover:shadow-blue-500/25 active:scale-95"
            >
              登录 / 注册
            </Link>
          </div>
        )}
      </div>

      {showProgressBar && <AnalysisProgressBar progress={taskProgress} onDismiss={handleDismiss} onClearTask={handleClearTask} />}
    </div>
  );
}
