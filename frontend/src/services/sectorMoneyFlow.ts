const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SectorMoneyFlowResponse {
  sectors: string[];
  daily_top: Record<string, string[]>;
  net_amounts: Record<string, Record<string, number>>;
  error?: string;
}

export async function fetchSectorMoneyFlow(
  days: number = 5,
  top_n: number = 6
): Promise<SectorMoneyFlowResponse> {
  const res = await fetch(
    `${API_BASE}/api/stock/sector-money-flow?days=${days}&top_n=${top_n}`
  );
  return res.json();
}
