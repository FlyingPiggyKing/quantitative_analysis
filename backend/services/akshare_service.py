"""Stock data service using Tushare Pro API."""
import os
import logging
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

# Get yfinance proxy setting (ONLY read, don't set environment variables yet)
_yf_proxy = os.environ.get("YF_PROXY")
logger.info(f"[PROXY] YF_PROXY={_yf_proxy}")
logger.info(f"[PROXY] Tushare: NO PROXY (direct connection to China)")

# Set NO_PROXY to exclude services that should NOT use proxy
# This is read from .env or uses a sensible default
_no_proxy = os.environ.get("NO_PROXY", "api.smith.langchain.com,api.minimaxi.com,api.tavily.com,tavily.dev,localhost,127.0.0.1")
os.environ["NO_PROXY"] = _no_proxy
os.environ["no_proxy"] = _no_proxy
logger.info(f"[PROXY] NO_PROXY={_no_proxy}")

# Import yfinance AFTER dotenv is loaded
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

# Tushare token from environment variable
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
if TUSHARE_TOKEN:
    ts.set_token(TUSHARE_TOKEN)


class _YFCache:
    """Simple in-memory cache for Yahoo Finance data with TTL.

    Prevents repeated API calls for the same symbol within TTL seconds.
    Uses stale-on-error strategy: returns stale cache if rate limited.
    """
    def __init__(self, ttl: int = 300):  # 5 minutes default TTL
        self._ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value if not expired."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self._ttl:
                    return entry["data"]
                # Expired - remove it
                del self._cache[key]
        return None

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Cache a value."""
        with self._lock:
            self._cache[key] = {
                "data": data,
                "timestamp": time.time()
            }

    def get_or_fetch(self, key: str, fetch_func) -> Dict[str, Any]:
        """Get from cache or fetch if not cached/expired."""
        cached = self.get(key)
        if cached is not None:
            logger.info(f"[美股] Cache hit for {key}")
            return cached

        logger.info(f"[美股] Cache miss for {key}, fetching...")
        result = fetch_func()
        self.set(key, result)
        return result

    def on_error_return_stale(self, key: str, fetch_func, max_stale_seconds: int = 3600) -> Dict[str, Any]:
        """On error (e.g., rate limit), return stale cache if available."""
        try:
            return self.get_or_fetch(key, fetch_func)
        except Exception as e:
            # On error, try to return stale cache
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    age = time.time() - entry["timestamp"]
                    if age < max_stale_seconds:
                        logger.warning(f"[美股] {key} error, returning stale cache (age: {age:.0f}s)")
                        return entry["data"]
            # No stale cache, re-raise
            raise


# Global cache for US stock data - 5 minute TTL
_yf_cache = _YFCache(ttl=300)

# Global cache for A-share company info (Tushare stock_company) - 24 hour TTL
# Company profile data rarely changes; long TTL keeps us well under the 120-point rate limit.
_company_cache = _YFCache(ttl=86400)

# Global cache for A-share main business composition (Tushare fina_mainbz) - 24 hour TTL
# Main business data updates only on quarterly reports; long TTL keeps us well under
# the 2000-point rate limit.
_main_biz_cache = _YFCache(ttl=86400)


# Simple sector money flow cache - 5 minute TTL
_sector_mf_cache: Dict[str, Any] = {}
_sector_mf_cache_time: float = 0
_SECTOR_MF_CACHE_TTL: int = 300  # 5 minutes

# SW2021 classification table cache - refreshed daily
_sw_classify_cache: Dict[str, Any] = {}
_sw_classify_cache_date: str = ""  # YYYYMMDD of last fetch

# Index member cache - keyed by index_code, refreshed daily
_index_member_cache: Dict[str, Any] = {}
_index_member_cache_date: str = ""

# Stock basic name cache - refreshed daily
_stock_basic_name_cache: Dict[str, str] = {}  # ts_code -> name
_stock_basic_name_cache_date: str = ""

# Per-date moneyflow cache - keyed by trade_date (YYYYMMDD), long TTL for closed days
_moneyflow_day_cache: Dict[str, Any] = {}  # trade_date -> {ts_code: net_inflow_yi}
_moneyflow_day_cache_time: Dict[str, float] = {}
_MONEYFLOW_DAY_CACHE_TTL_CLOSED: int = 86400  # 24 hours for closed days
_MONEYFLOW_DAY_CACHE_TTL_TODAY: int = 300  # 5 minutes for today

# Per-date stock basics cache - keyed by trade_date (YYYYMMDD), long TTL for closed days
# Value: {ts_code: {pe_ttm, total_mv_yi}}
_stock_basics_cache: Dict[str, Dict[str, Any]] = {}
_stock_basics_cache_time: Dict[str, float] = {}
_STOCK_BASICS_CACHE_TTL_CLOSED: int = 86400
_STOCK_BASICS_CACHE_TTL_TODAY: int = 300


def _get_cached_sector_mf(days: int, top_n: int, fetch_func) -> dict:
    """Get sector money flow from cache or fetch if expired."""
    global _sector_mf_cache, _sector_mf_cache_time
    cache_key = f"{days}_{top_n}"
    current_time = time.time()

    if _sector_mf_cache and (current_time - _sector_mf_cache_time) < _SECTOR_MF_CACHE_TTL:
        logger.info(f"[A股] Sector moneyflow cache hit for {cache_key}")
        return _sector_mf_cache

    logger.info(f"[A股] Sector moneyflow cache miss for {cache_key}, fetching...")
    result = fetch_func()
    _sector_mf_cache = result
    _sector_mf_cache_time = current_time
    return result


class _ProxyContext:
    """Context manager for yfinance proxy - temporarily sets proxy for yfinance calls.

    IMPORTANT: This context manager properly isolates yfinance proxy settings from Tushare.
    It ensures that proxy environment variables are ONLY set within this context
    and are always cleaned up afterwards, even if an exception occurs.
    """
    def __init__(self):
        self._proxy = _yf_proxy

    def __enter__(self):
        if self._proxy:
            # Save and set proxy env vars ONLY for yfinance
            os.environ["https_proxy"] = self._proxy
            os.environ["http_proxy"] = self._proxy
            logger.info(f"[PROXY] Enabled proxy: {self._proxy}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._proxy:
            # CRITICAL: Always remove proxy env vars so Tushare doesn't use them
            os.environ.pop("https_proxy", None)
            os.environ.pop("http_proxy", None)
            logger.info("[PROXY] Disabled proxy")
        return False  # Don't suppress exceptions


def _symbol_to_ts_code(symbol: str) -> str:
    """Convert A-share symbol to Tushare ts_code format."""
    symbol = symbol.strip()

    if "." in symbol:
        return symbol.upper()

    if len(symbol) == 6:
        if symbol.startswith(('6', '9', '5')):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"
    return symbol


def _safe_float(val) -> Optional[float]:
    """Convert pandas/NumPy value to float or None."""
    try:
        if pd.isna(val):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


# Keywords that mark a fina_mainbz row as an inter-segment adjustment rather than a real product.
# These rows (e.g. 内部抵销, 抵减, 合计) carry negative values that net out inter-segment revenue
# and should not be treated as first-class products in the visualization.
_ADJUSTMENT_KEYWORDS = ("抵销", "抵减", "调整", "合计")


def _is_adjustment_row(item: str, sales: float) -> bool:
    """True if a fina_mainbz row is an inter-segment adjustment (not a real product)."""
    if sales < 0:
        return True
    return any(kw in str(item) for kw in _ADJUSTMENT_KEYWORDS)


def _build_series_for_item(df, periods, item, ts_code, type_code):
    """Build a single-item time series across `periods` from a fina_mainbz DataFrame.

    Returns ``{item, values: [{period, sales, profit, cost, gross_margin_pct, yoy_pct}]}``.
    """
    values = []
    for p in periods:
        match = df[(df["end_date"].astype(str) == str(p)) & (df["bz_item"] == item)]
        if match.empty:
            values.append({"period": p, "sales": None, "profit": None,
                           "cost": None, "gross_margin_pct": None, "yoy_pct": None})
            continue
        row = match.iloc[0]
        sales = _safe_float(row.get("bz_sales"))
        profit = _safe_float(row.get("bz_profit"))
        cost = _safe_float(row.get("bz_cost"))
        gm = ((sales - cost) / sales * 100) if (sales and cost is not None) else None
        values.append({
            "period": p, "sales": sales, "profit": profit, "cost": cost,
            "gross_margin_pct": round(gm, 2) if gm is not None else None,
            "yoy_pct": None,  # filled in after the loop
        })

    # Compute yoy_pct now that we have the full series.
    prev = None
    for v in values:
        if v["sales"] is not None and prev is not None and prev > 0:
            v["yoy_pct"] = round((v["sales"] - prev) / prev * 100, 2)
        prev = v["sales"] if v["sales"] is not None else prev

    return {"item": item, "values": values}


def _build_series_for_others(df, periods, other_items, ts_code, type_code, top_items):
    """Aggregate the non-top items into a single "其他" series across `periods`."""
    values = []
    for p in periods:
        period_df = df[(df["end_date"].astype(str) == str(p)) & (df["bz_item"].isin(other_items))]
        if period_df.empty:
            values.append({"period": p, "sales": None, "profit": None,
                           "cost": None, "gross_margin_pct": None, "yoy_pct": None})
            continue
        sales = _safe_float(period_df["bz_sales"].sum())
        profit = _safe_float(period_df["bz_profit"].sum())
        cost = _safe_float(period_df["bz_cost"].sum())
        gm = ((sales - cost) / sales * 100) if (sales and cost is not None) else None
        values.append({
            "period": p, "sales": sales, "profit": profit, "cost": cost,
            "gross_margin_pct": round(gm, 2) if gm is not None else None,
            "yoy_pct": None,
        })

    prev = None
    for v in values:
        if v["sales"] is not None and prev is not None and prev > 0:
            v["yoy_pct"] = round((v["sales"] - prev) / prev * 100, 2)
        prev = v["sales"] if v["sales"] is not None else prev

    return {"item": "其他", "values": values}


def _us_symbol_to_yf_code(symbol: str) -> str:
    """Convert US stock symbol to Yahoo Finance format (strip .US suffix, uppercase)."""
    symbol = symbol.strip().upper()
    if symbol.endswith(".US"):
        return symbol[:-3]
    return symbol


class AShareService:
    """Service wrapper for A-share stock data via Tushare Pro API."""

    @staticmethod
    def get_stock_info(symbol: str) -> dict:
        """Get basic A-share stock information."""
        logger.info(f"[A股] Fetching info for {symbol} via Tushare (NO PROXY)")
        try:
            ts_code = _symbol_to_ts_code(symbol)

            # Try realtime quotes first (faster, less likely to rate limit)
            try:
                quotes = ts.get_realtime_quotes(symbol)
                if quotes is not None and not quotes.empty:
                    name = quotes.iloc[0].get("name", "未知")
                    if name and name != "unknown":
                        logger.info(f"[A股] {symbol} found via realtime quotes")
                        return {
                            "symbol": symbol,
                            "name": name,
                            "market": "A",
                            "sector": "未知",
                        }
            except Exception as e:
                logger.warning(f"[A股] {symbol} realtime quotes failed: {e}")

            # Fallback to stock_basic with timeout handling
            try:
                df = ts.pro_api().stock_basic(ts_code=ts_code, fields='ts_code,symbol,name,area,industry,market,list_date')
                if df is not None and not df.empty:
                    row = df.iloc[0]
                    logger.info(f"[A股] {symbol} found via stock_basic")
                    return {
                        "symbol": symbol,
                        "name": row.get("name", "未知"),
                        "market": "A",
                        "sector": row.get("industry", "未知"),
                    }
            except Exception as e:
                logger.warning(f"[A股] {symbol} stock_basic failed: {e}")
                # If it's a rate limit error, don't try more endpoints (they'll also fail)
                if "权限" in str(e) or "每分钟" in str(e) or "Connection" in str(e):
                    return {"symbol": symbol, "error": f"Tushare rate limited: {str(e)[:50]}"}

            return {"symbol": symbol, "error": "Stock not found"}
        except Exception as e:
            logger.error(f"[A股] {symbol} error: {e}")
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_kline_data(
        symbol: str,
        days: int = 100,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> dict:
        """Get K-line data for an A-share stock."""
        try:
            ts_code = _symbol_to_ts_code(symbol)
            pro = ts.pro_api()

            # Determine date range
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            # Fetch daily data
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return {"symbol": symbol, "error": "No data found"}

            # Rename columns
            df = df.rename(columns={
                "trade_date": "date",
                "vol": "volume",
                "pct_chg": "change_pct"
            })

            # Convert date format
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

            # Sort by date
            df = df.sort_values("date")

            # Take last N days
            df = df.tail(days)

            data = df[["date", "open", "close", "high", "low", "volume", "amount", "change_pct"]].to_dict("records")

            return {
                "symbol": symbol,
                "period": period,
                "data": data
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_realtime_quote(symbol: str) -> dict:
        """Get real-time quote for an A-share stock."""
        try:
            ts_code = _symbol_to_ts_code(symbol)

            # Use realtime quotes
            quotes = ts.get_realtime_quotes(ts_code)
            if quotes is None or quotes.empty:
                return {"symbol": symbol, "error": "Stock not found"}

            row = quotes.iloc[0]

            def safe_float(val):
                try:
                    return float(val)
                except:
                    return 0.0

            return {
                "symbol": symbol,
                "name": row.get("name", "未知"),
                "price": safe_float(row.get("price", 0)),
                "change_pct": safe_float(row.get("price", 0)) - safe_float(row.get("pre_close", 0)),
                "volume": safe_float(row.get("volume", 0)),
                "amount": safe_float(row.get("amount", 0)),
                "high": safe_float(row.get("high", 0)),
                "low": safe_float(row.get("low", 0)),
                "open": safe_float(row.get("open", 0)),
                "close_prev": safe_float(row.get("pre_close", 0)),
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_company_info(symbol: str) -> dict:
        """Get A-share listed-company basic info from Tushare stock_company.

        Cached for 24h (company profile changes rarely). Returns shape
        ``{"data": <row or null>, "error": <str or null>}``.
        """
        try:
            ts_code = _symbol_to_ts_code(symbol)
        except Exception:
            return {"data": None, "error": "Invalid A-share symbol"}

        cache_key = f"company:{ts_code}"

        def fetch():
            pro = ts.pro_api()
            df = pro.stock_company(ts_code=ts_code)
            if df is None or df.empty:
                return {"data": None, "error": "未找到该公司信息"}
            row = df.iloc[0]

            def safe_str(val):
                if val is None:
                    return None
                try:
                    if pd.isna(val):
                        return None
                except (TypeError, ValueError):
                    pass
                s = str(val).strip()
                return s if s else None

            def safe_float(val):
                try:
                    return float(val) if pd.notna(val) else None
                except (TypeError, ValueError):
                    return None

            def safe_int(val):
                try:
                    return int(val) if pd.notna(val) else None
                except (TypeError, ValueError):
                    return None

            def safe_date(val):
                s = safe_str(val)
                if s is None:
                    return None
                # Tushare returns dates as 'YYYYMMDD'; normalize to 'YYYY-MM-DD'
                if len(s) == 8 and s.isdigit():
                    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
                return s

            return {
                "data": {
                    "market": "A",
                    "ts_code": safe_str(row.get("ts_code")) or ts_code,
                    "com_name": safe_str(row.get("com_name")),
                    "com_id": safe_str(row.get("com_id")),
                    "exchange": safe_str(row.get("exchange")),
                    "chairman": safe_str(row.get("chairman")),
                    "manager": safe_str(row.get("manager")),
                    "secretary": safe_str(row.get("secretary")),
                    "reg_capital": safe_float(row.get("reg_capital")),
                    "setup_date": safe_date(row.get("setup_date")),
                    "province": safe_str(row.get("province")),
                    "city": safe_str(row.get("city")),
                    "introduction": safe_str(row.get("introduction")),
                    "website": safe_str(row.get("website")),
                    "email": safe_str(row.get("email")),
                    "office": safe_str(row.get("office")),
                    "employees": safe_int(row.get("employees")),
                    "main_business": safe_str(row.get("main_business")),
                    "business_scope": safe_str(row.get("business_scope")),
                },
                "error": None,
            }

        try:
            return _company_cache.get_or_fetch(cache_key, fetch)
        except Exception as e:
            logger.warning(f"[A股] {ts_code} stock_company failed: {e}")
            return {"data": None, "error": f"获取公司信息失败: {str(e)[:120]}"}

    @staticmethod
    def get_main_business_composition(symbol: str, period: Optional[str] = None, type: str = "P") -> dict:
        """Get A-share main business composition from Tushare fina_mainbz (doc_id=81).

        Returns revenue / profit / cost rows for a given (ts_code, period, type),
        with derived share and margin metrics precomputed. Cached 24h per
        (ts_code, type, period) key.

        Args:
            symbol: 6-digit A-share code (e.g. "600519").
            period: Optional reporting period in YYYYMMDD. None = latest.
            type: One of "P" (product), "D" (region), "I" (industry).

        Returns:
            ``{ts_code, period, type, rows: [...], source: "tushare", updated_at}``
            on success; ``{rows: []}`` when Tushare returns nothing.
        """
        try:
            ts_code = _symbol_to_ts_code(symbol)
        except Exception:
            return {"rows": [], "error": "Invalid A-share symbol"}

        if type not in ("P", "D", "I"):
            return {"rows": [], "error": f"Invalid type '{type}', must be P/D/I"}

        cache_key = f"main_biz:{ts_code}:{type}:{period or 'latest'}"

        def fetch():
            pro = ts.pro_api()
            kwargs = {"ts_code": ts_code, "type": type}
            if period:
                kwargs["period"] = period
            df = pro.fina_mainbz(**kwargs)

            if df is None or df.empty:
                return {"ts_code": ts_code, "period": period, "type": type,
                        "rows": [], "source": "tushare", "updated_at": datetime.now().isoformat()}

            # When period is None, restrict to the most recent end_date in the response.
            if not period and "end_date" in df.columns and len(df):
                latest_end = str(df["end_date"].max())
                df = df[df["end_date"].astype(str) == latest_end].copy()
                actual_period = latest_end
            else:
                actual_period = str(df["end_date"].iloc[0]) if "end_date" in df.columns and len(df) else period

            # 1. Drop rows where bz_sales is NaN/0 (not meaningful).
            df = df[pd.notna(df["bz_sales"]) & (df["bz_sales"] != 0)].copy()

            # 2. Drop exact-duplicate (item, sales, cost, curr_type) tuples — keep first.
            #    Catches cases like 茅台 "系列酒" / "其他酒系列" with identical numbers.
            df = df.drop_duplicates(subset=["bz_item", "bz_sales", "bz_cost", "curr_type"], keep="first")

            # 3. Compute derived metrics; sort by sales desc.
            #    `gross_sales` = sum of positive values only (used for revenue_share_pct denominator
            #    so positive rows always sum to 100% in the visualization). `total_sales` = net sum
            #    including adjustment rows (used to surface the reconciliation in the footnote).
            gross_sales = float(df.loc[df["bz_sales"] > 0, "bz_sales"].sum()) if len(df) else 0.0
            total_sales = float(df["bz_sales"].sum()) if len(df) else 0.0
            total_profit = float(df["bz_profit"].sum()) if len(df) and pd.notna(df["bz_profit"]).any() else 0.0

            rows = []
            for _, row in df.iterrows():
                sales = float(row["bz_sales"]) if pd.notna(row["bz_sales"]) else 0.0
                profit_raw = row["bz_profit"]
                cost_raw = row["bz_cost"]
                profit = float(profit_raw) if pd.notna(profit_raw) else None
                cost = float(cost_raw) if pd.notna(cost_raw) else None
                item = str(row["bz_item"]).strip() if pd.notna(row["bz_item"]) else ""

                # revenue_share_pct uses gross (positive-only) as denominator so positive rows
                # naturally sum to ~100%. Adjustment rows get a negative share by the same math.
                revenue_share = (sales / gross_sales * 100) if gross_sales else 0.0
                profit_share = (profit / total_profit * 100) if (profit is not None and total_profit) else None
                gross_margin = ((sales - cost) / sales * 100) if (cost is not None and sales) else None
                is_adjustment = _is_adjustment_row(item, sales)

                rows.append({
                    "item": item,
                    "sales": sales,
                    "profit": profit,
                    "cost": cost,
                    "curr_type": str(row["curr_type"]).strip() if pd.notna(row.get("curr_type")) else "CNY",
                    "revenue_share_pct": round(revenue_share, 2),
                    "profit_share_pct": round(profit_share, 2) if profit_share is not None else None,
                    "gross_margin_pct": round(gross_margin, 2) if gross_margin is not None else None,
                    "is_adjustment": is_adjustment,
                })

            rows.sort(key=lambda r: r["sales"], reverse=True)

            return {
                "ts_code": ts_code,
                "period": actual_period,
                "type": type,
                "rows": rows,
                "gross_sales": gross_sales,
                "total_sales": total_sales,
                "source": "tushare",
                "updated_at": datetime.now().isoformat(),
            }

        try:
            return _main_biz_cache.get_or_fetch(cache_key, fetch)
        except Exception as e:
            logger.warning(f"[A股] {ts_code} fina_mainbz ({type}, {period}) failed: {e}")
            return {"rows": [], "error": f"获取主营业务构成失败: {str(e)[:120]}"}

    @staticmethod
    def get_main_business_history(symbol: str, type: str = "P", top: int = 3) -> dict:
        """Get last N annual periods of by-product (or by-region/industry) data for cross-period view.

        Computes top-N series by latest-period revenue, buckets the rest as `其他`,
        and computes yoy_pct per period (null for the earliest).

        Args:
            symbol: 6-digit A-share code.
            type: "P" / "D" / "I".
            top: Number of top series to keep; rest aggregated as "其他".

        Returns:
            ``{ts_code, type, periods, series: [{item, values: [{period, sales, profit,
            cost, gross_margin_pct, yoy_pct}]}], source: "tushare"}``
        """
        try:
            ts_code = _symbol_to_ts_code(symbol)
        except Exception:
            return {"rows": [], "error": "Invalid A-share symbol"}

        if type not in ("P", "D", "I"):
            return {"rows": [], "error": f"Invalid type '{type}', must be P/D/I"}

        # Last 4 annual periods (Dec 31). If current month >= 5, last year is finalized; else year-1.
        now = datetime.now()
        last_full_year = now.year if now.month >= 5 else now.year - 1
        periods = [f"{y}1231" for y in range(last_full_year - 3, last_full_year + 1)]
        latest_period = periods[-1]

        cache_key = f"main_biz_history:{ts_code}:{type}:{top}:{latest_period}"

        def fetch():
            pro = ts.pro_api()
            df = pro.fina_mainbz(ts_code=ts_code, type=type, end_date=latest_period)
            if df is None or df.empty:
                return {
                    "ts_code": ts_code, "type": type, "periods": periods,
                    "series": [], "source": "tushare",
                    "updated_at": datetime.now().isoformat(),
                }

            df = df[pd.notna(df["bz_sales"]) & (df["bz_sales"] != 0)].copy()
            df = df.drop_duplicates(subset=["end_date", "bz_item", "bz_sales", "bz_cost"], keep="first")

            # 1. Determine top-N items by latest period revenue.
            latest = df[df["end_date"].astype(str) == str(latest_period)]
            if latest.empty:
                latest_period_actual = str(df["end_date"].max())
                latest = df[df["end_date"].astype(str) == latest_period_actual]
            else:
                latest_period_actual = str(latest_period)

            top_items = (latest.sort_values("bz_sales", ascending=False)["bz_item"]
                         .head(top).tolist())
            # Exclude adjustment rows (inter-segment elimination) from the "其他" bucket so the
            # historical chart doesn't show a negative or misleading series.
            latest_items_with_sales = {
                i: float(latest.loc[latest["bz_item"] == i, "bz_sales"].iloc[0])
                for i in latest["bz_item"].unique()
            }
            other_items = [
                i for i, s in latest_items_with_sales.items()
                if i not in top_items and not _is_adjustment_row(i, s)
            ]

            # 2. Build per-item series across all 4 periods (with "其他" bucket).
            series = []
            for item in top_items:
                series.append(_build_series_for_item(df, periods, item, ts_code, type))
            if other_items:
                series.append(_build_series_for_others(df, periods, other_items, ts_code, type, top_items))

            return {
                "ts_code": ts_code,
                "type": type,
                "periods": periods,
                "series": series,
                "source": "tushare",
                "updated_at": datetime.now().isoformat(),
            }

        try:
            return _main_biz_cache.get_or_fetch(cache_key, fetch)
        except Exception as e:
            logger.warning(f"[A股] {ts_code} fina_mainbz history ({type}) failed: {e}")
            return {"periods": periods, "series": [], "error": f"获取跨期数据失败: {str(e)[:120]}"}

    @staticmethod
    def has_distinct_industry(symbol: str, period: Optional[str] = None) -> dict:
        """Check whether by-industry rows add items not present in by-product rows.

        Returns ``{has_distinct: bool, industry_items: [...]}``.
        """
        product = AShareService.get_main_business_composition(symbol, period=period, type="P")
        industry = AShareService.get_main_business_composition(symbol, period=period, type="I")
        product_items = {r["item"] for r in product.get("rows", [])}
        industry_items = {r["item"] for r in industry.get("rows", [])}
        distinct = bool(industry_items - product_items)
        return {"has_distinct": distinct, "industry_items": sorted(industry_items)}

    @staticmethod
    def get_daily_basic(symbol: str, days: int = 30) -> dict:
        """Get daily basic metrics (PE TTM, PB, turnover rate, market cap) from Tushare daily_basic."""
        try:
            ts_code = _symbol_to_ts_code(symbol)
            pro = ts.pro_api()

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            df = pro.daily_basic(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df is None or df.empty:
                return {"symbol": symbol, "error": "No daily_basic data"}

            df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
            df = df.sort_values("trade_date").tail(days)

            def safe_float(val):
                try:
                    return float(val) if pd.notna(val) else None
                except (TypeError, ValueError):
                    return None

            records = []
            for _, row in df.iterrows():
                records.append({
                    "trade_date": row["trade_date"],
                    "pe_ttm": safe_float(row.get("pe_ttm")),
                    "pb": safe_float(row.get("pb")),
                    "turnover_rate": safe_float(row.get("turnover_rate")),
                    "total_mv": safe_float(row.get("total_mv")),
                    "circ_mv": safe_float(row.get("circ_mv")),
                })

            return {
                "symbol": symbol,
                "data": records,
                "latest": records[-1] if records else {},
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_moneyflow(symbol: str, days: int = 30) -> dict:
        """Get A-share main force net inflow via Tushare moneyflow_ths API.

        Returns buy_lg_amount (主力大单净流入 in 万元) and net_d5_amount (5日累计).
        """
        try:
            ts_code = _symbol_to_ts_code(symbol)
            pro = ts.pro_api()

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            df = pro.moneyflow_ths(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return {"symbol": symbol, "market": "A-share", "error": "No moneyflow_ths data"}

            # Parse date format (Tushare returns as YYYYMMDD)
            if "trade_date" in df.columns:
                df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
            elif "date" in df.columns:
                df["trade_date"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

            df = df.sort_values("trade_date").tail(days)

            def safe_float(val):
                try:
                    return float(val) if pd.notna(val) else None
                except (TypeError, ValueError):
                    return None

            records = []
            for _, row in df.iterrows():
                records.append({
                    "trade_date": row["trade_date"],
                    "net_amount": safe_float(row.get("net_amount")),
                    "buy_lg_amount": safe_float(row.get("buy_lg_amount")),
                    "net_d5_amount": safe_float(row.get("net_d5_amount")),
                })

            # Use net_d5_amount from latest record as the official 5-day cumulative
            net_5d_total = records[-1].get("net_d5_amount") if records and records[-1].get("net_d5_amount") is not None else None

            return {
                "symbol": symbol,
                "market": "A-share",
                "data": records,
                "latest": records[-1] if records else {},
                "net_5d_total": net_5d_total,
            }
        except Exception as e:
            return {"symbol": symbol, "market": "A-share", "error": str(e)}

    @staticmethod
    def _fetch_sector_moneyflow(days: int, top_n: int) -> dict:
        """Internal fetch without caching."""
        try:
            pro = ts.pro_api()

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 3)).strftime("%Y%m%d")  # buffer for weekends

            df = pro.moneyflow_ind_dc(start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return {"sectors": [], "daily_top": {}, "net_amounts": {}, "error": "No data returned"}

            # Filter to only industry sectors (content_type = "行业")
            if "content_type" in df.columns:
                df = df[df["content_type"] == "行业"]

            if df.empty:
                return {"sectors": [], "daily_top": {}, "net_amounts": {}, "error": "No industry sector data"}

            # Parse date format (Tushare returns as YYYYMMDD)
            if "trade_date" in df.columns:
                df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

            def safe_float(val):
                try:
                    return float(val) if pd.notna(val) else 0.0
                except (TypeError, ValueError):
                    return 0.0

            # Build net_amounts dict: { date: { sector: amount_in_yi } }
            # net_amount is in 元, convert to 亿元 (/ 1e8)
            # Aggregate by sector name (sum) to handle same name with different DC codes
            net_amounts: Dict[str, Dict[str, float]] = {}
            all_sectors = set()

            for _, row in df.iterrows():
                date = row["trade_date"]
                sector = row.get("name", "未知")
                amount_in_yuan = safe_float(row.get("net_amount", 0))
                amount_in_yi = amount_in_yuan / 1e8  # 元 -> 亿元

                if date not in net_amounts:
                    net_amounts[date] = {}
                # Aggregate: sum if same sector name appears multiple times
                if sector in net_amounts[date]:
                    net_amounts[date][sector] += amount_in_yi
                else:
                    net_amounts[date][sector] = amount_in_yi
                all_sectors.add(sector)

            # Deduplicate roman-numeral variants. Tushare's DC source emits two
            # separate codes (e.g., BK1444.DC + BK1238.DC for "IT服务Ⅱ/Ⅲ") that
            # almost always carry identical net_amount — they're aliases of the
            # same sector, not distinct sub-sectors. Summing would double-count.
            # When variants disagree (rare, e.g. "其他电源设备"), they are real
            # sub-sectors and must stay separate.
            import re
            roman_pattern = r'[IVXⅰⅱⅲⅳⅴⅵⅷⅸⅹⅠ-Ⅿ]+$'
            for date in net_amounts:
                base_groups: Dict[str, List[str]] = {}
                for s in list(net_amounts[date].keys()):
                    base = re.sub(roman_pattern, '', s.strip())
                    if base not in base_groups:
                        base_groups[base] = []
                    base_groups[base].append(s)

                for base, names in base_groups.items():
                    if len(names) <= 1:
                        continue
                    amounts = [net_amounts[date][n] for n in names]
                    max_abs = max(abs(a) for a in amounts) or 1.0
                    spread = max(amounts) - min(amounts)
                    # Treat as aliases when values match within 1% of magnitude
                    if spread / max_abs < 0.01:
                        for n in names:
                            del net_amounts[date][n]
                            all_sectors.discard(n)
                        net_amounts[date][base] = amounts[0]
                        all_sectors.add(base)

            # Sort dates descending (newest first) and take last `days` trading days
            sorted_dates = sorted(net_amounts.keys(), reverse=True)[:days]

            # Build daily_top: each day has top_n sectors sorted by net_amount desc
            daily_top: Dict[str, List[str]] = {}
            for date in sorted_dates:
                sectors_with_amount = net_amounts.get(date, {})
                sorted_sectors = sorted(sectors_with_amount.items(), key=lambda x: x[1], reverse=True)
                daily_top[date] = [s[0] for s in sorted_sectors[:top_n]]

            # Filter net_amounts to only include sectors and dates we care about
            filtered_net_amounts: Dict[str, Dict[str, float]] = {}
            for date in sorted_dates:
                filtered_net_amounts[date] = {
                    s: net_amounts[date].get(s, 0.0) for s in daily_top[date]
                }

            return {
                "sectors": sorted(list(all_sectors)),
                "daily_top": daily_top,
                "net_amounts": filtered_net_amounts,
            }
        except Exception as e:
            logger.error(f"[A股] Sector moneyflow error: {e}")
            return {"sectors": [], "daily_top": {}, "net_amounts": {}, "error": str(e)}

    @staticmethod
    def get_sector_moneyflow(days: int = 5, top_n: int = 6) -> dict:
        """Get sector-level money flow via Tushare moneyflow_industr API.

        Returns aggregated data with:
        - sectors: union of all sector names across days
        - daily_top: top N sectors per day by net_amount
        - net_amounts: net_amount per sector per day (in 亿元)

        Results are cached for 5 minutes to avoid excessive API calls.
        """
        return _get_cached_sector_mf(days, top_n, lambda: AShareService._fetch_sector_moneyflow(days, top_n))

    @staticmethod
    def get_daily_basic_batch(symbols: List[str], days: int = 30) -> dict:
        """Get daily basic metrics for multiple A-share symbols in a single batch request."""
        import concurrent.futures

        results = []
        errors = []

        def fetch_single(symbol: str) -> dict:
            return AShareService.get_daily_basic(symbol, days)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(fetch_single, s): s for s in symbols}
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if "error" in data:
                        errors.append({"symbol": symbol, "error": data["error"]})
                    else:
                        results.append(data)
                except Exception as e:
                    errors.append({"symbol": symbol, "error": str(e)})

        return {"results": results, "errors": errors}

    @staticmethod
    def get_stock_info_batch(symbols: List[str]) -> dict:
        """Get basic A-share stock information for multiple symbols in a single batch request."""
        import concurrent.futures

        results = []
        errors = []

        def fetch_single(symbol: str) -> dict:
            return AShareService.get_stock_info(symbol)

        # Tushare Pro supports higher concurrency
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(fetch_single, s): s for s in symbols}
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if "error" in data:
                        errors.append({"symbol": symbol, "error": data["error"]})
                    else:
                        results.append(data)
                except Exception as e:
                    errors.append({"symbol": symbol, "error": str(e)})

        return {"results": results, "errors": errors}

    @staticmethod
    def get_top_list(trade_date: str) -> dict:
        """Get Dragon Tiger List (龙虎榜) data for a specific trade date via Tushare top_list API.

        Returns institutional trading data including net amounts, close price, pct_change.
        """
        try:
            pro = ts.pro_api()
            df = pro.top_list(trade_date=trade_date)

            if df is None or df.empty:
                return {"trade_date": trade_date, "data": []}

            def safe_float(val):
                try:
                    return float(val) if pd.notna(val) else None
                except (TypeError, ValueError):
                    return None

            records = []
            for _, row in df.iterrows():
                records.append({
                    "ts_code": str(row.get("ts_code", "")),
                    "name": str(row.get("name", "")),
                    "close": safe_float(row.get("close")),
                    "pct_change": safe_float(row.get("pct_change")),
                    "amount": safe_float(row.get("amount")),
                    "net_amount": safe_float(row.get("net_amount")),
                    "reason": str(row.get("reason", "")),
                })

            return {"trade_date": trade_date, "data": records}
        except Exception as e:
            logger.error(f"[A股] top_list error for {trade_date}: {e}")
            return {"trade_date": trade_date, "error": str(e), "data": []}

    @staticmethod
    def get_dragon_tiger_list(days: int = 3) -> dict:
        """Get aggregated Dragon Tiger List data from last N trading days.

        Returns top 5 by cumulative net buy amount and top 5 by cumulative net sell amount
        (summed across all N trading days), with latest close/pct_change from most recent date.
        This is a read-only operation that does NOT trigger AI analysis.
        """
        try:
            pro = ts.pro_api()

            # Get recent trading days
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
            trade_cal_df = pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date, is_open='1')
            trade_dates = trade_cal_df.head(days)['cal_date'].tolist()

            logger.info(f"[A股] DragonTigerList: querying dates {trade_dates}")

            # Fetch top_list for each trading day
            all_data = []
            for date in trade_dates:
                result = AShareService.get_top_list(date)
                if result.get("data"):
                    for record in result["data"]:
                        record["query_date"] = date
                    all_data.extend(result["data"])

            if not all_data:
                return {"net_buy": [], "net_sell": [], "error": None}

            # Convert to DataFrame
            df = pd.DataFrame(all_data)

            # Filter out records with no net_amount
            df = df.dropna(subset=["net_amount"])

            if df.empty:
                return {"net_buy": [], "net_sell": [], "error": None}

            # Group by stock and sum net_amount across all days
            aggregated = df.groupby(["ts_code", "name"]).agg({
                "net_amount": "sum",  # cumulative net amount
                "query_date": "max",    # latest date
            }).reset_index()

            # Count appearances (上榜次数)
            appearance_count = df.groupby(["ts_code", "name"]).size().reset_index(name="appear_count")

            # Get latest close/pct_change for each stock (from the most recent date entry)
            latest_data = df.sort_values("query_date", ascending=False).groupby("ts_code").first().reset_index()
            latest_data = latest_data[["ts_code", "close", "pct_change", "reason"]]
            latest_data.columns = ["ts_code", "close", "pct_change", "reason"]

            # Merge aggregated with latest data and appearance count
            aggregated = aggregated.merge(latest_data, on="ts_code", how="left")
            aggregated = aggregated.merge(appearance_count, on=["ts_code", "name"], how="left")

            # Fetch industry info from stock_basic
            try:
                stock_basic = pro.stock_basic(exchange='', list_status='L', fields='ts_code,industry')
                industry_map = dict(zip(stock_basic['ts_code'], stock_basic['industry']))
                aggregated['industry'] = aggregated['ts_code'].map(industry_map).fillna('')
            except Exception as e:
                logger.warning(f"[A股] Failed to fetch industry data: {e}")
                aggregated['industry'] = ''

            # Batch fetch valuation metrics for all unique ts_codes
            all_ts_codes = aggregated['ts_code'].unique().tolist()
            valuation_map = {}  # ts_code -> {pe_ttm, total_mv_yi}
            if all_ts_codes:
                val_result = AShareService.get_daily_basic_batch(all_ts_codes, days=30)
                for val_item in val_result.get("results", []):
                    sym = val_item.get("symbol", "")
                    latest = val_item.get("latest")
                    if latest:
                        total_mv = latest.get("total_mv")
                        pe_ttm = latest.get("pe_ttm")
                        # total_mv in 万元 (Tushare convention), convert to 亿元 (/10000); null/0 market cap → null
                        total_mv_yi = round(total_mv / 10000, 2) if total_mv and total_mv > 0 else None
                        valuation_map[sym] = {"pe_ttm": pe_ttm, "total_mv_yi": total_mv_yi}

            def make_item(row) -> dict:
                ts = row.get("ts_code", "")
                val = valuation_map.get(ts, {})
                return {
                    "trade_date": str(row.get("query_date", "")),
                    "ts_code": ts,
                    "name": row.get("name", ""),
                    "industry": row.get("industry", ""),
                    "close": row.get("close"),
                    "pct_change": row.get("pct_change"),
                    "net_amount": row.get("net_amount"),
                    "reason": row.get("reason", ""),
                    "appear_count": int(row.get("appear_count", 1)),
                    "pe_ttm": val.get("pe_ttm"),
                    "total_mv_yi": val.get("total_mv_yi"),
                }

            # Top 5 by cumulative net buy (descending)
            net_buy_df = aggregated.nlargest(5, "net_amount")
            net_buy = [make_item(row) for _, row in net_buy_df.iterrows()]

            # Top 5 by cumulative net sell (ascending - most negative first)
            net_sell_df = aggregated.nsmallest(5, "net_amount")
            net_sell = [make_item(row) for _, row in net_sell_df.iterrows()]

            logger.info(f"[A股] DragonTigerList: net_buy={len(net_buy)}, net_sell={len(net_sell)}")

            return {"net_buy": net_buy, "net_sell": net_sell, "error": None}
        except Exception as e:
            logger.error(f"[A股] get_dragon_tiger_list error: {e}")
            return {"net_buy": [], "net_sell": [], "error": str(e)}

    @staticmethod
    def get_financial_fundamentals(symbol: str) -> dict:
        """Get quarterly financial fundamentals for an A-share stock.

        Fetches from Tushare fina_indicator and income tables.
        Returns EPS, ROE, profit margins, growth rates, revenue, and net income.
        """
        try:
            ts_code = _symbol_to_ts_code(symbol)
            pro = ts.pro_api()

            # Fields to fetch from fina_indicator
            fina_fields = (
                "ts_code,ann_date,end_date,end_type,eps,dt_eps,bps,gross_margin,netprofit_margin,"
                "roe,roe_yearly,debt_to_assets,current_ratio,basic_eps_yoy,netprofit_yoy,tr_yoy"
            )

            # Fields to fetch from income
            income_fields = (
                "ts_code,ann_date,end_date,total_revenue,revenue,n_income,gross_profit"
            )

            # Fetch latest quarter from fina_indicator (no date filter, get most recent)
            fina_df = pro.fina_indicator(ts_code=ts_code, fields=fina_fields)

            # Fetch latest quarter from income (may fail due to rate limit - wrap gracefully)
            income_df = None
            try:
                income_df = pro.income(ts_code=ts_code, fields=income_fields)
            except Exception as e:
                logger.warning(f"[A股] {symbol} income API failed: {e}")

            if (fina_df is None or fina_df.empty) and (income_df is None or income_df.empty):
                return {"symbol": symbol, "error": "No financial data", "data": None}

            def safe_float(val):
                try:
                    return float(val) if pd.notna(val) else None
                except (TypeError, ValueError):
                    return None

            # Use fina_indicator as primary source for most fields
            result = {"symbol": symbol}
            _fina_gross_margin = None

            if fina_df is not None and not fina_df.empty:
                row = fina_df.iloc[0]
                end_date = str(row.get("end_date", ""))
                result["period"] = end_date
                result["ann_date"] = str(row.get("ann_date", ""))

                # Derive report type from end_date (period) MM-DD suffix
                # 0331 -> Q1, 0630 -> half-year, 0930 -> Q3, 1231 -> annual
                month_day = end_date[4:]
                if month_day == "0331":
                    result["report_label"] = f"{end_date[:4]}年一季报"
                elif month_day == "0630":
                    result["report_label"] = f"{end_date[:4]}年半年报"
                elif month_day == "0930":
                    result["report_label"] = f"{end_date[:4]}年三季报"
                elif month_day == "1231":
                    result["report_label"] = f"{end_date[:4]}年年报"
                else:
                    result["report_label"] = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

                result["eps"] = safe_float(row.get("eps"))
                result["bps"] = safe_float(row.get("bps"))
                result["roe"] = safe_float(row.get("roe"))
                result["roe_yearly"] = safe_float(row.get("roe_yearly"))
                # gross_margin from fina_indicator: if > 1000 it's gross_profit in 元, not a %
                _fina_gross_margin = safe_float(row.get("gross_margin"))
                result["gross_margin"] = _fina_gross_margin
                result["netprofit_margin"] = safe_float(row.get("netprofit_margin"))
                result["basic_eps_yoy"] = safe_float(row.get("basic_eps_yoy"))
                result["netprofit_yoy"] = safe_float(row.get("netprofit_yoy"))
                result["tr_yoy"] = safe_float(row.get("tr_yoy"))
                result["debt_to_assets"] = safe_float(row.get("debt_to_assets"))
                result["current_ratio"] = safe_float(row.get("current_ratio"))
            else:
                result["period"] = None
                result["ann_date"] = None
                result["report_label"] = None
                result["eps"] = None
                result["bps"] = None
                result["roe"] = None
                result["roe_yearly"] = None
                result["netprofit_margin"] = None
                result["basic_eps_yoy"] = None
                result["netprofit_yoy"] = None
                result["tr_yoy"] = None
                result["debt_to_assets"] = None
                result["current_ratio"] = None

            if income_df is not None and not income_df.empty:
                # Try to find the record matching the same end_date as fina_indicator
                income_row = None
                if result.get("period"):
                    matching = income_df[income_df["end_date"].astype(str) == result["period"]]
                    if not matching.empty:
                        income_row = matching.iloc[0]
                    else:
                        income_row = income_df.iloc[0]
                else:
                    income_row = income_df.iloc[0]

                total_revenue = safe_float(income_row.get("total_revenue"))
                revenue = safe_float(income_row.get("revenue"))
                gross_profit = safe_float(income_row.get("gross_profit"))

                result["total_revenue"] = total_revenue
                result["revenue"] = revenue
                result["n_income"] = safe_float(income_row.get("n_income"))

                # gross_margin from fina_indicator can be either:
                # 1. A percentage (e.g., 33.26 for 33.26%) - typical for annual reports
                # 2. Gross profit in 元 (e.g., 5175926820.42) - typical for quarterly reports
                # Heuristic: if gross_margin > 1000, treat as gross_profit in 元 and compute %
                if _fina_gross_margin is not None and revenue is not None and revenue > 0:
                    if _fina_gross_margin > 1000:
                        result["gross_margin"] = (_fina_gross_margin / revenue) * 100
            else:
                result["total_revenue"] = None
                result["revenue"] = None
                result["n_income"] = None

            return {"symbol": symbol, "data": result}

        except Exception as e:
            logger.error(f"[A股] {symbol} financial fundamentals error: {e}")
            return {"symbol": symbol, "error": str(e), "data": None}

    # ---------- SW2021 sector-to-stocks helpers ----------

    @staticmethod
    def _get_sw_classify() -> Dict[str, Any]:
        """Fetch and cache the full SW2021 index_classify table (L1+L2+L3) once per day."""
        global _sw_classify_cache, _sw_classify_cache_date
        today = datetime.now().strftime("%Y%m%d")
        if _sw_classify_cache and _sw_classify_cache_date == today:
            return _sw_classify_cache
        try:
            pro = ts.pro_api()
            # Fetch all three levels
            df = pro.index_classify(src='SW2021')
            if df is None or df.empty:
                return {}
            # Build: index_code -> {name, level, ...}
            by_code: Dict[str, Any] = {}
            for _, row in df.iterrows():
                code = str(row.get("index_code", ""))
                if code:
                    by_code[code] = {
                        "index_code": code,
                        "name": str(row.get("industry_name", "")),
                        "level": str(row.get("level", "")),
                        "industry_code": str(row.get("industry_code", "")),
                        "src": str(row.get("src", "")),
                    }
            _sw_classify_cache = by_code
            _sw_classify_cache_date = today
            logger.info(f"[A股] SW2021 classify cached: {len(by_code)} entries")
            return by_code
        except Exception as e:
            logger.error(f"[A股] _get_sw_classify error: {e}")
            return _sw_classify_cache if _sw_classify_cache else {}

    @staticmethod
    def _resolve_sector_to_sw(name: str) -> tuple:
        """Resolve a DC sector name to an SW2021 index_code.

        Normalizes the name (trim whitespace, strip trailing roman numerals using
        the existing regex pattern) and matches against SW2021:
        1. Exact normalized match
        2. L2 normalized match
        3. Substring containment

        Returns (index_code, matched_name) or (None, None) on no match.
        """
        import re
        roman_pattern = r'[IVXⅰⅱⅲⅳⅴⅵⅷⅸⅹⅠ-Ⅿ]+$'
        normalized = re.sub(roman_pattern, '', name.strip())

        sw_table = AShareService._get_sw_classify()
        if not sw_table:
            return None, None

        # Strategy 1: exact normalized match at any level
        for code, info in sw_table.items():
            sw_norm = re.sub(roman_pattern, '', info["name"].strip())
            if sw_norm == normalized:
                return code, info["name"]

        # Strategy 2: L2 exact normalized match
        l2_matches = [
            (code, info["name"]) for code, info in sw_table.items()
            if info["level"] == "L2" and re.sub(roman_pattern, '', info["name"].strip()) == normalized
        ]
        if len(l2_matches) == 1:
            return l2_matches[0]
        if len(l2_matches) > 1:
            # Prefer exact string match over substring
            exact = [m for m in l2_matches if m[1] == normalized]
            if exact:
                return exact[0]

        # Strategy 3: substring containment
        substring_matches = [
            (code, info["name"]) for code, info in sw_table.items()
            if normalized in re.sub(roman_pattern, '', info["name"].strip())
        ]
        if len(substring_matches) == 1:
            return substring_matches[0]
        if len(substring_matches) > 1:
            # Prefer L2
            l2 = [m for m in substring_matches if sw_table[m[0]]["level"] == "L2"]
            if len(l2) == 1:
                return l2[0]

        return None, None

    @staticmethod
    def _get_index_members(index_code: str) -> list:
        """Fetch and cache member ts_code list for an SW2021 index via index_member."""
        global _index_member_cache, _index_member_cache_date
        today = datetime.now().strftime("%Y%m%d")
        if index_code in _index_member_cache and _index_member_cache_date == today:
            return _index_member_cache[index_code]
        try:
            pro = ts.pro_api()
            df = pro.index_member(index_code=index_code)
            if df is None or df.empty:
                members = []
            else:
                members = df["con_code"].tolist()
            if _index_member_cache_date != today:
                _index_member_cache = {}
                _index_member_cache_date = today
            _index_member_cache[index_code] = members
            logger.info(f"[A股] index_member {index_code}: {len(members)} members cached")
            return members
        except Exception as e:
            logger.error(f"[A股] _get_index_members error for {index_code}: {e}")
            return _index_member_cache.get(index_code, [])

    @staticmethod
    def _get_moneyflow_day(trade_date: str) -> dict:
        """Fetch full moneyflow table for a date and return {ts_code: net_inflow_yi}.

        net_inflow = ((buy_elg_amount - sell_elg_amount) + (buy_lg_amount - sell_lg_amount)) / 10000
        Detects Tushare permission/rate-limit errors and propagates a clear error.
        """
        global _moneyflow_day_cache, _moneyflow_day_cache_time
        today = datetime.now().strftime("%Y%m%d")
        is_today = (trade_date == today)

        # Check cache
        if trade_date in _moneyflow_day_cache:
            cached_time = _moneyflow_day_cache_time.get(trade_date, 0)
            ttl = _MONEYFLOW_DAY_CACHE_TTL_TODAY if is_today else _MONEYFLOW_DAY_CACHE_TTL_CLOSED
            if time.time() - cached_time < ttl:
                return _moneyflow_day_cache[trade_date]

        try:
            pro = ts.pro_api()
            df = pro.moneyflow(trade_date=trade_date, fields='ts_code,buy_elg_amount,sell_elg_amount,buy_lg_amount,sell_lg_amount,net_mf_amount')
            if df is None or df.empty:
                result = {}
            else:
                result = {}
                for _, row in df.iterrows():
                    ts_code = str(row.get("ts_code", ""))
                    buy_elg = float(row.get("buy_elg_amount", 0) or 0)
                    sell_elg = float(row.get("sell_elg_amount", 0) or 0)
                    buy_lg = float(row.get("buy_lg_amount", 0) or 0)
                    sell_lg = float(row.get("sell_lg_amount", 0) or 0)
                    net_inflow_yi = ((buy_elg - sell_elg) + (buy_lg - sell_lg)) / 10000
                    result[ts_code] = net_inflow_yi
            _moneyflow_day_cache[trade_date] = result
            _moneyflow_day_cache_time[trade_date] = time.time()
            logger.info(f"[A股] moneyflow {trade_date}: {len(result)} stocks cached")
            return result
        except Exception as e:
            err_str = str(e)
            if "权限" in err_str or "每分钟" in err_str or "Connection" in err_str:
                logger.warning(f"[A股] moneyflow {trade_date} permission/rate-limit error: {err_str[:80]}")
                return {"__error__": f"Tushare权限或速率限制: {err_str[:100]}"}
            logger.error(f"[A股] _get_moneyflow_day error for {trade_date}: {e}")
            return {"__error__": str(e)}

    @staticmethod
    def _get_stock_names(ts_codes: list) -> dict:
        """Resolve a list of ts_codes to company names via cached stock_basic."""
        global _stock_basic_name_cache, _stock_basic_name_cache_date
        today = datetime.now().strftime("%Y%m%d")

        # Return cached subset
        if _stock_basic_name_cache and _stock_basic_name_cache_date == today:
            return {code: _stock_basic_name_cache.get(code, code) for code in ts_codes}

        try:
            pro = ts.pro_api()
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
            if df is not None and not df.empty:
                if _stock_basic_name_cache_date != today:
                    _stock_basic_name_cache.clear()
                    _stock_basic_name_cache_date = today
                for _, row in df.iterrows():
                    _stock_basic_name_cache[str(row["ts_code"])] = str(row["name"])
                logger.info(f"[A股] stock_basic name cache: {len(_stock_basic_name_cache)} entries")
        except Exception as e:
            logger.error(f"[A股] _get_stock_names error: {e}")

        return {code: _stock_basic_name_cache.get(code, code) for code in ts_codes}

    @staticmethod
    def _get_stock_basics(trade_date: str) -> dict:
        """Fetch daily_basic for all stocks on a given trade date and return {ts_code: {pe_ttm, total_mv_yi}}.

        Caches per date with long TTL for closed days.
        total_mv is in 元; divide by 1e4 to get 市值 in 万亿 (displayed as e.g. "1.29万亿").
        """
        global _stock_basics_cache, _stock_basics_cache_time
        today = datetime.now().strftime("%Y%m%d")
        is_today = (trade_date == today)
        ttl = _STOCK_BASICS_CACHE_TTL_TODAY if is_today else _STOCK_BASICS_CACHE_TTL_CLOSED

        if trade_date in _stock_basics_cache:
            if time.time() - _stock_basics_cache_time.get(trade_date, 0) < ttl:
                return _stock_basics_cache[trade_date]

        try:
            pro = ts.pro_api()
            # Fetch all stocks' daily_basic for this date
            df = pro.daily_basic(trade_date=trade_date, fields='ts_code,pe_ttm,total_mv')
            if df is None or df.empty:
                result = {}
            else:
                result = {}
                for _, row in df.iterrows():
                    ts_code = str(row.get("ts_code", ""))
                    pe_ttm = float(row["pe_ttm"]) if pd.notna(row.get("pe_ttm")) else None
                    total_mv_yi = float(row["total_mv"]) / 1e8 if pd.notna(row.get("total_mv")) else None
                    # total_mv is in 元; display as 万亿 (divide by 1e4) or 亿 (divide by 1e8)
                    # 1.29万亿 = 1.29×10¹² 元 → /1e4 = 12930.66亿 → display as "1.29万亿"
                    total_mv_yi = float(row["total_mv"]) / 1e4 if pd.notna(row.get("total_mv")) else None
                    result[ts_code] = {"pe_ttm": pe_ttm, "total_mv_yi": total_mv_yi}
            _stock_basics_cache[trade_date] = result
            _stock_basics_cache_time[trade_date] = time.time()
            logger.info(f"[A股] daily_basic {trade_date}: {len(result)} stocks cached")
            return result
        except Exception as e:
            err_str = str(e)
            if "权限" in err_str or "每分钟" in err_str or "Connection" in err_str:
                logger.warning(f"[A股] daily_basic {trade_date} permission/rate-limit: {err_str[:80]}")
                return {"__error__": f"Tushare权限或速率限制: {err_str[:100]}"}
            logger.error(f"[A股] _get_stock_basics error for {trade_date}: {e}")
            return {"__error__": str(e)}

    @staticmethod
    def get_sector_top_stocks(sector: str, dates: List[str], top_n: int = 5) -> dict:
        """Get top N stocks by main-force net inflow for a sector on given dates.

        Resolves sector name to SW2021 index, fetches members, ranks per date.
        Returns {sector, index_code, matched_name, by_date, error}.
        """
        # Step 1: resolve sector -> SW2021 index_code
        index_code, matched_name = AShareService._resolve_sector_to_sw(sector)
        if not index_code:
            return {
                "sector": sector,
                "index_code": None,
                "matched_name": None,
                "by_date": {},
                "error": "无法匹配到申万行业成分股",
            }

        # Step 2: get members
        members = AShareService._get_index_members(index_code)
        if not members:
            return {
                "sector": sector,
                "index_code": index_code,
                "matched_name": matched_name,
                "by_date": {},
                "error": f"指数 {index_code} 无成分股",
            }

        member_set = set(members)

        # Step 3: for each date, rank members by net inflow
        by_date: Dict[str, list] = {}
        for date_str in dates:
            # Accept YYYY-MM-DD or YYYYMMDD
            trade_date = date_str.replace("-", "")
            mf_map = AShareService._get_moneyflow_day(trade_date)

            if "__error__" in mf_map:
                return {
                    "sector": sector,
                    "index_code": index_code,
                    "matched_name": matched_name,
                    "by_date": {},
                    "error": mf_map["__error__"],
                }

            # Filter to members and build ranked list
            ranked = []
            for ts_code, net_inflow_yi in mf_map.items():
                if ts_code in member_set:
                    ranked.append((ts_code, net_inflow_yi))

            # Sort by net_inflow descending (top_n regardless of sign)
            ranked.sort(key=lambda x: x[1], reverse=True)
            top_stocks = ranked[:top_n]

            # Resolve names and basics
            ts_codes_needed = [r[0] for r in top_stocks]
            names = AShareService._get_stock_names(ts_codes_needed)
            basics = AShareService._get_stock_basics(trade_date)

            by_date[date_str] = [
                {
                    "ts_code": ts_code,
                    "name": names.get(ts_code, ts_code),
                    "net_inflow": round(ni, 2),
                    "pe_ttm": basics.get(ts_code, {}).get("pe_ttm"),
                    "total_mv_yi": basics.get(ts_code, {}).get("total_mv_yi"),
                }
                for ts_code, ni in top_stocks
            ]

        return {
            "sector": sector,
            "index_code": index_code,
            "matched_name": matched_name,
            "by_date": by_date,
            "error": None,
        }


class USStockService:
    """Service wrapper for US stock data via Futu OpenAPI.

    Delegates to FutuQuoteService for all data fetching.
    """

    @staticmethod
    def get_daily_basic(symbol: str, days: int = 30) -> dict:
        """Get daily basic metrics for US stock via Futu OpenAPI.

        Routes through `etf_valuation.get_etf_aware_daily_basic` so ETF symbols
        pick up yahooquery-sourced PE/PB and dividend fields; non-ETF symbols
        are byte-identical to the Futu response (plus `is_etf: false`).
        """
        from backend.services import etf_valuation
        return etf_valuation.get_etf_aware_daily_basic(symbol, days)

    @staticmethod
    def get_stock_info(symbol: str) -> dict:
        """Get basic US stock information via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_stock_info(symbol)

    @staticmethod
    def get_kline_data(
        symbol: str,
        days: int = 100,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> dict:
        """Get K-line data for a US stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_kline_data(symbol, days, period, adjust)

    @staticmethod
    def get_realtime_quote(symbol: str) -> dict:
        """Get real-time quote for a US stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_realtime_quote(symbol)

    @staticmethod
    def get_daily_basic_batch(symbols: List[str], days: int = 30) -> dict:
        """Get daily basic metrics for multiple US stock symbols via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_daily_basic_batch(symbols, days)

    @staticmethod
    def get_stock_info_batch(symbols: List[str]) -> dict:
        """Get basic US stock information for multiple symbols via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_stock_info_batch(symbols)

    @staticmethod
    def get_moneyflow(symbol: str, days: int = 30) -> dict:
        """Get main force net inflow for US stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_capital_flow(symbol, days)

    @staticmethod
    def get_company_info(symbol: str) -> dict:
        """Get US listed-company basic info via Futu get_company_profile + get_company_executives."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_company_info(symbol)

    @staticmethod
    def get_revenue_breakdown(symbol: str) -> dict:
        """Get US listed-company main-business composition via Futu
        ``get_financials_revenue_breakdown`` (proto 3228).

        Returns a single payload with all four breakdown dimensions
        (Product / Industry / Region / Business). See
        ``FutuQuoteService.get_revenue_breakdown`` for the response shape.
        """
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_revenue_breakdown(symbol)

    @staticmethod
    def get_revenue_breakdown_history(symbol: str, n_periods: int = 4) -> dict:
        """Get last N annual periods of US by-product data via Futu
        ``get_financials_revenue_breakdown`` (parallel per-period calls).
        """
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_revenue_breakdown_history(symbol, n_periods)

    @staticmethod
    def get_shareholders_overview(symbol: str) -> dict:
        """Get US listed-company shareholder overview (top holders + holder
        type + holding period list) via Futu ``get_shareholders_overview``
        (proto 3237). See ``FutuQuoteService.get_shareholders_overview``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_overview(symbol)

    @staticmethod
    def get_shareholders_institutional(symbol: str, n_periods: int = 30) -> dict:
        """Get US institutional-holding aggregate over the last N periods
        via Futu ``get_shareholders_institutional`` (proto 3238, paginated
        server-side up to N). See ``FutuQuoteService.get_shareholders_institutional``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_institutional(symbol, n_periods)

    @staticmethod
    def get_shareholders_holder_detail(
        symbol: str,
        holder_id=None,
        period_id=None,
        num: int = 50,
        next_key=None,
    ) -> dict:
        """Get US shareholder-detail rows via Futu ``get_shareholders_holder_detail``
        (proto 3239). See ``FutuQuoteService.get_shareholders_holder_detail``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_holder_detail(
            symbol,
            holder_id=holder_id,
            period_id=period_id,
            num=num,
            next_key=next_key,
        )

    @staticmethod
    def get_shareholders_holding_changes(
        symbol: str,
        filter_type: int = 1,
        num: int = 50,
        next_key=None,
    ) -> dict:
        """Get US latest-period holding changes (increases / decreases) via
        Futu ``get_shareholders_holding_changes``. Note: the SDK does NOT
        accept a ``holder_id`` parameter — per-holder reduction history
        goes through ``get_shareholders_holder_detail(holder_id=...)``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_holding_changes(
            symbol, filter_type=filter_type, num=num, next_key=next_key
        )


class HKStockService:
    """Service wrapper for HK stock data via Futu OpenAPI.

    Delegates to FutuQuoteService for all data fetching.
    """

    @staticmethod
    def get_stock_info(symbol: str) -> dict:
        """Get basic HK stock information via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_stock_info(symbol)

    @staticmethod
    def get_kline_data(
        symbol: str,
        days: int = 100,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> dict:
        """Get K-line data for a HK stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_kline_data(symbol, days, period, adjust)

    @staticmethod
    def get_realtime_quote(symbol: str) -> dict:
        """Get real-time quote for a HK stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_realtime_quote(symbol)

    @staticmethod
    def get_daily_basic(symbol: str, days: int = 30) -> dict:
        """Get daily basic metrics for HK stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_daily_basic(symbol, days)

    @staticmethod
    def get_daily_basic_batch(symbols: List[str], days: int = 30) -> dict:
        """Get daily basic metrics for multiple HK stock symbols via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_daily_basic_batch(symbols, days)

    @staticmethod
    def get_stock_info_batch(symbols: List[str]) -> dict:
        """Get basic HK stock information for multiple symbols via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_stock_info_batch(symbols)

    @staticmethod
    def get_moneyflow(symbol: str, days: int = 30) -> dict:
        """Get main force net inflow for HK stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_capital_flow(symbol, days)

    @staticmethod
    def get_company_info(symbol: str) -> dict:
        """Get HK listed-company basic info via Futu get_company_profile + get_company_executives."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_company_info(symbol)

    @staticmethod
    def get_revenue_breakdown(symbol: str) -> dict:
        """Get HK listed-company main-business composition via Futu
        ``get_financials_revenue_breakdown`` (proto 3228).
        """
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_revenue_breakdown(symbol)

    @staticmethod
    def get_revenue_breakdown_history(symbol: str, n_periods: int = 4) -> dict:
        """Get last N annual periods of HK by-product data via Futu
        ``get_financials_revenue_breakdown`` (parallel per-period calls).
        """
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_revenue_breakdown_history(symbol, n_periods)

    @staticmethod
    def get_shareholders_overview(symbol: str) -> dict:
        """Get HK listed-company shareholder overview (top holders + holder
        type + holding period list) via Futu ``get_shareholders_overview``
        (proto 3237). See ``FutuQuoteService.get_shareholders_overview``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_overview(symbol)

    @staticmethod
    def get_shareholders_institutional(symbol: str, n_periods: int = 30) -> dict:
        """Get HK institutional-holding aggregate over the last N periods
        via Futu ``get_shareholders_institutional`` (proto 3238, paginated
        server-side up to N). See ``FutuQuoteService.get_shareholders_institutional``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_institutional(symbol, n_periods)

    @staticmethod
    def get_shareholders_holder_detail(
        symbol: str,
        holder_id=None,
        period_id=None,
        num: int = 50,
        next_key=None,
    ) -> dict:
        """Get HK shareholder-detail rows via Futu ``get_shareholders_holder_detail``
        (proto 3239). See ``FutuQuoteService.get_shareholders_holder_detail``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_holder_detail(
            symbol,
            holder_id=holder_id,
            period_id=period_id,
            num=num,
            next_key=next_key,
        )

    @staticmethod
    def get_shareholders_holding_changes(
        symbol: str,
        filter_type: int = 1,
        num: int = 50,
        next_key=None,
    ) -> dict:
        """Get HK latest-period holding changes (increases / decreases) via
        Futu ``get_shareholders_holding_changes``. Note: the SDK does NOT
        accept a ``holder_id`` parameter — per-holder reduction history
        goes through ``get_shareholders_holder_detail(holder_id=...)``."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_shareholders_holding_changes(
            symbol, filter_type=filter_type, num=num, next_key=next_key
        )


