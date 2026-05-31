"use client";

import { useEffect, useRef, useState } from "react";
import { fetchSectorMoneyFlow, SectorMoneyFlowResponse } from "@/services/sectorMoneyFlow";
import SectorTopStocksPanel from "@/components/SectorTopStocksPanel";

// Brass/parchment-aligned palette for sector colors (warm, vintage)
const SECTOR_PALETTE = [
  "#c89c3a", // brass
  "#e5c163", // bright brass
  "#a8392a", // oxblood
  "#6ea96a", // emerald
  "#5a9a92", // teal
  "#d4a84b", // gold
  "#9c7621", // deep brass
  "#c75a4a", // soft oxblood
  "#8b5a3c", // brown
  "#b88a2c", // bronze
];

const OUTFLOW_COLOR = "#5a4a3a"; // muted brown for outflow

function sectorColor(name: string, isPositive: boolean): string {
  if (!isPositive) return OUTFLOW_COLOR;
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i);
    hash = hash & hash;
  }
  return SECTOR_PALETTE[Math.abs(hash) % SECTOR_PALETTE.length];
}

interface SegmentRect {
  sector: string;
  // Three line segments (start→corner, corner→corner, corner→end) for hit-testing
  lines: Array<{ x1: number; y1: number; x2: number; y2: number }>;
}

