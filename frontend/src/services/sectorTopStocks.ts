const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StockTopInfo {
  ts_code: string;
  name: string;
  net_inflow: number;
  pe_ttm: number | null;
  total_mv_yi: number | null;
}

export interface SectorTopStocksResponse {
  sector: string;
  index_code: string | null;
  matched_name: string | null;
  by_date: Record<string, StockTopInfo[]>;
  error?: string | null;
}

export async function fetchSectorTopStocks(
  sector: string,
  dates: string[],
  top_n: number = 5
): Promise<SectorTopStocksResponse> {
  const res = await fetch(
    `${API_BASE}/api/stock/sector-top-stocks?sector=${encodeURIComponent(sector)}&dates=${dates.join(",")}&top_n=${top_n}`
  );
  return res.json();
}