# Backward compatibility - AkshareService now points to AShareService
AkshareService = AShareService


def calculate_indicators(kline_data: list) -> dict:
    """Calculate technical indicators (MACD, RSI) from K-line data."""
    if not kline_data or len(kline_data) < 30:
        return {"error": "Insufficient data for indicators"}

    df = pd.DataFrame(kline_data)
    closes = pd.to_numeric(df["close"], errors="coerce")

    # MACD (12, 26, 9)
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_hist = 2 * (dif - dea)

    # RSI
    rsi6 = _rsi(closes, 6)
    rsi12 = _rsi(closes, 12)
    rsi24 = _rsi(closes, 24)

    # MA
    ma5 = closes.rolling(window=5).mean()
    ma10 = closes.rolling(window=10).mean()
    ma20 = closes.rolling(window=20).mean()
    ma60 = closes.rolling(window=60).mean() if len(closes) >= 60 else None

    return {
        "macd": {
            "dif": float(dif.iloc[-1]) if len(dif) > 0 else 0,
            "dea": float(dea.iloc[-1]) if len(dea) > 0 else 0,
            "hist": float(macd_hist.iloc[-1]) if len(macd_hist) > 0 else 0,
        },
        "rsi": {
            "rsi6": float(rsi6[-1]) if len(rsi6) > 0 else 0,
            "rsi12": float(rsi12[-1]) if len(rsi12) > 0 else 0,
            "rsi24": float(rsi24[-1]) if len(rsi24) > 0 else 0,
        },
        "ma": {
            "ma5": float(ma5.iloc[-1]) if len(ma5) > 0 else 0,
            "ma10": float(ma10.iloc[-1]) if len(ma10) > 0 else 0,
            "ma20": float(ma20.iloc[-1]) if len(ma20) > 0 else 0,
            "ma60": float(ma60.iloc[-1]) if ma60 is not None and len(ma60) > 0 else None,
        }
    }


