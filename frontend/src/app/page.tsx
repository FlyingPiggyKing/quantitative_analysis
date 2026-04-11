"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import WatchList from "@/components/WatchList";
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

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [user, isLoading, router]);

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

  // Show loading or redirect
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  // Show progress bar if there's an active task and not dismissed
  const showProgressBar = activeTaskId && taskProgress && !isDismissed;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-white mb-2">Stock Analyzer</h1>
            <p className="text-slate-400">输入股票代码查看K线图和技术指标</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-300">Welcome, {user.username}</span>
            <button
              onClick={() => {
                localStorage.removeItem("auth_token");
                localStorage.removeItem("auth_user");
                router.push("/login");
                window.location.reload();
              }}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
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
            className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            查询
          </button>

          <button
            type="button"
            onClick={handleTrendAnalysis}
            disabled={isAnalyzing}
            className={`w-full px-4 py-3 font-medium rounded-lg transition-colors ${
              isAnalyzing
                ? "bg-slate-600 text-slate-400 cursor-not-allowed opacity-50"
                : "bg-green-600 hover:bg-green-700 text-white"
            }`}
          >
            {isAnalyzing ? "分析中..." : "趋势分析"}
          </button>
        </form>

        <div className="mb-8">
          <WatchList key={refreshTrigger} />
        </div>

        <div className="text-center text-slate-500 text-sm">
          <p>示例代码: 000001 (平安银行), 600000 (浦发银行), 300059 (东方财富)</p>
        </div>
      </div>

      {showProgressBar && <AnalysisProgressBar progress={taskProgress} onDismiss={handleDismiss} />}
    </div>
  );
}
