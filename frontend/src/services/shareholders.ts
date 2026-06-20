const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// HK / US shareholder research (Futu protos 3237/3238/3239 + holding_changes)
// ---------------------------------------------------------------------------
/** A single row from ``get_shareholders_overview.main_holder`` /
 *  ``holder_type``. ``holder_id`` is ``null`` for the synthetic "Other"
 *  row in ``main_holder`` and for every row in ``holder_type``. */
export interface ShareholderRow {
  static_date: number | null;
  static_date_str: string;
  name: string;
  /** Percentage (e.g. 23.09 means 23.09%). */
  holder_pct: number;
  holder_id: number | null;
}

/** Report period list from ``get_shareholders_overview.holding_period``. */
export interface HoldingPeriod {
  period_text: string;
  period_id: number | null;
}

/** Response from ``GET /api/stock/shareholders-futu/overview?symbol=...``. */
export interface ShareholdersOverviewResponse {
  symbol: string;
  code: string;
  market: "HK" | "US";
  main_holder: ShareholderRow[];
  holder_type: ShareholderRow[];
  holding_period: HoldingPeriod[];
  source: "futu";
  updated_at: string;
}

/** One quarterly period from the institutional aggregate. */
export interface ShareholdersInstitutionalRow {
  period_text: string;
  institution_quantity: number;
  institution_quantity_change: number;
  holder_quantity: number;
  holder_quantity_change: number;
  /** Percentage (e.g. 46.7 means 46.7%). */
  holder_pct: number;
  holder_pct_change: number;
  update_time_str: string;
}

/** Response from ``GET /api/stock/shareholders-futu/institutional?symbol=...&n_periods=...``. */
export interface ShareholdersInstitutionalResponse {
  symbol: string;
  code: string;
  market: "HK" | "US";
  periods: ShareholdersInstitutionalRow[];
  has_more: boolean;
  source: "futu";
  updated_at: string;
}

/** A single holder-detail row. ``close_price`` is the latest snapshot price
 *  across all rows in a single period (a known Futu-side quirk — NOT the
 *  historical close on ``holding_date``); used as informational only. */
export interface ShareholdersHolderDetailRow {
  period_text: string;
  holder_id: number | null;
  name: string;
  holder_quantity: number;
  holder_quantity_change: number;
  holder_pct: number;
  holder_pct_change: number;
  holding_date: number | null;
  holding_date_str: string;
  close_price: number;
  price_change_pct: number;
  source_group_name: string;
  update_time_str: string;
}

/** Response from ``GET /api/stock/shareholders-futu/holder-detail?symbol=...``. */
export interface ShareholdersHolderDetailResponse {
  symbol: string;
  code: string;
  market: "HK" | "US";
  rows: ShareholdersHolderDetailRow[];
  next_key: string;
  has_more: boolean;
  source: "futu";
  updated_at: string;
}

/** A single holding-changes row (increases or decreases). */
export interface ShareholdersHoldingChangesRow {
  period_text: string;
  name: string;
  holder_id: number | null;
  share_change_num: number;
  shares_change_price: number;
  share_ratio: number;
  holder_type: string;
  holder_type_id: number | null;
  holding_date: number | null;
  holding_date_str: string;
  share_ratio_change: number;
  share_num: number;
}

/** Response from ``GET /api/stock/shareholders-futu/holding-changes?symbol=...&filter_type=...``. */
export interface ShareholdersHoldingChangesResponse {
  symbol: string;
  code: string;
  market: "HK" | "US";
  rows: ShareholdersHoldingChangesRow[];
  next_key: string;
  has_more: boolean;
  source: "futu";
  updated_at: string;
}

/** All four endpoints wrap their payload in ``{data, error}``. This fetcher
 *  unwraps ``data`` and returns ``null`` when the backend signals
 *  ``error`` or ``data === null`` (e.g. older OpenD / A-share 400 / etc.). */
async function fetchShareholders<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const body = (await res.json()) as { data?: T | null; error?: string | null };
    if (body.error || !body.data) return null;
    return body.data;
  } catch {
    return null;
  }
}

/** HK/US shareholder overview (top holders + holder type + holding period list). */
export async function getShareholdersOverview(
  symbol: string,
): Promise<ShareholdersOverviewResponse | null> {
  const params = new URLSearchParams({ symbol });
  return fetchShareholders<ShareholdersOverviewResponse>(
    `${API_BASE}/api/stock/shareholders-futu/overview?${params.toString()}`,
  );
}

/** HK/US institutional-holding aggregate over the last ``nPeriods`` periods
 *  (server-side paginated; cap 50). */
export async function getShareholdersInstitutional(
  symbol: string,
  nPeriods: number = 30,
): Promise<ShareholdersInstitutionalResponse | null> {
  const params = new URLSearchParams({
    symbol,
    n_periods: String(nPeriods),
  });
  return fetchShareholders<ShareholdersInstitutionalResponse>(
    `${API_BASE}/api/stock/shareholders-futu/institutional?${params.toString()}`,
  );
}

/** HK/US shareholder-detail rows. Without filters returns a paginated top-N
 *  list; set ``holder_id`` to drill into a single holder's cross-period
 *  history; set ``period_id`` to scope to a single report period. */
export async function getShareholdersHolderDetail(
  symbol: string,
  opts: {
    holder_id?: number | null;
    period_id?: number | null;
    num?: number;
    next_key?: string | null;
  } = {},
): Promise<ShareholdersHolderDetailResponse | null> {
  const params = new URLSearchParams({ symbol });
  if (opts.holder_id != null) params.set("holder_id", String(opts.holder_id));
  if (opts.period_id != null) params.set("period_id", String(opts.period_id));
  if (opts.num != null) params.set("num", String(opts.num));
  if (opts.next_key != null && opts.next_key !== "") {
    params.set("next_key", opts.next_key);
  }
  return fetchShareholders<ShareholdersHolderDetailResponse>(
    `${API_BASE}/api/stock/shareholders-futu/holder-detail?${params.toString()}`,
  );
}

/** HK/US latest-period holding changes.
 *  ``filter_type=1`` → increases (增持), ``filter_type=2`` → decreases (减持).
 *  The Futu SDK does NOT accept a ``holder_id`` parameter on this endpoint —
 *  per-holder reduction history goes through ``getShareholdersHolderDetail({holder_id})`` instead. */
export async function getShareholdersHoldingChanges(
  symbol: string,
  filterType: 1 | 2 = 1,
  opts: { num?: number; next_key?: string | null } = {},
): Promise<ShareholdersHoldingChangesResponse | null> {
  const params = new URLSearchParams({
    symbol,
    filter_type: String(filterType),
  });
  if (opts.num != null) params.set("num", String(opts.num));
  if (opts.next_key != null && opts.next_key !== "") {
    params.set("next_key", opts.next_key);
  }
  return fetchShareholders<ShareholdersHoldingChangesResponse>(
    `${API_BASE}/api/stock/shareholders-futu/holding-changes?${params.toString()}`,
  );
}
