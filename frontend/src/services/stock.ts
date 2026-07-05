const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ValuationRecord {
  trade_date: string;
  pe_ttm: number | null;
  pb: number | null;
  turnover_rate: number | null;
  total_mv: number | null;
  circ_mv: number | null;
  // ETF-specific fields (only populated when is_etf=true on ValuationResponse).
  dividend_yield?: number | null;
  dividend_rate?: number | null;
  as_of?: string | null;
}

export interface ValuationResponse {
  symbol: string;
  data?: ValuationRecord[];
  latest?: ValuationRecord;
  error?: string;
  // True when the symbol is recognised as a US ETF and the latest record was
  // merged with yahooquery fundamentals. False (or absent for non-US markets)
  // for regular stocks.
  is_etf?: boolean;
}

export async function fetchStockValuation(
  symbol: string,
  days: number = 30
): Promise<ValuationResponse> {
  const res = await fetch(`${API_BASE}/api/stock/${symbol}/valuation?days=${days}`);
  return res.json();
}
