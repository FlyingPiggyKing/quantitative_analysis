const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface IndexMetricData {
  ts_code: string;
  name?: string;
  years: number;
  current_pe: number | null;  // PE for SW indices, PE_TTM for broad indices
  opportunity: number | null;
  danger: number | null;
  current_percentile: number | null;
  historical_high: number | null;
  historical_low: number | null;
  error?: string;
}

export interface IndexInfo {
  name: string;
  ts_code: string;
}

export interface PEHistoryItem {
  trade_date: string;
  pe: number;
}

export interface IndexHistoryResponse {
  ts_code: string;
  name?: string;
  years: number;
  data: PEHistoryItem[];
  error?: string;
}

export interface IndexMetricsResponse {
  indices?: IndexInfo[];
  error?: string;
}

export interface IndustryInfo {
  name: string;
  ts_code: string;
}

export interface IndustryListResponse {
  industries?: IndustryInfo[];
  error?: string;
}

export interface SubIndustryInfo {
  name: string;
  ts_code: string;
}

export interface SubIndustryListResponse {
  sub_industries?: SubIndustryInfo[];
  error?: string;
}

export async function fetchIndexList(): Promise<IndexMetricsResponse> {
  const res = await fetch(`${API_BASE}/api/index/list`);
  return res.json();
}

export async function fetchIndustryList(): Promise<IndustryListResponse> {
  const res = await fetch(`${API_BASE}/api/index/industry/list`);
  return res.json();
}

export async function fetchSubIndustryList(ts_code: string): Promise<SubIndustryListResponse> {
  const res = await fetch(`${API_BASE}/api/index/industry/subindustry?ts_code=${ts_code}`);
  return res.json();
}

export async function fetchIndexMetrics(
  ts_code: string,
  years: number = 10
): Promise<IndexMetricData> {
  const res = await fetch(`${API_BASE}/api/index/metrics?ts_code=${ts_code}&years=${years}`);
  return res.json();
}

export async function fetchIndexHistory(
  ts_code: string,
  years: number = 10
): Promise<IndexHistoryResponse> {
  const res = await fetch(`${API_BASE}/api/index/history?ts_code=${ts_code}&years=${years}`);
  return res.json();
}
