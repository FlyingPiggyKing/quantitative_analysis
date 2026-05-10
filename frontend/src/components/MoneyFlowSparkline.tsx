"use client";

interface MoneyFlowSparklineProps {
  flowHistory: Array<{ date: string; flow: number | null }>;
  loading?: boolean;
  mobile?: boolean;
}

export default function MoneyFlowSparkline({ flowHistory, loading, mobile }: MoneyFlowSparklineProps) {
  if (loading) {
    return (
      <svg width={mobile ? 60 : 80} height={mobile ? 24 : 30} viewBox={`0 0 ${mobile ? 60 : 80} ${mobile ? 24 : 30}`} className="opacity-40">
        <line x1="0" y1={mobile ? 12 : 15} x2={mobile ? 60 : 80} y2={mobile ? 12 : 15} stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 2" />
      </svg>
    );
  }

  const validData = flowHistory.filter((d) => d.flow != null);
  if (validData.length === 0) {
    return <span className="text-slate-500 text-xs">-</span>;
  }

  // Determine color based on 5-day trend
  const isPositive = validData.length >= 5
    ? validData.slice(-5).reduce((sum, d) => sum + (d.flow ?? 0), 0) >= 0
    : (validData[validData.length - 1]?.flow ?? 0) >= 0;

  const color = isPositive ? "#ef4444" : "#22c55e"; // red for inflow, green for outflow

  // For sparkline, we show the flow values centered around 0
  // Find min and max to determine range
  const flows = validData.map(d => d.flow!);
  const minFlow = Math.min(...flows);
  const maxFlow = Math.max(...flows);
  const range = maxFlow - minFlow || 1;
  const absMax = Math.max(Math.abs(minFlow), Math.abs(maxFlow));

  const padding = mobile ? 2 : 4;
  const width = mobile ? 60 : 80;
  const height = mobile ? 24 : 30;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  // Center the line around the middle of the chart (0 baseline)
  // Scale based on absMax so both positive and negative are visible
  const scale = absMax > 0 ? (chartHeight / 2) / absMax : 1;

  const points = validData.map((d, i) => {
    const x = padding + (i / (validData.length - 1 || 1)) * chartWidth;
    // y = middle - flow * scale (so positive flows go up)
    const y = padding + chartHeight / 2 - (d.flow! * scale);
    return `${x},${y}`;
  });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {/* Zero baseline */}
      <line
        x1={padding}
        y1={padding + chartHeight / 2}
        x2={padding + chartWidth}
        y2={padding + chartHeight / 2}
        stroke="#374151"
        strokeWidth="0.5"
        strokeDasharray="2 2"
      />
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={mobile ? 1 : 1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
