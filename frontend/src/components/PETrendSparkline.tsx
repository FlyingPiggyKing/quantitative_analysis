"use client";

interface PETrendSparklineProps {
  peHistory: Array<{ date: string; pe: number | null }>;
  loading?: boolean;
  mobile?: boolean;
}

export default function PETrendSparkline({ peHistory, loading, mobile }: PETrendSparklineProps) {
  if (loading) {
    return (
      <svg width={mobile ? 60 : 80} height={mobile ? 24 : 30} viewBox={`0 0 ${mobile ? 60 : 80} ${mobile ? 24 : 30}`} className="opacity-40">
        <line x1="0" y1={mobile ? 12 : 15} x2={mobile ? 60 : 80} y2={mobile ? 12 : 15} stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 2" />
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

  const padding = mobile ? 2 : 4;
  const width = mobile ? 60 : 80;
  const height = mobile ? 24 : 30;
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
        strokeWidth={mobile ? 1 : 1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
