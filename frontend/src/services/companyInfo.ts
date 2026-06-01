const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CompanyInfo {
  ts_code: string;
  com_name: string | null;
  com_id: string | null;
  exchange: string | null;
  chairman: string | null;
  manager: string | null;
  secretary: string | null;
  /** Registered capital in 万元 (frontend divides by 10000 to display as 亿元) */
  reg_capital: number | null;
  setup_date: string | null;
  province: string | null;
  city: string | null;
  introduction: string | null;
  website: string | null;
  email: string | null;
  office: string | null;
  employees: number | null;
  main_business: string | null;
  business_scope: string | null;
}

export interface CompanyInfoResponse {
  data: CompanyInfo | null;
  error: string | null;
}

export async function getCompanyInfo(symbol: string): Promise<CompanyInfoResponse> {
  const res = await fetch(`${API_BASE}/api/stock/company?symbol=${encodeURIComponent(symbol)}`);
  if (!res.ok) {
    return { data: null, error: `HTTP ${res.status}` };
  }
  return res.json();
}
