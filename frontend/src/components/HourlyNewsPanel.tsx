"use client";

import { useState, useEffect, useCallback } from "react";
import { getHourlyNews, HourlyNewsSummary } from "@/services/hourlyNews";

type DirectionTone = "up" | "down" | "flat";

function getDirectionTone(direction: string): DirectionTone {
  if (direction.includes("流入")) return "up";
  if (direction.includes("流出")) return "down";
  return "flat";
}

function DirectionBadge({ direction }: { direction: string }) {
  const tone = getDirectionTone(direction);
  const cls =
    tone === "up" ? "vt-pred-up" :
    tone === "down" ? "vt-pred-down" :
    "vt-pred-flat";
  const arrow = tone === "up" ? "▲" : tone === "down" ? "▼" : "◆";
  return (
    <span className={`${cls} whitespace-nowrap shrink-0`} style={{ fontSize: "0.78rem", padding: "0.12rem 0.5rem" }}>
      <span className="opacity-80">{arrow}</span>
      <span>资金 · {direction}</span>
    </span>
  );
}

interface HourlyNewsCardProps {
  summary: HourlyNewsSummary;
}

function HourlyNewsCard({ summary }: HourlyNewsCardProps) {
  const direction = summary.market_impact?.direction || "中性";

  return (
    <div className="vt-panel p-4 sm:p-5 mb-4 relative vt-ornament-tl vt-ornament-tr vt-ornament-bl vt-ornament-br">
      {/* Header with hour and market direction */}
      <div className="flex items-center justify-between mb-4 gap-3">
        <h3 className="font-[var(--font-playfair)] text-base sm:text-lg tracking-[0.18em] text-vt-brass-300 uppercase">
          {summary.hour}
          <span className="text-vt-parchment-dim ml-2 text-xs tracking-[0.12em] normal-case">新闻摘要</span>
        </h3>
        <DirectionBadge direction={direction} />
      </div>

      <hr className="vt-rule mb-4 opacity-60" />

      {/* Top 3 News */}
      <div className="mb-4">
        <ul className="space-y-3">
          {summary.top3_news && summary.top3_news.length > 0 ? (
            summary.top3_news.filter(Boolean).map((news, idx) => (
              <li key={idx}>
                <p className="text-vt-parchment text-sm leading-relaxed break-words">
                  <span className="text-vt-brass-300 font-[var(--font-playfair)] font-bold mr-1">
                    {idx + 1}.
                  </span>
                  {news?.summary ?? "暂无摘要"}
                </p>
                {news?.impact_reason && (
                  <p className="text-vt-parchment-dim text-xs mt-1 leading-relaxed border-l-2 border-vt-brass-700/50 pl-2">
                    {news.impact_reason}
                  </p>
                )}
              </li>
            ))
          ) : (
            <li className="text-vt-parchment-dim text-sm italic">暂无重要新闻</li>
          )}
        </ul>
      </div>

      {/* Market Impact */}
      <div className="mb-4">
        <h4 className="vt-engraved text-[0.7rem] tracking-[0.18em] uppercase text-vt-brass-400 mb-2">
          ❖ 大 盘 影 响
        </h4>
        <p className="text-vt-parchment text-sm leading-relaxed">
          {summary.market_impact?.reason || "暂无分析"}
        </p>
      </div>

      {/* Sector Impact */}
      <div>
        <h4 className="vt-engraved text-[0.7rem] tracking-[0.18em] uppercase text-vt-brass-400 mb-2">
          ❖ 影 响 板 块
        </h4>
        {summary.sector_impact && summary.sector_impact.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {summary.sector_impact.map((sector, idx) => (
              <span
                key={idx}
                title={sector.reason}
                className="px-2.5 py-1 text-xs rounded-sm bg-vt-ink-700 text-vt-parchment border border-vt-brass-700/60 hover:border-vt-brass-500/80 transition-colors cursor-default"
              >
                {sector.sector}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-vt-parchment-dim text-sm italic">暂无板块影响分析</p>
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
      <div className="flex items-center justify-center py-10">
        <span className="vt-engraved text-sm vt-pulse">加载中…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-10 gap-3">
        <span className="text-vt-oxblood-400 text-sm">{error}</span>
        <button onClick={loadData} className="vt-btn-secondary px-4 py-2 text-xs">
          重 试
        </button>
      </div>
    );
  }

  if (!newsData || newsData.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 gap-3">
        <span className="vt-engraved text-sm text-vt-parchment-dim">暂无小时资讯数据</span>
        <button onClick={loadData} className="vt-btn-secondary px-4 py-2 text-xs">
          刷 新
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-[var(--font-playfair)] text-base sm:text-lg tracking-[0.2em] text-vt-parchment uppercase">
          <span className="text-vt-brass-400">❖</span> 小 时 资 讯 <span className="text-vt-brass-400">❖</span>
        </h2>
        <button onClick={loadData} className="vt-btn-secondary px-3 py-1.5 text-xs shrink-0">
          刷 新
        </button>
      </div>

      {newsData.map((summary) => (
        <HourlyNewsCard key={summary.hour_timestamp} summary={summary} />
      ))}
    </div>
  );
}
