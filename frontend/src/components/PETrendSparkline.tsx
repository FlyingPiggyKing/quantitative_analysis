"use client";

interface PETrendSparklineProps {
  peHistory: Array<{ date: string; pe: number | null }>;
  loading?: boolean;
}

export default function PETrendSparkline({ peHistory, loading }: PETrendSparklineProps) {
  if (loading) {
    return (
      <svg width="80" height="30" viewBox="0 0 80 30" className="opacity-40">
        <line x1="0" y1="15" x2="80" y2="15" stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 2" />
      </svg>
    );
  }

  const validData = peHistory.filter((d) => d.pe != null);
  if (validData.length === 0) {
    return <span className="text-slate-500 text-xs">-</span>;
  }

  const minPE = Math.min(...validData.map((d) => d.pe!));
  const maxPE = Math.max(...validData.map((d) => d.pe!));
  const range = maxPE - minPE || 1;

  const padding = 4;
  const width = 80;
  const height = 30;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const points = validData.map((d, i) => {
    const x = padding + (i / (validData.length - 1 || 1)) * chartWidth;
    const y = padding + (1 - (d.pe! - minPE) / range) * chartHeight;
    return `${x},${y}`;
  });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke="#60a5fa"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
