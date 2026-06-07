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

// ---------------------------------------------------------------------------
// Futu-backed main business composition (HK / US stocks)
// ---------------------------------------------------------------------------
/** A single item in a Futu `get_financials_revenue_breakdown` dimension. */
export interface FutuMainBusinessItem {
  item: string;
  /** Revenue in the stock's reporting currency (raw, not pre-divided). */
  revenue: number;
  /** Pre-computed percentage from Futu (e.g. 12.34 means 12.34%). */
  ratio_pct: number;
  currency_code: string;
}

/** Response from `GET /api/stock/main-business-futu?symbol=...`. */
export interface FutuMainBusinessResponse {
  symbol: string;
  code: string;
  market: "HK" | "US";
  period: string;
  currency_code: string;
  product: FutuMainBusinessItem[];
  region: FutuMainBusinessItem[];
  industry: FutuMainBusinessItem[];
  business: FutuMainBusinessItem[];
  has_distinct_industry: boolean;
  source: "futu";
  updated_at: string;
}

/** Response from `GET /api/stock/main-business-futu/history?symbol=...`. */
export interface FutuMainBusinessHistoryResponse {
  symbol: string;
  code: string;
  market: "HK" | "US";
  currency_code: string;
  periods: string[];
  items: Array<{
    item: string;
    currency_code: string;
    values: Array<{ period: string; revenue: number; ratio_pct: number }>;
  }>;
  source: "futu";
  updated_at: string;
}

/** Returns `null` on 4xx/5xx (including the 400 "Unsupported symbol" for A-share)
 *  OR when the backend returns `{data: null, error: "..."}`. The Futu backend
 *  wraps its payload in a `{data, error}` envelope (consistent with the other
 *  HK/US endpoints in this project); this fetcher unwraps `data` and surfaces
 *  the error envelope as `null`. */
export async function getFutuMainBusiness(
  symbol: string,
): Promise<FutuMainBusinessResponse | null> {
  try {
    const params = new URLSearchParams({ symbol });
    const res = await fetch(`${API_BASE}/api/stock/main-business-futu?${params.toString()}`);
    if (!res.ok) return null;
    const body = (await res.json()) as { data?: FutuMainBusinessResponse | null; error?: string | null };
    if (body.error || !body.data) return null;
    return body.data;
  } catch {
    return null;
  }
}

/** Returns `null` on 4xx/5xx OR when the backend returns `{data: null, error: "..."}`. */
export async function getFutuMainBusinessHistory(
  symbol: string,
  nPeriods: number = 4,
): Promise<FutuMainBusinessHistoryResponse | null> {
  try {
    const params = new URLSearchParams({ symbol, n_periods: String(nPeriods) });
    const res = await fetch(
      `${API_BASE}/api/stock/main-business-futu/history?${params.toString()}`,
    );
    if (!res.ok) return null;
    const body = (await res.json()) as { data?: FutuMainBusinessHistoryResponse | null; error?: string | null };
    if (body.error || !body.data) return null;
    return body.data;
  } catch {
    return null;
  }
}
