"use client";

import { useState, useEffect, useCallback } from "react";
import { getAuthHeaders } from "@/services/auth";
import { getTrendRunStatus, triggerTrendRun, TrendRunStatus } from "@/services/trendRun";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const RUN_STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  running: "运行中",
  completed: "已完成",
  cancelled: "已取消",
  interrupted: "已中断",
};

interface WatchlistStock {
  symbol: string;
  name: string;
  market: string;
  added_at: string;
  user_count: number;
}

interface User {
  id: number;
  username: string;
  created_at: string;
}

interface AdminStats {
  watchlist_stocks: WatchlistStock[];
  watchlist_count: number;
  users: User[];
  user_count: number;
}

export default function SystemAdminPanel() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [trendRun, setTrendRun] = useState<TrendRunStatus | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/admin/stats`, {
      headers: getAuthHeaders(),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch stats");
        return res.json();
      })
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const refreshTrendRun = useCallback(async () => {
    try {
      const status = await getTrendRunStatus();
      setTrendRun(status);
    } catch (err) {
      console.error("Failed to fetch trend run status:", err);
    }
  }, []);

  // Poll trend-run status; faster while a run is active.
  useEffect(() => {
    refreshTrendRun();
    const isActive =
      trendRun?.run?.status === "pending" || trendRun?.run?.status === "running";
    const intervalId = setInterval(refreshTrendRun, isActive ? 4000 : 30000);
    return () => clearInterval(intervalId);
  }, [refreshTrendRun, trendRun?.run?.status]);

  const handleTriggerTrendRun = useCallback(async () => {
    if (!trendRun) return;

    // Off-schedule (weekend / before 17:00 / already ran today): require two
    // explicit confirmations before starting a run.
    if (!trendRun.on_schedule && trendRun.off_schedule_reason) {
      const first = window.confirm(
        `${trendRun.off_schedule_reason}\n\n是否真的需要现在运行趋势分析？`
      );
      if (!first) return;
      const second = window.confirm(
        "请再次确认：这将立即启动一次全量趋势分析（分 4 批，每 5 小时一批）。确定运行吗？"
      );
      if (!second) return;
    } else {
      // On-schedule recovery: single confirmation.
      const ok = window.confirm("确认运行趋势分析？");
      if (!ok) return;
    }

    setTriggering(true);
    setTriggerError(null);
    try {
      await triggerTrendRun();
      await refreshTrendRun();
    } catch (err) {
      setTriggerError(err instanceof Error ? err.message : "触发失败");
    } finally {
      setTriggering(false);
    }
  }, [trendRun, refreshTrendRun]);

  if (loading) {
    return (
      <div className="vt-panel p-4 text-center">
        <span className="vt-engraved">加载中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="vt-panel p-4 text-center text-red-400">
        <span className="vt-engraved">加载失败: {error}</span>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      {/* Trend Analysis Progress Block */}
      <div className="vt-panel p-4">
        <h3 className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-brass-400 mb-4">
          趋 势 分 析 进 度
        </h3>
        {trendRun?.run ? (
          <div className="space-y-2 text-sm">
            <p className="vt-engraved">
              运行日期：{trendRun.run.run_date}
              <span className="text-vt-parchment-dim">
                {" "}
                ({trendRun.run.trigger_type === "auto" ? "自动" : "手动"} ·{" "}
                {RUN_STATUS_LABELS[trendRun.run.status] || trendRun.run.status})
              </span>
            </p>
            {trendRun.run.status === "pending" || trendRun.run.status === "running" ? (
              <>
                <p className="vt-engraved">
                  第 {trendRun.run.current_batch}/{trendRun.run.batch_count} 批
                </p>
                <p className="vt-engraved">
                  {trendRun.run.batch_completed}/{trendRun.run.batch_total}
                </p>
              </>
            ) : (
              <p className="vt-engraved text-vt-parchment-dim">最近一次运行已结束</p>
            )}
          </div>
        ) : (
          <p className="vt-engraved text-vt-parchment-dim text-sm">暂无运行记录</p>
        )}

        <button
          type="button"
          onClick={handleTriggerTrendRun}
          disabled={!trendRun || trendRun.run_active || triggering}
          className="vt-btn-oxblood w-full px-4 py-2 text-sm min-h-[40px] mt-4 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {triggering ? "触 发 中 …" : "趋 势 分 析"}
        </button>
        {trendRun?.run_active && trendRun.disabled_reason && (
          <p className="vt-engraved text-vt-parchment-dim text-xs mt-2">{trendRun.disabled_reason}</p>
        )}
        {!trendRun?.run_active && trendRun?.off_schedule_reason && (
          <p className="vt-engraved text-vt-parchment-dim text-xs mt-2">
            {trendRun.off_schedule_reason}点击后需二次确认。
          </p>
        )}
        {triggerError && (
          <p className="vt-engraved text-red-400 text-xs mt-2">{triggerError}</p>
        )}
      </div>

      {/* Stock Statistics Block */}
      <div className="vt-panel p-4">
        <h3 className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-brass-400 mb-4">
          股 票 统 计
        </h3>
        <p className="vt-engraved text-sm mb-3">共 {stats.watchlist_count} 只股票</p>
        <div className="space-y-1 text-sm">
          {stats.watchlist_stocks.length === 0 ? (
            <p className="vt-engraved text-vt-parchment-dim">暂无数据</p>
          ) : (
            <div className="max-h-48 overflow-y-auto">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-vt-ink-900">
                  <tr className="text-vt-brass-400 text-xs">
                    <th className="py-1 px-2">代码</th>
                    <th className="py-1 px-2">名称</th>
                    <th className="py-1 px-2">市场</th>
                    <th className="py-1 px-2">添加日期</th>
                    <th className="py-1 px-2">关注人数</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.watchlist_stocks.map((stock) => (
                    <tr key={stock.symbol} className="border-t border-vt-ink-800">
                      <td className="py-1 px-2 vt-engraved">{stock.symbol}</td>
                      <td className="py-1 px-2 vt-engraved">{stock.name}</td>
                      <td className="py-1 px-2 vt-engraved">{stock.market}</td>
                      <td className="py-1 px-2 vt-engraved text-vt-parchment-dim">
                        {new Date(stock.added_at).toLocaleDateString("zh-CN")}
                      </td>
                      <td className="py-1 px-2 vt-engraved">{stock.user_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* User Statistics Block */}
      <div className="vt-panel p-4">
        <h3 className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-brass-400 mb-4">
          用 户 统 计
        </h3>
        <p className="vt-engraved text-sm mb-3">共 {stats.user_count} 位用户</p>
        <div className="space-y-1 text-sm">
          {stats.users.length === 0 ? (
            <p className="vt-engraved text-vt-parchment-dim">暂无数据</p>
          ) : (
            <div className="max-h-48 overflow-y-auto">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-vt-ink-900">
                  <tr className="text-vt-brass-400 text-xs">
                    <th className="py-1 px-2">ID</th>
                    <th className="py-1 px-2">用户名</th>
                    <th className="py-1 px-2">注册日期</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.users.map((user) => (
                    <tr key={user.id} className="border-t border-vt-ink-800">
                      <td className="py-1 px-2 vt-engraved">{user.id}</td>
                      <td className="py-1 px-2 vt-engraved">{user.username}</td>
                      <td className="py-1 px-2 vt-engraved text-vt-parchment-dim">
                        {new Date(user.created_at).toLocaleDateString("zh-CN")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
