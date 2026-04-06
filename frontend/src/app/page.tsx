"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import WatchList from "@/components/WatchList";

export default function Home() {
  const [symbol, setSymbol] = useState("");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbol.trim()) {
      router.push(`/stock/${symbol.trim()}`);
    }
  };

  // This component will re-render when returning from detail page
  // The WatchList component will automatically refresh

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Stock Analyzer</h1>
          <p className="text-slate-400">输入股票代码查看K线图和技术指标</p>
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
        </form>

        <div className="mb-8">
          <WatchList key={refreshTrigger} />
        </div>

        <div className="text-center text-slate-500 text-sm">
          <p>示例代码: 000001 (平安银行), 600000 (浦发银行), 300059 (东方财富)</p>
        </div>
      </div>
    </div>
  );
}
