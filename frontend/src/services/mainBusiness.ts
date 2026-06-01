const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** A single normalized row in the main business composition response. */
export interface MainBusinessRow {
  item: string;
  /** Revenue in 元 (frontend divides by 1e8 for 亿元 display). */
  sales: number;
  profit: number | null;
  cost: number | null;
  curr_type: string;
  revenue_share_pct: number;
  profit_share_pct: number | null;
  gross_margin_pct: number | null;
  /** True for inter-segment adjustment rows (e.g. 内部抵销, 抵减, 合计).
   *  These rows have negative sales and are excluded from the stacked bar. */
  is_adjustment?: boolean;
}

export interface MainBusinessResponse {
  ts_code: string;
  period: string | null;
  type: "P" | "D" | "I";
  rows: MainBusinessRow[];
  /** Sum of positive bz_sales (the gross total before inter-segment elimination). */
  gross_sales?: number;
  /** Net sum of all bz_sales including adjustment rows. */
  total_sales?: number;
  source?: string;
  updated_at?: string;
  error?: string;
}

export interface MainBusinessHistoryValue {
  period: string;
  sales: number | null;
  profit: number | null;
  cost: number | null;
  gross_margin_pct: number | null;
  yoy_pct: number | null;
}

export interface MainBusinessHistorySeries {
  item: string;
  values: MainBusinessHistoryValue[];
}

export interface MainBusinessHistoryResponse {
  ts_code: string;
  type: "P" | "D" | "I";
  periods: string[];
  series: MainBusinessHistorySeries[];
  source?: string;
  updated_at?: string;
  error?: string;
}

export interface HasDistinctIndustryResponse {
  has_distinct: boolean;
  industry_items: string[];
  error?: string;
}

async function getJsonOrError<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: { error?: string } = {};
    try {
      detail = await res.json();
    } catch {
      // ignore
    }
    throw new Error(detail.error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function getMainBusiness(
  symbol: string,
  type: "P" | "D" | "I" = "P",
  period?: string,
): Promise<MainBusinessResponse> {
  const params = new URLSearchParams({ symbol, type });
  if (period) params.set("period", period);
  const res = await fetch(`${API_BASE}/api/stock/main-business?${params.toString()}`);
  return getJsonOrError<MainBusinessResponse>(res);
}

export async function getMainBusinessHistory(
  symbol: string,
  type: "P" | "D" | "I" = "P",
  top: number = 3,
): Promise<MainBusinessHistoryResponse> {
  const params = new URLSearchParams({ symbol, type, top: String(top) });
  const res = await fetch(`${API_BASE}/api/stock/main-business/history?${params.toString()}`);
  return getJsonOrError<MainBusinessHistoryResponse>(res);
}

export async function getHasDistinctIndustry(symbol: string): Promise<HasDistinctIndustryResponse> {
  const params = new URLSearchParams({ symbol });
  const res = await fetch(`${API_BASE}/api/stock/main-business/has-distinct-industry?${params.toString()}`);
  return getJsonOrError<HasDistinctIndustryResponse>(res);
}
