"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getWatchlist, WatchlistItem } from "@/services/watchlist";

interface WatchListProps {
  refreshTrigger?: number;
}

export default function WatchList({ refreshTrigger = 0 }: WatchListProps) {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const fetchWatchlist = async () => {
      setLoading(true);
      try {
        const data = await getWatchlist(page, pageSize);
        setItems(data.items);
        setTotalPages(data.total_pages);
      } catch (err) {
        console.error("Failed to fetch watchlist:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchWatchlist();
  }, [page, pageSize, refreshTrigger]);

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setPage(1);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN");
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="text-slate-400 text-center">加载中...</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <h2 className="text-lg font-medium text-white mb-4">我的自选</h2>

      {items.length === 0 ? (
        <div className="text-slate-400 text-center py-8">
          暂无自选股票，搜索股票后点击"加入自选"
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 px-3">股票代码</th>
                  <th className="text-left py-2 px-3">股票名称</th>
                  <th className="text-left py-2 px-3">添加日期</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.symbol}
                    className="text-white border-b border-slate-700/50 hover:bg-slate-700/30"
                  >
                    <td className="py-2 px-3">
                      <Link
                        href={`/stock/${item.symbol}`}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        {item.symbol}
                      </Link>
                    </td>
                    <td className="py-2 px-3">
                      <Link
                        href={`/stock/${item.symbol}`}
                        className="hover:text-blue-300"
                      >
                        {item.name}
                      </Link>
                    </td>
                    <td className="py-2 px-3 text-slate-400">{formatDate(item.added_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-sm">每页显示:</span>
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                className="bg-slate-700 text-white text-sm rounded px-2 py-1 border border-slate-600"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={30}>30</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 bg-slate-700 text-white text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600"
              >
                上一页
              </button>
              <span className="text-slate-400 text-sm">
                第 {page} / {totalPages} 页
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 bg-slate-700 text-white text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
