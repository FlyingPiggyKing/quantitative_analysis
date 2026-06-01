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
    def get_daily_basic(symbol: str, days: int = 30) -> dict:
        """Get daily basic metrics for US stock via Futu OpenAPI."""
        from backend.services.futu_quote_service import FutuQuoteService
        return FutuQuoteService.get_daily_basic(symbol, days)

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
