"use client";

import { useMemo, useState, useRef, useEffect } from "react";
import { PEHistoryItem } from "@/services/indexMetrics";

interface PEHistoryChartProps {
  data: PEHistoryItem[];
  opportunity: number | null;
  danger: number | null;
  height?: number;
}

export default function PEHistoryChart({
  data,
  opportunity,
  danger,
  height = 150,
}: PEHistoryChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(600);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth);
      }
    };
    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return null;

    const parsed = data
      .filter((d) => d.pe > 0)
      .map((d) => ({
        date: new Date(
          // Convert YYYYMMDD to YYYY-MM-DD for consistent parsing
          `${d.trade_date.slice(0, 4)}-${d.trade_date.slice(4, 6)}-${d.trade_date.slice(6, 8)}`
        ),
        pe: d.pe,
      }))
      .sort((a, b) => a.date.getTime() - b.date.getTime());

    if (parsed.length === 0) return null;

    const peValues = parsed.map((d) => d.pe);
    const minPE = Math.min(...peValues);
    const maxPE = Math.max(...peValues);
    const minDate = parsed[0].date.getTime();
    const maxDate = parsed[parsed.length - 1].date.getTime();

    const padding = (maxPE - minPE) * 0.1 || 5;
    let yMin = Math.max(0, minPE - padding);
    let yMax = maxPE + padding;

    if (opportunity !== null) yMin = Math.min(yMin, opportunity * 0.9);
    if (danger !== null) yMax = Math.max(yMax, danger * 1.05);

    const width = containerWidth;
    const chartHeight = height;
    const padTop = 10;
    const padBottom = 25;
    const padLeft = 35;
    const padRight = 10;

    const plotWidth = width - padLeft - padRight;
    const plotHeight = chartHeight - padTop - padBottom;

    const xScale = (date: Date) =>
      padLeft + ((date.getTime() - minDate) / (maxDate - minDate)) * plotWidth;

    const yScale = (pe: number) =>
      padTop + (1 - (pe - yMin) / (yMax - yMin)) * plotHeight;

    // Build line path
    const linePoints = parsed.map((d) => `${xScale(d.date)},${yScale(d.pe)}`);
    const linePath = `M ${linePoints.join(" L ")}`;

    // Build area path (line + close to bottom)
    const bottomY = padTop + plotHeight;
    const firstX = xScale(parsed[0].date);
    const lastX = xScale(parsed[parsed.length - 1].date);
    const areaPath = `M ${firstX},${bottomY} L ${linePoints.join(" L ")} L ${lastX},${bottomY} Z`;

    const dateLabels = [
      parsed[0].date,
      parsed[Math.floor(parsed.length / 2)].date,
      parsed[parsed.length - 1].date,
    ];

    const yLabels = [yMin, (yMin + yMax) / 2, yMax];

    return {
      width,
      chartHeight,
      padLeft,
      padRight,
      padTop,
      padBottom,
      plotWidth,
      plotHeight,
      yScale,
      xScale,
      linePath,
      areaPath,
      dateLabels,
      yLabels,
    };
  }, [data, opportunity, danger, height, containerWidth]);

  if (!chartData) {
    return (
      <div ref={containerRef} className="w-full flex items-center justify-center vt-engraved text-sm" style={{ height: `${height}px` }}>
        暂无数据
      </div>
    );
  }

  const {
    width,
    chartHeight,
    padLeft,
    padRight,
    padTop,
    plotWidth,
    plotHeight,
    yScale,
    linePath,
    areaPath,
    dateLabels,
    yLabels,
  } = chartData;

  return (
    <div ref={containerRef} className="w-full" style={{ height: `${chartHeight}px` }}>
      <svg width={width} height={chartHeight} style={{ display: "block" }}>
        {/* Grid lines - horizontal */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = padTop + ratio * plotHeight;
          return (
            <line
              key={`grid-h-${ratio}`}
              x1={padLeft}
              y1={y}
              x2={padLeft + plotWidth}
              y2={y}
              stroke="#2d251a"
              strokeWidth={1}
            />
          );
        })}

        {/* Shaded area - light blue */}
        <path
          d={areaPath}
          fill="rgba(74, 158, 255, 0.25)"
          stroke="none"
        />

        {/* PE line - light blue */}
        <path
          d={linePath}
          fill="none"
          stroke="#4a9eff"
          strokeWidth={1.5}
        />

        {/* Opportunity line - green dashed */}
        {opportunity !== null && (
          <>
            <line
              x1={padLeft}
              y1={yScale(opportunity)}
              x2={padLeft + plotWidth}
              y2={yScale(opportunity)}
              stroke="#22c55e"
              strokeWidth={1.5}
              strokeDasharray="5,3"
            />
            <text
              x={padLeft + plotWidth - 4}
              y={yScale(opportunity) - 4}
              textAnchor="end"
              fill="#22c55e"
              fontSize="10"
            >
              机会 {opportunity.toFixed(1)}
            </text>
          </>
        )}

        {/* Danger line - red dashed */}
        {danger !== null && (
          <>
            <line
              x1={padLeft}
              y1={yScale(danger)}
              x2={padLeft + plotWidth}
              y2={yScale(danger)}
              stroke="#ef4444"
              strokeWidth={1.5}
              strokeDasharray="5,3"
            />
            <text
              x={padLeft + plotWidth - 4}
              y={yScale(danger) - 4}
              textAnchor="end"
              fill="#ef4444"
              fontSize="10"
            >
              危险 {danger.toFixed(1)}
            </text>
          </>
        )}

        {/* Y axis labels */}
        {yLabels.map((label, i) => (
          <text
            key={`y-label-${i}`}
            x={padLeft - 4}
            y={yScale(label) + 3}
            textAnchor="end"
            fill="#b8a87d"
            fontSize="9"
            opacity={0.6}
          >
            {label.toFixed(0)}
          </text>
        ))}

        {/* X axis labels - dates */}
        {dateLabels.map((date, i) => {
          const x = padLeft + (i / 2) * plotWidth;
          return (
            <text
              key={`x-label-${i}`}
              x={x}
              y={padTop + plotHeight + 15}
              textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"}
              fill="#b8a87d"
              fontSize="9"
              opacity={0.6}
            >
              {date.toLocaleDateString("zh-CN", { year: "2-digit", month: "short" })}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
