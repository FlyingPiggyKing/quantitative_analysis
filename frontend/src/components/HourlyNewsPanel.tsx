"use client";

import { useState, useEffect, useCallback } from "react";
import { getHourlyNews, HourlyNewsSummary } from "@/services/hourlyNews";

function getDirectionColor(direction: string): string {
  if (direction.includes("流入")) return "text-vt-emerald-400";
  if (direction.includes("流出")) return "text-vt-oxblood-400";
  return "text-vt-brass-300";
}

function getDirectionBg(direction: string): string {
  if (direction.includes("流入")) return "bg-vt-emerald-900/30";
  if (direction.includes("流出")) return "bg-vt-oxblood-900/30";
  return "bg-vt-brass-900/30";
}

interface HourlyNewsCardProps {
  summary: HourlyNewsSummary;
}

function HourlyNewsCard({ summary }: HourlyNewsCardProps) {
  const direction = summary.market_impact?.direction || "中性";

  return (
    <div className="vt-panel p-4 mb-3">
      {/* Header with hour and market direction */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-[var(--font-playfair)] text-lg tracking-[0.1em] text-vt-parchment">
          {summary.hour} 新闻摘要
        </h3>
        <span className={`px-2 py-0.5 text-xs font-medium rounded ${getDirectionBg(direction)} ${getDirectionColor(direction)}`}>
          {direction}
        </span>
      </div>

      {/* Top 3 News */}
      <div className="mb-3">
        <h4 className="vt-engraved text-xs tracking-[0.1em] uppercase text-vt-brass-300 mb-2">
          重要新闻
        </h4>
        <ul className="space-y-2">
          {summary.top3_news && summary.top3_news.length > 0 ? (
            summary.top3_news.map((news, idx) => (
              <li key={idx} className="flex flex-col">
                <span className="text-vt-parchment text-sm">
                  <span className="inline-block w-5 h-5 text-center bg-vt-ink-700 text-vt-brass-300 text-xs font-medium rounded mr-2">
                    {idx + 1}
                  </span>
                  {news.summary}
                </span>
                {news.impact_reason && (
                  <span className="text-vt-parchment-dim text-xs mt-0.5 ml-7">
                    → {news.impact_reason}
                  </span>
                )}
              </li>
            ))
          ) : (
            <li className="text-vt-parchment-dim text-sm">暂无重要新闻</li>
          )}
        </ul>
      </div>

      {/* Market Impact */}
      <div className="mb-3">
        <h4 className="vt-engraved text-xs tracking-[0.1em] uppercase text-vt-brass-300 mb-1">
          大盘影响
        </h4>
        <p className="text-vt-parchment text-sm">
          {summary.market_impact?.reason || "暂无分析"}
        </p>
      </div>

      {/* Sector Impact */}
      <div>
        <h4 className="vt-engraved text-xs tracking-[0.1em] uppercase text-vt-brass-300 mb-1">
          影响板块
        </h4>
        {summary.sector_impact && summary.sector_impact.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {summary.sector_impact.map((sector, idx) => (
              <span key={idx} className="px-2 py-1 bg-vt-ink-700 text-vt-parchment text-xs rounded">
                {sector.sector}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-vt-parchment-dim text-sm">暂无板块影响分析</p>
        )}
      </div>
    </div>
  );
}

export default function HourlyNewsPanel() {
  const [newsData, setNewsData] = useState<HourlyNewsSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHourlyNews(3);
      setNewsData(data);
    } catch (err) {
      setError("加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <span className="vt-engraved text-sm">加载中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <span className="vt-oxblood-400 text-sm">{error}</span>
      </div>
    );
  }

  if (!newsData || newsData.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <span className="vt-engraved text-sm text-vt-parchment-dim">暂无小时资讯数据</span>
        <button
          onClick={loadData}
          className="mt-3 vt-btn-secondary px-4 py-2 text-xs"
        >
          刷 新
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-[var(--font-playfair)] text-lg tracking-[0.15em] text-vt-parchment uppercase">
          小时资讯
        </h2>
        <button
          onClick={loadData}
          className="vt-btn-secondary px-3 py-1 text-xs"
        >
          刷 新
        </button>
      </div>

      {newsData.map((summary) => (
        <HourlyNewsCard key={summary.hour_timestamp} summary={summary} />
      ))}
    </div>
  );
}