export default function SectorMoneyFlowSankey() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const segmentsRef = useRef<SegmentRect[]>([]);
  const [data, setData] = useState<SectorMoneyFlowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateStr, setDateStr] = useState<string>("");
  const [containerWidth, setContainerWidth] = useState<number>(0);
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [highlightedSector, setHighlightedSector] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const result = await fetchSectorMoneyFlow(5, 8);
        if (result.error) {
          setError(result.error);
        } else {
          setData(result);
          const dates = Object.keys(result.daily_top).sort().reverse();
          if (dates.length > 0) setDateStr(dates[0]);
        }
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 640);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w > 0) setContainerWidth(w);
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [data]);

  useEffect(() => {
    if (!data || !canvasRef.current || !containerRef.current || containerWidth === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { daily_top, net_amounts } = data;
    const dates = Object.keys(daily_top).sort().reverse();
    const topN = 8;

    const padding = isMobile
      ? { top: 24, right: 12, bottom: 12, left: 12 }
      : { top: 32, right: 24, bottom: 16, left: 24 };

    const dateLabelHeight = 22;
    const barHeight = isMobile ? 14 : 18;
    const barGap = isMobile ? 4 : 5;
    const rowContentHeight = topN * barHeight + (topN - 1) * barGap;
    const rowHeight = dateLabelHeight + rowContentHeight;
    const rowGap = isMobile ? 18 : 24;

    const chartWidth = containerWidth - padding.left - padding.right;
    const totalHeight = dates.length * (rowHeight + rowGap) + padding.top + padding.bottom;

    const barAreaWidth = chartWidth * (isMobile ? 0.6 : 0.65);
    const laneAreaStart = padding.left + barAreaWidth + chartWidth * 0.05;
    const laneAreaEnd = padding.left + chartWidth;
    const labelMaxWidth = isMobile ? chartWidth * 0.55 : chartWidth * 0.6;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = containerWidth * dpr;
    canvas.height = totalHeight * dpr;
    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${totalHeight}px`;
    ctx.scale(dpr, dpr);

    const bgGradient = ctx.createLinearGradient(0, 0, 0, totalHeight);
    bgGradient.addColorStop(0, "rgba(40, 32, 22, 0.5)");
    bgGradient.addColorStop(1, "rgba(24, 19, 13, 0.5)");
    ctx.fillStyle = bgGradient;
    ctx.fillRect(0, 0, containerWidth, totalHeight);

    const maxAbsValue = Math.max(
      ...dates.flatMap((d) =>
        (daily_top[d] || []).map((s) => Math.abs(net_amounts[d]?.[s] || 0))
      )
    );

    const sectorPositions: Record<string, Array<{ dateIdx: number; barY: number; barX: number; barWidth: number; rankIdx: number }>> = {};

    dates.forEach((date, dateIdx) => {
      const rowTop = padding.top + dateIdx * (rowHeight + rowGap) + dateLabelHeight;
      const sectors = daily_top[date] || [];

      sectors.forEach((sector, rankIdx) => {
        const value = net_amounts[date]?.[sector] || 0;
        const absValue = Math.abs(value);
        const barWidth = (absValue / maxAbsValue) * barAreaWidth;
        const barY = rowTop + rankIdx * (barHeight + barGap);

        if (!sectorPositions[sector]) sectorPositions[sector] = [];
        sectorPositions[sector].push({
          dateIdx,
          barY: barY + barHeight / 2,
          barX: padding.left + barWidth,
          barWidth,
          rankIdx,
        });
      });
    });

    // Helper: is this sector dimmed (i.e., highlightedSector is set but it's different)
    const isDimmed = (sector: string) => highlightedSector !== null && highlightedSector !== sector;

    // Draw date labels and dividers
    dates.forEach((date, dateIdx) => {
      const rowStartY = padding.top + dateIdx * (rowHeight + rowGap);
      const sectors = daily_top[date] || [];

      ctx.fillStyle = "#e5c163";
      ctx.font = isMobile ? "600 11px Georgia, serif" : "600 13px Georgia, serif";
      ctx.textAlign = "left";

      const dateLabel = date.slice(5).replace("-", "/");
      ctx.fillText(dateLabel, padding.left, rowStartY + 12);

      ctx.fillStyle = "#8a7853";
      ctx.font = isMobile ? "10px Georgia, serif" : "11px Georgia, serif";
      ctx.fillText(`· Top ${sectors.length} 行业`, padding.left + ctx.measureText(dateLabel).width + 6, rowStartY + 12);

      if (dateIdx < dates.length - 1) {
        ctx.strokeStyle = "rgba(140, 105, 50, 0.15)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, rowStartY + rowHeight + rowGap / 2);
        ctx.lineTo(padding.left + chartWidth, rowStartY + rowHeight + rowGap / 2);
        ctx.stroke();
      }
    });

    // Draw flow lines first so bars/labels render on top of them
    const flowLineEntries = Object.entries(sectorPositions).filter(([, p]) => p.length >= 2);

    const segments: Array<{ sector: string; curr: typeof sectorPositions[string][0]; next: typeof sectorPositions[string][0]; color: string }> = [];
    flowLineEntries.forEach(([sector, positions]) => {
      const value = net_amounts[dates[positions[0].dateIdx]]?.[sector] || 0;
      const isPositive = value >= 0;
      const color = sectorColor(sector, isPositive);
      for (let i = 0; i < positions.length - 1; i++) {
        segments.push({ sector, curr: positions[i], next: positions[i + 1], color });
      }
    });

    const laneCount = Math.max(segments.length, 1);
    const laneWidth = (laneAreaEnd - laneAreaStart) / laneCount;

    const segmentRects: SegmentRect[] = [];

    segments.forEach(({ sector, curr, next, color }, idx) => {
      const laneX = laneAreaStart + (idx + 0.5) * laneWidth;
      const dimmed = isDimmed(sector);
      const highlighted = highlightedSector === sector;

      ctx.strokeStyle = color;
      ctx.globalAlpha = dimmed ? 0.1 : highlighted ? 0.95 : 0.55;
      ctx.lineWidth = highlighted ? 3.5 : 1.8;
      ctx.beginPath();
      ctx.moveTo(curr.barX, curr.barY);
      ctx.lineTo(laneX, curr.barY);
      ctx.lineTo(laneX, next.barY);
      ctx.lineTo(next.barX, next.barY);
      ctx.stroke();
      ctx.globalAlpha = 1;

      segmentRects.push({
        sector,
        lines: [
          { x1: curr.barX, y1: curr.barY, x2: laneX, y2: curr.barY },
          { x1: laneX, y1: curr.barY, x2: laneX, y2: next.barY },
          { x1: laneX, y1: next.barY, x2: next.barX, y2: next.barY },
        ],
      });
    });

    segmentsRef.current = segmentRects;

    // Draw bars on top of flow lines
    dates.forEach((date, dateIdx) => {
      const rowTop = padding.top + dateIdx * (rowHeight + rowGap) + dateLabelHeight;
      const sectors = daily_top[date] || [];

      sectors.forEach((sector, rankIdx) => {
        const value = net_amounts[date]?.[sector] || 0;
        const absValue = Math.abs(value);
        const barWidth = (absValue / maxAbsValue) * barAreaWidth;
        const barY = rowTop + rankIdx * (barHeight + barGap);
        const isPositive = value >= 0;
        const color = sectorColor(sector, isPositive);
        const dimmed = isDimmed(sector);

        ctx.globalAlpha = dimmed ? 0.2 : 1;

        ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
        ctx.fillRect(padding.left + 1, barY + 1, barWidth, barHeight);

        const barGradient = ctx.createLinearGradient(padding.left, barY, padding.left, barY + barHeight);
        barGradient.addColorStop(0, color);
        barGradient.addColorStop(1, adjustBrightness(color, -0.25));
        ctx.fillStyle = barGradient;
        ctx.fillRect(padding.left, barY, barWidth, barHeight);

        ctx.fillStyle = "rgba(255, 255, 255, 0.15)";
        ctx.fillRect(padding.left, barY, barWidth, 1);

        const sign = value >= 0 ? "+" : "";
        const valueLabel = `${sign}${value.toFixed(1)}亿`;

        const sectorFont = isMobile ? "600 11px Georgia, serif" : "600 12px Georgia, serif";
        const valueFont = isMobile ? "10px Georgia, serif" : "11px Georgia, serif";

        ctx.font = sectorFont;
        const sectorWidth = ctx.measureText(sector).width;
        ctx.font = valueFont;
        const valueWidth = ctx.measureText(valueLabel).width;

        const inlinePadding = 6;
        const inlineGap = 8;
        const bothFitInside = barWidth >= sectorWidth + valueWidth + inlinePadding * 2 + inlineGap;
        const sectorFitsInside = barWidth >= sectorWidth + inlinePadding * 2;

        if (bothFitInside) {
          ctx.fillStyle = "#fff3d6";
          ctx.font = sectorFont;
          ctx.textAlign = "left";
          ctx.fillText(sector, padding.left + inlinePadding, barY + barHeight / 2 + 4);

          ctx.fillStyle = "rgba(255, 243, 214, 0.85)";
          ctx.font = valueFont;
          ctx.textAlign = "right";
          ctx.fillText(valueLabel, padding.left + barWidth - inlinePadding, barY + barHeight / 2 + 4);
        } else if (sectorFitsInside) {
          ctx.fillStyle = "#fff3d6";
          ctx.font = sectorFont;
          ctx.textAlign = "left";
          ctx.fillText(sector, padding.left + inlinePadding, barY + barHeight / 2 + 4);

          ctx.fillStyle = "#f4e9cf";
          ctx.font = valueFont;
          ctx.textAlign = "left";
          ctx.fillText(valueLabel, padding.left + barWidth + 6, barY + barHeight / 2 + 4);
        } else {
          ctx.fillStyle = "#f4e9cf";
          ctx.font = sectorFont;
          ctx.textAlign = "left";

          const labelX = padding.left + barWidth + 6;
          const fullLabel = `${sector} ${valueLabel}`;

          let displayLabel = fullLabel;
          while (ctx.measureText(displayLabel).width > labelMaxWidth - barWidth && displayLabel.length > 5) {
            displayLabel = displayLabel.slice(0, -1);
          }
          ctx.fillText(displayLabel, labelX, barY + barHeight / 2 + 4);
        }

        ctx.globalAlpha = 1;
      });
    });
  }, [data, containerWidth, isMobile, highlightedSector]);

  // Click handler for canvas to detect line clicks
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Hit-test: find the segment whose any of 3 lines is within 6px of click
    const HIT_THRESHOLD = 6;
    let hitSector: string | null = null;
    let minDist = Infinity;

    for (const segRect of segmentsRef.current) {
      for (const line of segRect.lines) {
        const dist = pointToLineDistance(x, y, line.x1, line.y1, line.x2, line.y2);
        if (dist <= HIT_THRESHOLD && dist < minDist) {
          minDist = dist;
          hitSector = segRect.sector;
        }
      }
    }

    if (hitSector !== null) {
      // Toggle: click again on same sector to deselect
      setHighlightedSector(prev => prev === hitSector ? null : hitSector);
    } else {
      // Clicked empty area: clear selection
      setHighlightedSector(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="vt-engraved text-sm">加 载 中 …</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-vt-oxblood-400 text-sm">数 据 加 载 失 败: {error}</span>
      </div>
    );
  }

  if (!data || Object.keys(data.daily_top).length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="vt-engraved text-sm">暂 无 数 据</span>
      </div>
    );
  }

  const allDates = Object.keys(data.daily_top).sort().reverse();
  const flowSectors = Object.entries(
    allDates.reduce((acc, date, dateIdx) => {
      (data.daily_top[date] || []).forEach((s) => {
        if (!acc[s]) acc[s] = [];
        acc[s].push(dateIdx);
      });
      return acc;
    }, {} as Record<string, number[]>)
  ).filter(([, idxs]) => idxs.length >= 2);

  const legendItems = flowSectors.map(([sector, idxs]) => {
    // Sum net_amount across all dates this sector appears in
    let total = 0;
    idxs.forEach((dateIdx) => {
      const date = allDates[dateIdx];
      const val = data.net_amounts[date]?.[sector];
      if (typeof val === "number") total += val;
    });
    return {
      sector,
      color: sectorColor(sector, total >= 0),
      total,
    };
  });

  // Sort by total amount descending so largest flows appear first
  legendItems.sort((a, b) => b.total - a.total);

  return (
    <div>
      <div
        ref={containerRef}
        className="w-full overflow-hidden rounded border border-vt-ink-700"
        style={{
          background: "linear-gradient(180deg, rgba(40,32,22,0.4) 0%, rgba(24,19,13,0.4) 100%)",
        }}
      >
        <canvas
          ref={canvasRef}
          className="block cursor-pointer"
          onClick={handleCanvasClick}
        />
      </div>
      {highlightedSector && (
        <div className="flex justify-center mt-3">
          <button
            onClick={() => setHighlightedSector(null)}
            className="vt-engraved text-xs px-3 py-1 rounded border border-vt-ink-700 hover:border-vt-brass-400 transition-colors"
          >
            已选中: <span className="text-vt-brass-400">{highlightedSector}</span> · 点击取消
          </button>
        </div>
      )}
      {highlightedSector && data && (() => {
        // Derive which dates this sector appears in from daily_top
        const sectorDates = Object.entries(data.daily_top)
          .filter(([, sectors]) => sectors.includes(highlightedSector))
          .map(([date]) => date)
          .sort()
          .reverse();
        if (sectorDates.length === 0) return null;
        return <SectorTopStocksPanel sector={highlightedSector} dates={sectorDates} top_n={5} />;
      })()}
      {legendItems.length > 0 && (
        <div className="flex flex-wrap justify-center gap-x-3 gap-y-2 mt-3 text-xs">
          {legendItems.map(({ sector, color, total }) => {
            const isActive = highlightedSector === sector;
            const dimmed = highlightedSector !== null && !isActive;
            const sign = total >= 0 ? "+" : "";
            const totalLabel = `${sign}${total.toFixed(1)}亿`;
            const totalColor = total >= 0 ? "text-vt-emerald-400" : "text-vt-oxblood-400";
            return (
              <button
                key={sector}
                onClick={() =>
                  setHighlightedSector(prev => prev === sector ? null : sector)
                }
                className="flex items-center gap-1.5 cursor-pointer transition-opacity"
                style={{ opacity: dimmed ? 0.3 : 1 }}
              >
                <div
                  className="w-3 h-3 rounded-sm"
                  style={{
                    background: `linear-gradient(180deg, ${color}, ${adjustBrightness(color, -0.25)})`,
                    boxShadow: isActive
                      ? `0 0 0 2px ${color}` + ", 0 1px 0 rgba(255,255,255,0.1) inset"
                      : "0 1px 0 rgba(255,255,255,0.1) inset",
                  }}
                />
                <span className={isActive ? "text-vt-brass-400" : "text-vt-parchment-soft"}>
                  {sector}
                </span>
                <span className={`${totalColor} font-mono tabular-nums`}>
                  {totalLabel}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function adjustBrightness(hex: string, percent: number): string {
  const num = parseInt(hex.replace("#", ""), 16);
  let r = (num >> 16) & 0xff;
  let g = (num >> 8) & 0xff;
  let b = num & 0xff;
  r = Math.max(0, Math.min(255, Math.round(r + r * percent)));
  g = Math.max(0, Math.min(255, Math.round(g + g * percent)));
  b = Math.max(0, Math.min(255, Math.round(b + b * percent)));
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}

// Distance from point (px, py) to line segment (x1,y1)→(x2,y2)
function pointToLineDistance(px: number, py: number, x1: number, y1: number, x2: number, y2: number): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  if (dx === 0 && dy === 0) {
    return Math.hypot(px - x1, py - y1);
  }
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)));
  const closestX = x1 + t * dx;
  const closestY = y1 + t * dy;
  return Math.hypot(px - closestX, py - closestY);
}