def _rsi(prices, period: int = 14) -> list:
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.dropna().values.tolist()


def get_valuation_data(symbol: str, days: int = 100) -> dict:
    """Get PE, PB, and turnover rate data from Tushare daily_basic endpoint."""
    # Delegate to appropriate service based on symbol
    if _is_hk_stock_symbol(symbol):
        return HKStockService.get_daily_basic(symbol, days)
    elif symbol.upper().endswith(".US") or _is_us_stock_symbol(symbol):
        return USStockService.get_daily_basic(symbol, days)
    else:
        return AShareService.get_daily_basic(symbol, days)


def _is_us_stock_symbol(symbol: str) -> bool:
    """Check if a symbol appears to be a US stock (not a 6-digit A-share code)."""
    symbol = symbol.strip().upper()
    # US stocks are typically 1-5 letters, or have .US suffix/prefix
    if symbol.endswith(".US"):
        return True
    if symbol.startswith("US."):
        return True
    if len(symbol) <= 5 and not symbol.isdigit():
        return True
    return False


def _is_hk_stock_symbol(symbol: str) -> bool:
    """Check if a symbol appears to be a HK stock (4-5 digits, or HK. prefix, not A-share)."""
    symbol = symbol.strip()
    # HK stocks are 4-5 digits (e.g., 00700, 9988), or have HK. prefix
    if symbol.startswith("HK."):
        return True
    if len(symbol) in (4, 5) and symbol.isdigit():
        return True
    return False
