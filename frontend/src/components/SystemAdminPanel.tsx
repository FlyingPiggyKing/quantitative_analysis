"use client";

import { useState, useEffect } from "react";
import { getAuthHeaders } from "@/services/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
