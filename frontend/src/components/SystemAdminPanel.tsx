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

const STATUS_LABELS: Record<string, string> = {
  ok: "正常",
  warn: "滞后",
  stale: "停滞",
  unknown: "无数据",
};

const STATUS_PILL_CLASS: Record<string, string> = {
  ok: "vt-pill vt-pill-ok",
  warn: "vt-pill vt-pill-warn",
  stale: "vt-pill vt-pill-stale",
  unknown: "vt-pill vt-pill-unknown",
};

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffMs = now - then;
  if (Number.isNaN(diffMs)) return iso;
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.round(hours / 24);
  return `${days} 天前`;
}

function formatDateOnly(iso: string | null): string {
  if (!iso) return "—";
  // Accept either an ISO timestamp or a YYYY-MM-DD business date.
  const m = iso.match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : iso;
}

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

interface EtfPushRow {
  data_type: string;
  label_zh: string;
  last_received_at: string | null;
  last_record_date: string | null;
  row_count: number;
  lag_hours: number | null;
  status: "ok" | "warn" | "stale" | "unknown";
}

interface EtfPushStatus {
  tables: EtfPushRow[];
  server_time: string;
  db_path: string;
  thresholds: { warn_hours: number; stale_hours: number };
  error?: string;
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

  // ETF push status — auto-refresh every 60s; manual refresh via button.
  const [etfPush, setEtfPush] = useState<EtfPushStatus | null>(null);
  const [etfPushLoading, setEtfPushLoading] = useState(true);
  const [etfPushError, setEtfPushError] = useState<string | null>(null);
  const [etfPushRefreshing, setEtfPushRefreshing] = useState(false);

  const refreshEtfPush = useCallback(async (manual = false) => {
    if (manual) setEtfPushRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/etf-remote-push-status`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: EtfPushStatus = await res.json();
      setEtfPush(data);
      setEtfPushError(null);
    } catch (err) {
      // Keep previous snapshot visible; surface the error inline.
      setEtfPushError(err instanceof Error ? err.message : "刷新失败");
    } finally {
      setEtfPushLoading(false);
      if (manual) setEtfPushRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refreshEtfPush();
    const intervalId = setInterval(() => refreshEtfPush(), 60000);
    return () => clearInterval(intervalId);
  }, [refreshEtfPush]);

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

      {/* ETF Data Push Monitor Block */}
      <div className="vt-panel p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-[var(--font-playfair)] text-lg tracking-[0.18em] text-vt-brass-400">
            ETF 数 据 推 送 监 控
          </h3>
          <button
            type="button"
            onClick={() => refreshEtfPush(true)}
            disabled={etfPushRefreshing}
            className="vt-btn-oxblood px-3 py-1 text-xs min-h-[28px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {etfPushRefreshing ? "刷 新 中 …" : "刷 新"}
          </button>
        </div>

        {etfPushLoading ? (
          <p className="vt-engraved text-vt-parchment-dim text-sm">加载中…</p>
        ) : etfPush?.error && etfPush.tables.length === 0 ? (
          <p className="vt-engraved text-vt-parchment-dim text-sm">
            {etfPush.db_path ? `${etfPush.db_path} 未找到，` : ""}
            请检查 etf_remote.db 是否存在
          </p>
        ) : etfPush?.tables.length === 0 ? (
          <p className="vt-engraved text-vt-parchment-dim text-sm">暂无数据</p>
        ) : (
          <>
            <div className="max-h-72 overflow-y-auto">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-vt-ink-900">
                  <tr className="text-vt-brass-400 text-xs">
                    <th className="py-1 px-2">数据</th>
                    <th className="py-1 px-2">最近推送</th>
                    <th className="py-1 px-2">最新数据日期</th>
                    <th className="py-1 px-2">行数</th>
                    <th className="py-1 px-2">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {etfPush!.tables.map((row) => (
                    <tr key={row.data_type} className="border-t border-vt-ink-800">
                      <td className="py-1 px-2 vt-engraved">{row.label_zh}</td>
                      <td
                        className="py-1 px-2 vt-engraved text-vt-parchment-dim"
                        title={row.last_received_at ?? ""}
                      >
                        {formatRelative(row.last_received_at)}
                      </td>
                      <td className="py-1 px-2 vt-engraved text-vt-parchment-dim">
                        {formatDateOnly(row.last_record_date)}
                      </td>
                      <td className="py-1 px-2 vt-engraved">{row.row_count}</td>
                      <td className="py-1 px-2">
                        <span className={STATUS_PILL_CLASS[row.status]}>
                          {STATUS_LABELS[row.status] ?? row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between mt-3">
              <p className="vt-engraved text-vt-parchment-dim text-xs">
                最近检查：{etfPush?.server_time ?? "—"}
              </p>
              {etfPushError && (
                <p className="vt-engraved text-red-400 text-xs">
                  刷新失败（已保留上次快照）
                </p>
              )}
            </div>
          </>
        )}
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
