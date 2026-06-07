const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** A single free-form label row from Futu get_company_profile.
 *
 * `fieldType` is the Futu protobuf field discriminator:
 *   0 = SourceText (plain text)
 *   1 = LinkType (a clickable URL)
 *   2 = IndependentTitle
 */
export interface CompanyLabel {
  name: string;
  value: string;
  fieldType: 0 | 1 | 2;
}

/** A single director / executive row from Futu get_company_executives. */
export interface CompanyExecutive {
  name: string | null;
  displayName: string | null;
  position: string | null;
  beginDate: string | null;
  gender: string | null;
  age: string | null;
  education: string | null;
  annualSalary: number | null;
}

/** Tagged union: a single type covers A-share (Tushare) and HK/US (Futu) responses.
 *
 * The A-share path populates only the legacy Tushare fields (com_name, chairman, ...).
 * The HK/US path populates only the Futu fields (profile_labels, executives, name, market).
 * The panel component picks the layout by `market`.
 */
export interface CompanyInfo {
  market: "A" | "HK" | "US";

  // A-share (Tushare) fields — null/undefined for HK/US responses.
  ts_code?: string | null;
  com_name?: string | null;
  com_id?: string | null;
  exchange?: string | null;
  chairman?: string | null;
  manager?: string | null;
  secretary?: string | null;
  /** Registered capital in 万元 (frontend divides by 10000 to display as 亿元) */
  reg_capital?: number | null;
  setup_date?: string | null;
  province?: string | null;
  city?: string | null;
  introduction?: string | null;
  website?: string | null;
  email?: string | null;
  office?: string | null;
  employees?: number | null;
  main_business?: string | null;
  business_scope?: string | null;

  // HK/US (Futu) fields — empty arrays for A-share responses.
  /** Best-effort derived company name (first text-type profile label with non-empty value). */
  name?: string;
  profile_labels: CompanyLabel[];
  executives: CompanyExecutive[];
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
