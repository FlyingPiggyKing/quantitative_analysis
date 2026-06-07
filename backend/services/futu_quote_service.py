"""Futu OpenAPI service for US stock data.

Replaces Yahoo Finance with Futu OpenAPI for better performance and reliability.
"""
import os
import logging
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

# Futu OpenD connection config
FUTU_OPEND_HOST = os.getenv("FUTU_OPEND_HOST", "127.0.0.1")
FUTU_OPEND_PORT = int(os.getenv("FUTU_OPEND_PORT", "11111"))


def _to_python_type(val, default=None):
    """Convert numpy/pandas types to Python native types for JSON serialization."""
    if val is None:
        return default
    # numpy/pandas types have item() method
    if hasattr(val, 'item'):
        val = val.item()
    # Handle float conversion
    if isinstance(val, float):
        if val != val:  # NaN
            return default
        if val == float('inf') or val == float('-inf'):
            return default
        return float(val)
    # Handle int conversion
    if isinstance(val, int):
        return int(val)
    return val


class _FutuCache:
    """Simple in-memory cache for Futu API data with TTL.

    Prevents repeated API calls for the same symbol within TTL seconds.
    Uses stale-on-error strategy: returns stale cache if error occurs.
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
        """Get from cache or fetch if not cached/expired. Only caches successful results."""
        cached = self.get(key)
        if cached is not None:
            logger.info(f"[Futu] Cache hit for {key}")
            return cached

        logger.info(f"[Futu] Cache miss for {key}, fetching...")
        result = fetch_func()
        # Only cache successful results (error key absent or null).
        # Callers that wrap responses as ``{data, error: None}`` are valid successes.
        err = result.get("error") if isinstance(result, dict) else None
        if not err:
            self.set(key, result)
        else:
            logger.warning(f"[Futu] {key} fetch returned error, not caching: {str(err)[:50]}")
        return result

    def on_error_return_stale(self, key: str, fetch_func, max_stale_seconds: int = 3600) -> Dict[str, Any]:
        """On error, return stale cache if available. Does not cache error results."""
        try:
            return self.get_or_fetch(key, fetch_func)
        except Exception as e:
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    age = time.time() - entry["timestamp"]
                    if age < max_stale_seconds:
                        logger.warning(f"[Futu] {key} error, returning stale cache (age: {age:.0f}s)")
                        return entry["data"]
            raise


# Global cache for Futu data - 5 minute TTL
_futu_cache = _FutuCache(ttl=300)

# Global cache for Futu company profile / executives (get_company_info) - 24h TTL
# Company profile data rarely changes; long TTL keeps OpenD pressure low.
_company_info_cache = _FutuCache(ttl=86400)


def _symbol_to_futu_code(symbol: str) -> str:
    """Convert US stock symbol to Futu format (e.g., AAPL -> US.AAPL)."""
    symbol = symbol.strip().upper()
    if symbol.endswith(".US"):
        return f"US.{symbol[:-3]}"
    if "." in symbol:
        return symbol
    return f"US.{symbol}"


def _futu_code_to_symbol(futu_code: str) -> str:
    """Convert Futu code to standard symbol (e.g., US.AAPL -> AAPL)."""
    if "." in futu_code:
        parts = futu_code.split(".")
        if len(parts) == 2 and parts[0] == "US":
            return parts[1]
    return futu_code


def _symbol_to_hk_futu_code(symbol: str) -> str:
    """Convert HK stock symbol to Futu format (e.g., 00700 -> HK.00700)."""
    symbol = symbol.strip()
    if symbol.startswith("HK."):
        return symbol
    if "." in symbol:
        return symbol
    # Preserve leading zeros — do not convert to int
    return f"HK.{symbol}"


def _hk_futu_code_to_symbol(futu_code: str) -> str:
    """Convert Futu HK code to standard symbol (e.g., HK.00700 -> 00700)."""
    if "." in futu_code:
        parts = futu_code.split(".")
        if len(parts) == 2 and parts[0] == "HK":
            return parts[1]
    return futu_code


def _is_hk_stock_symbol(symbol: str) -> bool:
    """Check if a symbol appears to be a HK stock (4-5 digits, not 6-digit A-share)."""
    symbol = symbol.strip()
    if len(symbol) in (4, 5) and symbol.isdigit():
        return True
    return False


def _get_futu_code(symbol: str) -> tuple:
    """Get Futu code and market for any symbol.

    Returns (futu_code, market) where market is 'HK' or 'US'.
    """
    symbol = symbol.strip()
    if _is_hk_stock_symbol(symbol):
        return (_symbol_to_hk_futu_code(symbol), "HK")
    return (_symbol_to_futu_code(symbol), "US")


class FutuQuoteService:
    """Service wrapper for US stock data via Futu OpenAPI."""

    _quote_ctx = None
    _ctx_lock = threading.Lock()

    @classmethod
    def _get_quote_context(cls):
        """Get or create shared quote context."""
        if cls._quote_ctx is None:
            with cls._ctx_lock:
                if cls._quote_ctx is None:
                    from futu import OpenQuoteContext
                    cls._quote_ctx = OpenQuoteContext(
                        host=FUTU_OPEND_HOST,
                        port=FUTU_OPEND_PORT
                    )
                    logger.info(f"[Futu] Created quote context ({FUTU_OPEND_HOST}:{FUTU_OPEND_PORT})")
        return cls._quote_ctx

    @classmethod
    def close_context(cls):
        """Close the quote context."""
        with cls._ctx_lock:
            if cls._quote_ctx is not None:
                cls._quote_ctx.close()
                cls._quote_ctx = None
                logger.info("[Futu] Closed quote context")

    @staticmethod
    def get_snapshot(symbol: str) -> dict:
        """Get market snapshot (PE, PB, turnover_rate, market_cap) via Futu."""
        cache_key = f"snapshot:{symbol.upper()}"

        def fetch_snapshot() -> dict:
            logger.info(f"[Futu] Fetching snapshot for {symbol}")
            ctx = FutuQuoteService._get_quote_context()
            futu_code, market = _get_futu_code(symbol)

            ret, data = ctx.get_market_snapshot([futu_code])
            if ret != 0:
                raise Exception(f"Futu API error: {data}")

            if data is None or len(data) == 0:
                return {"symbol": symbol, "error": "Stock not found"}

            row = data.iloc[0] if hasattr(data, "iloc") else data[0]

            return {
                "symbol": symbol.upper(),
                "name": row.get("name", ""),
                "market": market,
                "pe_ttm": _to_python_type(row.get("pe_ttm_ratio")),
                "pb": _to_python_type(row.get("pb_ratio")),
                "turnover_rate": _to_python_type(row.get("turnover_rate")),
                "total_mv": _to_python_type(row.get("total_market_val")),
                "circ_mv": _to_python_type(row.get("circular_market_val")),
                # Additional fields for realtime quote compatibility
                "price": _to_python_type(row.get("last_price")),
                "open": _to_python_type(row.get("open_price")),
                "high": _to_python_type(row.get("high_price")),
                "low": _to_python_type(row.get("low_price")),
                "close_prev": _to_python_type(row.get("prev_close_price")),
                "volume": int(_to_python_type(row.get("volume"), 0) or 0),
                "change_pct": 0.0,  # Calculated from price - prev_close if needed
            }

        try:
            return _futu_cache.on_error_return_stale(cache_key, fetch_snapshot)
        except Exception as e:
            logger.error(f"[Futu] {symbol} snapshot error: {e}")
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_stock_info(symbol: str) -> dict:
        """Get basic US stock info via Futu snapshot (name, sector)."""
        cache_key = f"info:{symbol.upper()}"

        def fetch_info() -> dict:
            logger.info(f"[Futu] Fetching info for {symbol}")
            result = FutuQuoteService.get_snapshot(symbol)
            if "error" in result:
                return result

            return {
                "symbol": symbol.upper(),
                "name": result.get("name", "未知"),
                "market": result.get("market", "US"),
                "sector": "未知",  # Futu snapshot doesn't provide sector directly
            }

        try:
            return _futu_cache.on_error_return_stale(cache_key, fetch_info)
        except Exception as e:
            logger.error(f"[Futu] {symbol} info error: {e}")
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_realtime_quote(symbol: str) -> dict:
        """Get realtime quote via Futu snapshot."""
        cache_key = f"realtime:{symbol.upper()}"

        def fetch_quote() -> dict:
            logger.info(f"[Futu] Fetching realtime quote for {symbol}")
            result = FutuQuoteService.get_snapshot(symbol)
            if "error" in result:
                return result

            price = result.get("price", 0)
            prev_close = result.get("close_prev", 0)
            change_pct = 0.0
            if prev_close and prev_close != 0:
                change_pct = ((price - prev_close) / prev_close) * 100

            return {
                "symbol": symbol.upper(),
                "name": result.get("name", "未知"),
                "market": result.get("market", "US"),
                "price": price,
                "change_pct": change_pct,
                "volume": result.get("volume", 0),
                "amount": 0.0,  # Not available in snapshot
                "high": result.get("high", 0),
                "low": result.get("low", 0),
                "open": result.get("open", 0),
                "close_prev": prev_close,
            }

        try:
            return _futu_cache.on_error_return_stale(cache_key, fetch_quote)
        except Exception as e:
            logger.error(f"[Futu] {symbol} realtime quote error: {e}")
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_kline_data(
        symbol: str,
        days: int = 100,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> dict:
        """Get K-line data via Futu historical K-line API."""
        cache_key = f"kline:{symbol.upper()}:{days}:{period}:{adjust}"

        def fetch_kline() -> dict:
            logger.info(f"[Futu] Fetching K-line for {symbol} ({days} days)")
            ctx = FutuQuoteService._get_quote_context()
            futu_code, market = _get_futu_code(symbol)

            # Map period to Futu KLType
            from futu import KLType, AuType
            ktype_map = {
                "daily": KLType.K_DAY,
                "weekly": KLType.K_WEEK,
                "monthly": KLType.K_MON,
            }
            kl_type = ktype_map.get(period.lower(), KLType.K_DAY)

            # Map adjust to Futu AuType
            au_map = {
                "qfq": AuType.QFQ,   # Forward adjustment (前复权)
                "hfq": AuType.HFQ,   # Backward adjustment (后复权)
                "no": AuType.NONE,   # No adjustment
            }
            au_type = au_map.get(adjust.lower(), AuType.QFQ)

            # Calculate date range
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")

            ret, data, page_req_key = ctx.request_history_kline(
                futu_code,
                start=start_date,
                end=end_date,
                ktype=kl_type,
                autype=au_type,
                max_count=1000,
            )

            if ret != 0:
                raise Exception(f"Futu API error: {data}")

            if data is None or len(data) == 0:
                return {"symbol": symbol, "error": "No data found"}

            # Process data
            records = []
            for i in range(len(data)):
                row = data.iloc[i] if hasattr(data, "iloc") else data[i]

                # Parse time_key (format: yyyy-MM-dd HH:mm:ss)
                time_key = row.get("time_key", "")
                date_str = time_key.split(" ")[0] if time_key else ""

                # Calculate change_pct
                last_close = _to_python_type(row.get("last_close"), 0)
                close = _to_python_type(row.get("close"), 0)
                change_pct = 0.0
                if last_close and last_close != 0:
                    change_pct = ((close - last_close) / last_close) * 100

                records.append({
                    "date": date_str,
                    "open": _to_python_type(row.get("open"), 0),
                    "close": close,
                    "high": _to_python_type(row.get("high"), 0),
                    "low": _to_python_type(row.get("low"), 0),
                    "volume": int(_to_python_type(row.get("volume"), 0) or 0),
                    "change_pct": change_pct,
                    # PE and turnover_rate from K-line
                    "pe_ttm": _to_python_type(row.get("pe_ratio")),
                    "turnover_rate": _to_python_type(row.get("turnover_rate")),
                })

            # Sort by date and take last N
            records.sort(key=lambda x: x["date"])
            records = records[-days:]

            return {
                "symbol": symbol,
                "period": period,
                "data": records,
            }

        try:
            return _futu_cache.on_error_return_stale(cache_key, fetch_kline)
        except Exception as e:
            logger.error(f"[Futu] {symbol} K-line error: {e}")
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_daily_basic(symbol: str, days: int = 30) -> dict:
        """Get daily basic metrics (PE, PB, turnover_rate) via Futu K-line.

        Uses request_history_kline to get historical PE and turnover_rate data.
        Returns a time series compatible with USStockService.
        """
        cache_key = f"daily_basic:{symbol.upper()}:{days}"

        def fetch_daily_basic() -> dict:
            logger.info(f"[Futu] Fetching daily basic for {symbol} ({days} days)")

            # Fetch K-line data which includes pe_ratio and turnover_rate
            kline_result = FutuQuoteService.get_kline_data(symbol, days=days, period="daily", adjust="qfq")
            if "error" in kline_result:
                return {"symbol": symbol, "error": kline_result["error"]}

            kline_data = kline_result.get("data", [])
            if not kline_data:
                return {"symbol": symbol, "error": "No K-line data available"}

            # Convert K-line records to daily_basic format
            records = []
            for row in kline_data:
                records.append({
                    "trade_date": row.get("date"),
                    "pe_ttm": row.get("pe_ttm"),
                    "pb": row.get("pb"),
                    "turnover_rate": row.get("turnover_rate"),
                    "total_mv": None,  # Not available in K-line
                    "circ_mv": None,   # Not available in K-line
                })

            # Get current snapshot for PB, market cap, and TTM PE
            snapshot = FutuQuoteService.get_snapshot(symbol)
            latest = records[-1] if records else {}
            if "error" not in snapshot and records:
                # Fill in TTM PE, PB and market cap from snapshot
                # Note: K-line only has pe_ratio (static PE), snapshot has pe_ttm_ratio (TTM PE)
                records[-1]["pe_ttm"] = snapshot.get("pe_ttm")  # This is pe_ttm_ratio from snapshot
                records[-1]["pb"] = snapshot.get("pb")
                records[-1]["total_mv"] = snapshot.get("total_mv")
                records[-1]["circ_mv"] = snapshot.get("circ_mv")

            return {
                "symbol": symbol,
                "data": records,
                "latest": latest,
            }

        try:
            return _futu_cache.on_error_return_stale(cache_key, fetch_daily_basic)
        except Exception as e:
            logger.error(f"[Futu] {symbol} daily_basic error: {e}")
            return {"symbol": symbol, "error": str(e)}
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_stock_info_batch(symbols: List[str], days: int = 30) -> dict:
        """Get basic info for multiple US stocks in a single batch request."""
        import concurrent.futures

        results = []
        errors = []

        def fetch_single(symbol: str) -> dict:
            return FutuQuoteService.get_stock_info(symbol)

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
    def get_daily_basic_batch(symbols: List[str], days: int = 30) -> dict:
        """Get daily basic metrics for multiple US stocks in a single batch request."""
        import concurrent.futures

        results = []
        errors = []

        def fetch_single(symbol: str) -> dict:
            return FutuQuoteService.get_daily_basic(symbol, days)

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
    def get_capital_flow(symbol: str, days: int = 30) -> dict:
        """Get main force net inflow (主力资金净流入) via Futu get_capital_flow API.

        Supports HK and US stocks. Returns main_in_flow (positive = net inflow).
        """
        cache_key = f"capital_flow:{symbol.upper()}:{days}"

        def fetch_capital_flow() -> dict:
            logger.info(f"[Futu] Fetching capital flow for {symbol} ({days} days)")
            ctx = FutuQuoteService._get_quote_context()
            futu_code, market = _get_futu_code(symbol)

            from futu import PeriodType
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")

            ret, data = ctx.get_capital_flow(
                stock_code=futu_code,
                start=start_date,
                end=end_date,
                period_type=PeriodType.DAY,
            )

            if ret != 0:
                raise Exception(f"Futu get_capital_flow error: {data}")

            if data is None or len(data) == 0:
                return {"symbol": symbol, "market": market, "error": "No capital flow data"}

            # Process data - extract main_in_flow per day
            # Note: Futu's get_capital_flow returns date field directly (may be empty string)
            records = []
            for i in range(len(data)):
                row = data.iloc[i] if hasattr(data, "iloc") else data[i]

                date_str = row.get("date", "") or row.get("time_key", "") or ""
                if date_str and " " in date_str:
                    date_str = date_str.split(" ")[0]

                records.append({
                    "date": date_str,
                    "main_in_flow": _to_python_type(row.get("main_in_flow")),
                    "_index": i,  # preserve original order as fallback
                })

            # Sort by date (if dates are valid), otherwise keep API order
            valid_dates = [r for r in records if r["date"]]
            if len(valid_dates) >= days:
                # Enough valid dates - sort and take last N
                records.sort(key=lambda x: x["date"])
                records = records[-days:]
            else:
                # Dates missing/empty - take last N from original API order
                records = records[-days:]

            # Calculate 5-day total
            net_5d_total = sum(r["main_in_flow"] or 0 for r in records[-5:])

            return {
                "symbol": symbol,
                "market": market,
                "data": records,
                "latest": records[-1] if records else {},
                "net_5d_total": net_5d_total,
            }

        try:
            return _futu_cache.on_error_return_stale(cache_key, fetch_capital_flow)
        except Exception as e:
            logger.error(f"[Futu] {symbol} capital flow error: {e}")
            return {"symbol": symbol, "market": "HK/US", "error": str(e)}

    @staticmethod
    def get_company_info(symbol: str) -> dict:
        """Get HK/US listed-company basic info via Futu get_company_profile + get_company_executives.

        Calls both endpoints in parallel (2 threads), merges into a single response
        dict, and caches the merged result for 24h. Returns shape
        ``{data: {symbol, code, market, profile_labels, executives, name, error},
        error: null}`` on success, or ``{data: None, error: <msg>}`` on failure.

        `profile_labels` is the raw Futu key-value list (label name + value +
        fieldType: 0=text, 1=link, 2=independent title). `executives` is the
        director list (name, displayName, position, beginDate, gender, age,
        education, annualSalary). `name` is derived from the first text-type
        label whose value is non-empty (best-effort fallback to "").
        """
        cache_key = f"company_info:{symbol.upper()}"

        def fetch_company_info() -> dict:
            logger.info(f"[Futu] Fetching company info for {symbol}")
            futu_code, market = _get_futu_code(symbol)
            ctx = FutuQuoteService._get_quote_context()

            import concurrent.futures

            profile_exc: Optional[Exception] = None
            executives_exc: Optional[Exception] = None
            profile_df = None
            executives_df = None

            def fetch_profile():
                ret, data = ctx.get_company_profile(futu_code)
                if ret != 0:
                    raise Exception(f"Futu get_company_profile error: {data}")
                return data

            def fetch_executives():
                ret, data = ctx.get_company_executives(futu_code)
                if ret != 0:
                    raise Exception(f"Futu get_company_executives error: {data}")
                return data

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                profile_future = executor.submit(fetch_profile)
                executives_future = executor.submit(fetch_executives)
                try:
                    profile_df = profile_future.result()
                except Exception as e:
                    profile_exc = e
                try:
                    executives_df = executives_future.result()
                except Exception as e:
                    executives_exc = e

            # Both endpoints failed → bubble up; outer except returns the error dict
            if profile_exc and executives_exc:
                raise profile_exc

            # Normalize profile_labels: list of {name, value, fieldType}
            profile_labels: List[Dict[str, Any]] = []
            derived_name = ""
            if profile_df is not None and len(profile_df):
                for i in range(len(profile_df)):
                    row = profile_df.iloc[i] if hasattr(profile_df, "iloc") else profile_df[i]
                    name = _to_python_type(row.get("name"), "") or ""
                    value = _to_python_type(row.get("value"), "") or ""
                    # fieldType may be int, string, or None — coerce to int; treat 1/2 as link/title
                    raw_ft = row.get("field_type")
                    if raw_ft is None or (isinstance(raw_ft, float) and raw_ft != raw_ft):
                        field_type = 0
                    else:
                        try:
                            field_type = int(raw_ft)
                        except (TypeError, ValueError):
                            field_type = 0
                    profile_labels.append({
                        "name": str(name),
                        "value": str(value),
                        "fieldType": field_type,
                    })
                # Derive name from first text-type (fieldType == 0) label with non-empty value
                for label in profile_labels:
                    if label["fieldType"] == 0 and label["value"]:
                        derived_name = label["value"]
                        break

            # Normalize executives: list of {name, displayName, position, beginDate, gender, age, education, annualSalary}
            executives: List[Dict[str, Any]] = []
            if executives_df is not None and len(executives_df):
                for i in range(len(executives_df)):
                    row = executives_df.iloc[i] if hasattr(executives_df, "iloc") else executives_df[i]
                    name_val = _to_python_type(row.get("leader_name"), None)
                    display_name = _to_python_type(row.get("display_leader_name"), None)
                    position = _to_python_type(row.get("position_name"), None)
                    begin_date = _to_python_type(row.get("begin_date_str"), None)
                    gender = _to_python_type(row.get("leader_gender"), None)
                    age = _to_python_type(row.get("leader_age"), None)
                    education = _to_python_type(row.get("highest_education"), None)
                    annual_salary = _to_python_type(row.get("annual_salary"), None)

                    def _opt_str(v):
                        if v is None:
                            return None
                        s = str(v).strip()
                        return s if s else None

                    def _opt_int(v):
                        if v is None:
                            return None
                        try:
                            return int(v)
                        except (TypeError, ValueError):
                            return None

                    executives.append({
                        "name": _opt_str(name_val),
                        "displayName": _opt_str(display_name),
                        "position": _opt_str(position),
                        "beginDate": _opt_str(begin_date),
                        "gender": _opt_str(gender),
                        "age": _opt_str(age),
                        "education": _opt_str(education),
                        "annualSalary": _opt_int(annual_salary),
                    })

            return {
                "data": {
                    "symbol": symbol.upper(),
                    "code": futu_code,
                    "market": market,
                    "name": derived_name,
                    "profile_labels": profile_labels,
                    "executives": executives,
                },
                "error": None,
            }

        try:
            return _company_info_cache.on_error_return_stale(cache_key, fetch_company_info)
        except Exception as e:
            logger.error(f"[Futu] {symbol} company info error: {e}")
            err_msg = str(e).lower()
            # Older OpenD (< 10.7.6708) doesn't know the new proto IDs for
            # get_company_profile / get_company_executives. Treat that as
            # "service unavailable" so the panel renders the clean 暂无公司信息
            # placeholder instead of leaking the raw protocol error.
            if "unknown protocol" in err_msg or "unknown proto" in err_msg or "protocol id" in err_msg:
                futu_code, market = _get_futu_code(symbol)
                return {
                    "data": {
                        "symbol": symbol.upper(),
                        "code": futu_code,
                        "market": market,
                        "name": "",
                        "profile_labels": [],
                        "executives": [],
                    },
                    "error": None,
                }
            return {"data": None, "error": f"获取公司信息失败: {str(e)[:120]}"}

    # ----------------------------------------------------------------------
    # Main business composition (Futu get_financials_revenue_breakdown, proto 3228)
    # ----------------------------------------------------------------------
    # RevenueBreakdownType values from Qot_Common.proto:
    #   1 = Product, 2 = Industry, 4 = Region, 8 = Business
    # F10Type values:
    #   7 = Annual report (preferred for cross-period history)
    @classmethod
    def get_revenue_breakdown(cls, symbol: str) -> dict:
        """Get HK/US listed-company main-business composition via Futu
        ``get_financials_revenue_breakdown`` (proto 3228, v10.7+).

        Single call returns ALL breakdown dimensions in ``breakdown_list`` keyed
        by ``type`` (Product=1, Industry=2, Region=4, Business=8). Each item is
        ``{name, main_oper_income, ratio}``. No cost / profit / margin data is
        provided by this Futu endpoint.

        Returns ``{data: <normalized payload>, error: null}`` on success,
        ``{data: <empty>, error: null}`` on empty data or older OpenD that
        doesn't know the proto (treated as clean empty, mirroring
        ``get_company_info``), or ``{data: null, error: <msg>}`` on other
        upstream errors. Cached 24h in ``_company_info_cache``.
        """
        cache_key = f"revenue_breakdown:{symbol.upper()}"

        def fetch_breakdown() -> dict:
            futu_code, market = _get_futu_code(symbol)
            ctx = FutuQuoteService._get_quote_context()
            ret, data = ctx.get_financials_revenue_breakdown(futu_code)
            if ret != 0:
                raise Exception(f"Futu get_financials_revenue_breakdown error: {data}")

            if not isinstance(data, dict):
                return _empty_breakdown_payload(symbol, futu_code, market)

            breakdown_list = data.get("breakdown_list") or []
            if not breakdown_list:
                # Still return screen_date_list so history() can be called without
                # an extra Futu round-trip — cache it together.
                return {
                    "data": _empty_breakdown_payload(symbol, futu_code, market, data),
                    "error": None,
                }

            product, industry, region, business = _split_breakdown_by_type(breakdown_list)
            product_items = {row["item"] for row in product}
            has_distinct_industry = any(
                row["item"] not in product_items for row in industry
            )

            return {
                "data": {
                    "symbol": symbol.upper(),
                    "code": futu_code,
                    "market": market,
                    "period": data.get("period", ""),
                    "currency_code": data.get("currency_code", ""),
                    "product": product,
                    "region": region,
                    "industry": industry,
                    "business": business,
                    "has_distinct_industry": has_distinct_industry,
                    "screen_date_list": data.get("screen_date_list", []),
                    "source": "futu",
                    "updated_at": datetime.now().isoformat(),
                },
                "error": None,
            }

        try:
            return _company_info_cache.on_error_return_stale(cache_key, fetch_breakdown)
        except Exception as e:
            logger.error(f"[Futu] {symbol} revenue breakdown error: {e}")
            err_msg = str(e).lower()
            # Older OpenD (< 10.7.6708) doesn't know proto 3228. Treat as
            # clean empty so the panel renders the "暂无主营业务构成数据"
            # placeholder instead of leaking the raw protocol error.
            if "unknown protocol" in err_msg or "unknown proto" in err_msg or "protocol id" in err_msg:
                futu_code, market = _get_futu_code(symbol)
                return {
                    "data": _empty_breakdown_payload(symbol, futu_code, market),
                    "error": None,
                }
            return {"data": None, "error": f"获取主营构成失败: {str(e)[:120]}"}

    @classmethod
    def get_revenue_breakdown_history(
        cls, symbol: str, n_periods: int = 4
    ) -> dict:
        """Get last N annual periods of by-product data for cross-period view.

        Strategy: first call ``get_revenue_breakdown`` to obtain the
        ``screen_date_list``, filter for annual periods (preferring
        ``financial_type == 7`` 年报, falling back to ``period_text`` ending in
        ``/FY``), then fire N parallel ``get_financials_revenue_breakdown``
        calls (each with a different ``date`` epoch-seconds value) and merge
        the results into a ``{periods, items}`` shape similar to the A-share
        history endpoint.

        Top-3 items by latest-period revenue are kept; the rest are bucketed
        as ``其他``. Each ``values`` array length equals ``periods.length``.
        Cached 24h in ``_company_info_cache``.
        """
        cache_key = f"revenue_breakdown_history:{symbol.upper()}:{n_periods}"

        def fetch_history() -> dict:
            futu_code, market = _get_futu_code(symbol)
            latest_resp = FutuQuoteService.get_revenue_breakdown(symbol)
            latest_data = latest_resp.get("data") or {}
            if latest_resp.get("error") or not latest_data:
                return {
                    "data": {
                        "symbol": symbol.upper(),
                        "code": futu_code,
                        "market": market,
                        "currency_code": latest_data.get("currency_code", ""),
                        "periods": [],
                        "items": [],
                        "source": "futu",
                        "updated_at": datetime.now().isoformat(),
                    },
                    "error": None,
                }

            screen_date_list = latest_data.get("screen_date_list", []) or []
            annual_dates = _pick_annual_screen_dates(screen_date_list, n_periods)
            if not annual_dates:
                return {
                    "data": {
                        "symbol": symbol.upper(),
                        "code": futu_code,
                        "market": market,
                        "currency_code": latest_data.get("currency_code", ""),
                        "periods": [],
                        "items": [],
                        "source": "futu",
                        "updated_at": datetime.now().isoformat(),
                    },
                    "error": None,
                }

            ctx = FutuQuoteService._get_quote_context()
            period_results: Dict[int, dict] = {}
            period_excs: Dict[int, str] = {}

            import concurrent.futures

            def fetch_one(d: int):
                ret, data = ctx.get_financials_revenue_breakdown(
                    futu_code, date=d
                )
                if ret != 0 or not isinstance(data, dict):
                    raise Exception(
                        f"Futu get_financials_revenue_breakdown(date={d}) error"
                    )
                return d, data

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(annual_dates))) as ex:
                futures = [ex.submit(fetch_one, d) for d in annual_dates]
                for fut in futures:
                    try:
                        d, data = fut.result()
                        period_results[d] = data
                    except Exception as e:
                        # Record the first epoch-seconds we couldn't fetch (best-effort)
                        period_excs[annual_dates[len(period_results)]] = str(e)[:80]

            if not period_results:
                return {
                    "data": {
                        "symbol": symbol.upper(),
                        "code": futu_code,
                        "market": market,
                        "currency_code": latest_data.get("currency_code", ""),
                        "periods": [],
                        "items": [],
                        "source": "futu",
                        "updated_at": datetime.now().isoformat(),
                    },
                    "error": None,
                }

            # Order periods chronologically (oldest first) and remember each
            # one's period_text for the x-axis.
            ordered_dates = sorted(period_results.keys())
            periods = [period_results[d].get("period", "") for d in ordered_dates]
            currency_code = (
                period_results[ordered_dates[-1]].get("currency_code")
                or latest_data.get("currency_code", "")
            )

            # Latest-period by-product list (to pick top-3).
            latest_breakdown = period_results[ordered_dates[-1]].get("breakdown_list", [])
            latest_product = next(
                (b.get("item_list", []) for b in latest_breakdown if b.get("type") == 1),
                [],
            )
            latest_sorted = sorted(
                [r for r in latest_product if _item_has_revenue(r)],
                key=lambda r: r.get("main_oper_income", 0) or 0,
                reverse=True,
            )
            top_items = [r["name"] for r in latest_sorted[:3]]
            other_items = [
                r["name"]
                for r in latest_sorted[3:]
            ]
            kept_items = set(top_items) | set(other_items)
            if other_items:
                # "其他" bucket — keep the label distinct from any real item name.
                pass

            # Build the per-item series: for each kept item, collect revenue
            # across the 4 ordered periods; for the "其他" bucket, sum the
            # non-top-3 items per period.
            series: Dict[str, Dict[str, Any]] = {}
            for name in top_items:
                series[name] = {
                    "item": name,
                    "currency_code": currency_code,
                    "values": [],
                }
            if other_items:
                series["其他"] = {
                    "item": "其他",
                    "currency_code": currency_code,
                    "values": [],
                }

            for d in ordered_dates:
                data = period_results[d]
                breakdown = data.get("breakdown_list", [])
                product_list = next(
                    (b.get("item_list", []) for b in breakdown if b.get("type") == 1),
                    [],
                )
                # Build a name -> item dict for this period
                by_name = {
                    r.get("name", ""): r
                    for r in product_list
                    if r.get("name")
                }
                period_label = data.get("period", "")
                for name in top_items:
                    r = by_name.get(name)
                    series[name]["values"].append(
                        {
                            "period": period_label,
                            "revenue": float(r.get("main_oper_income", 0) or 0)
                            if r
                            else 0.0,
                            "ratio_pct": float(r.get("ratio", 0) or 0) if r else 0.0,
                        }
                    )
                if other_items:
                    other_revenue = 0.0
                    other_ratio = 0.0
                    for name in other_items:
                        r = by_name.get(name)
                        if r:
                            other_revenue += float(r.get("main_oper_income", 0) or 0)
                            other_ratio += float(r.get("ratio", 0) or 0)
                    series["其他"]["values"].append(
                        {
                            "period": period_label,
                            "revenue": other_revenue,
                            "ratio_pct": other_ratio,
                        }
                    )

            # Order items: top-3 first by latest-period revenue, "其他" last.
            ordered_items: List[Dict[str, Any]] = []
            for name in top_items:
                if name in series:
                    ordered_items.append(series[name])
            if "其他" in series:
                ordered_items.append(series["其他"])

            return {
                "data": {
                    "symbol": symbol.upper(),
                    "code": futu_code,
                    "market": market,
                    "currency_code": currency_code,
                    "periods": periods,
                    "items": ordered_items,
                    "source": "futu",
                    "updated_at": datetime.now().isoformat(),
                },
                "error": None,
            }

        try:
            return _company_info_cache.on_error_return_stale(cache_key, fetch_history)
        except Exception as e:
            logger.error(f"[Futu] {symbol} revenue breakdown history error: {e}")
            err_msg = str(e).lower()
            if "unknown protocol" in err_msg or "unknown proto" in err_msg or "protocol id" in err_msg:
                futu_code, market = _get_futu_code(symbol)
                return {
                    "data": {
                        "symbol": symbol.upper(),
                        "code": futu_code,
                        "market": market,
                        "currency_code": "",
                        "periods": [],
                        "items": [],
                        "source": "futu",
                        "updated_at": datetime.now().isoformat(),
                    },
                    "error": None,
                }
            return {"data": None, "error": f"获取跨期主营构成失败: {str(e)[:120]}"}


def _item_has_revenue(item: dict) -> bool:
    """Return True if the breakdown item has a non-zero main_oper_income."""
    val = item.get("main_oper_income")
    if val is None:
        return False
    try:
        return float(val) > 0
    except (TypeError, ValueError):
        return False


def _normalize_breakdown_item(item: dict, default_currency: str) -> dict:
    """Normalize a single breakdown item from the raw Futu shape to the
    response shape used by the panel:
    ``{item, revenue, ratio_pct, currency_code}``.
    """
    name = str(item.get("name", "")).strip() or ""
    revenue = _to_python_type(item.get("main_oper_income"), 0.0) or 0.0
    try:
        revenue = float(revenue)
    except (TypeError, ValueError):
        revenue = 0.0
    ratio = _to_python_type(item.get("ratio"), 0.0) or 0.0
    try:
        ratio = float(ratio)
    except (TypeError, ValueError):
        ratio = 0.0
    return {
        "item": name,
        "revenue": revenue,
        "ratio_pct": round(ratio, 2),
        "currency_code": default_currency or "",
    }


def _split_breakdown_by_type(
    breakdown_list: list,
) -> tuple:
    """Split Futu ``breakdown_list`` by ``type`` into 4 lists of normalized
    items, sorted by revenue desc, deduped.

    Types: 1=Product, 2=Industry, 4=Region, 8=Business. Items with zero/null
    revenue are dropped. Fully duplicate ``(item, revenue, ratio_pct,
    currency_code)`` tuples are deduplicated (keep first).
    """
    product: list = []
    industry: list = []
    region: list = []
    business: list = []

    for group in breakdown_list:
        if not isinstance(group, dict):
            continue
        btype = group.get("type")
        items = group.get("item_list") or []
        if btype == 1:
            target = product
        elif btype == 2:
            target = industry
        elif btype == 4:
            target = region
        elif btype == 8:
            target = business
        else:
            continue
        for raw in items:
            if not isinstance(raw, dict):
                continue
            if not _item_has_revenue(raw):
                continue
            item_currency = str(raw.get("currency_code", "")).strip()
            if not item_currency:
                item_currency = ""
            target.append(_normalize_breakdown_item(raw, item_currency))

    for bucket in (product, industry, region, business):
        bucket.sort(key=lambda r: r["revenue"], reverse=True)
        # Dedup by full tuple
        seen = set()
        deduped = []
        for r in bucket:
            key = (r["item"], r["revenue"], r["ratio_pct"], r["currency_code"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)
        bucket[:] = deduped

    return product, industry, region, business


def _empty_breakdown_payload(
    symbol: str, futu_code: str, market: str, raw: dict = None
) -> dict:
    """Build an empty (but well-formed) revenue breakdown payload."""
    return {
        "symbol": symbol.upper() if symbol else "",
        "code": futu_code,
        "market": market,
        "period": (raw or {}).get("period", ""),
        "currency_code": (raw or {}).get("currency_code", ""),
        "product": [],
        "region": [],
        "industry": [],
        "business": [],
        "has_distinct_industry": False,
        "screen_date_list": (raw or {}).get("screen_date_list", []),
        "source": "futu",
        "updated_at": datetime.now().isoformat(),
    }


def _pick_annual_screen_dates(screen_date_list: list, n: int) -> list:
    """Pick up to ``n`` most recent annual period ``date`` values from
    ``screen_date_list``.

    Preference: entries with ``financial_type == 7`` (年报). Fallback: entries
    whose ``period_text`` ends in ``/FY`` (case-insensitive). Returns the
    epoch-seconds ``date`` values in descending order (most recent first).
    """
    if not screen_date_list:
        return []

    annual = [
        e
        for e in screen_date_list
        if isinstance(e, dict) and e.get("financial_type") == 7
    ]
    if not annual:
        annual = [
            e
            for e in screen_date_list
            if isinstance(e, dict)
            and isinstance(e.get("period_text"), str)
            and e["period_text"].strip().upper().endswith("/FY")
        ]
    if not annual:
        return []

    annual_sorted = sorted(
        [e for e in annual if isinstance(e.get("date"), int)],
        key=lambda e: e["date"],
        reverse=True,
    )
    return [e["date"] for e in annual_sorted[:n]]
