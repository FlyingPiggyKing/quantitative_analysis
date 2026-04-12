const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ValuationRecord {
  trade_date: string;
  pe_ttm: number | null;
  pb: number | null;
  turnover_rate: number | null;
  total_mv: number | null;
  circ_mv: number | null;
}

export interface ValuationResponse {
  symbol: string;
  data?: ValuationRecord[];
  latest?: ValuationRecord;
  error?: string;
}

export async function fetchStockValuation(
  symbol: string,
  days: number = 30
): Promise<ValuationResponse> {
  const res = await fetch(`${API_BASE}/api/stock/${symbol}/valuation?days=${days}`);
  return res.json();
}
