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


class USStockService:
    """Service wrapper for US stock data via Yahoo Finance API."""

    @staticmethod
    def get_stock_info(symbol: str) -> dict:
        """Get basic US stock information via Yahoo Finance (with 5-minute cache)."""
        cache_key = f"info:{symbol.upper()}"

        def fetch_info() -> dict:
            logger.info(f"[美股] Fetching info for {symbol} via Yahoo Finance (WITH PROXY: {_yf_proxy is not None})")
            yf_symbol = _us_symbol_to_yf_code(symbol)
            with _ProxyContext():
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info

            # Check for rate limiting - Yahoo Finance returns limited data when rate limited
            if info is None or info.get("regularMarketPrice") is None:
                # Check if this is a rate limit situation by looking at other indicators
                if info and info.get("symbol") == yf_symbol:
                    # Symbol exists but no price data - likely rate limited
                    logger.warning(f"[美股] {symbol} - rate limited by Yahoo Finance")
                    raise YFRateLimitError(f"Rate limited for {symbol}")
                logger.warning(f"[美股] {symbol} - stock not found")
                return {"symbol": symbol, "error": "Stock not found"}

            logger.info(f"[美股] {symbol} found: {info.get('shortName')}")
            return {
                "symbol": symbol.upper(),
                "name": info.get("shortName") or info.get("longName", "未知"),
                "market": "US",
                "sector": info.get("sector", "未知"),
            }

        try:
            return _yf_cache.on_error_return_stale(cache_key, fetch_info, max_stale_seconds=3600)
        except YFRateLimitError:
            return {"symbol": symbol, "error": "Rate limited by Yahoo Finance, please try again later"}
        except Exception as e:
            logger.error(f"[美股] {symbol} error: {e}")
            error_str = str(e).lower()
            if "rate" in error_str or "too many" in error_str or "429" in error_str:
                return {"symbol": symbol, "error": "Rate limited by Yahoo Finance, please try again later"}
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_kline_data(
        symbol: str,
        days: int = 100,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> dict:
        """Get K-line data for a US stock via Yahoo Finance (with 5-minute cache)."""
        cache_key = f"kline:{symbol.upper()}:{days}"

        def fetch_kline() -> dict:
            yf_symbol = _us_symbol_to_yf_code(symbol)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)

            with _ProxyContext():
                ticker = yf.Ticker(yf_symbol)
                # Fetch historical data
                hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="1d")

            if hist is None or hist.empty:
                raise YFRateLimitError(f"Rate limited for {symbol} kline")

            # Rename columns to match A-share format
            hist = hist.rename(columns={
                "Open": "open",
                "Close": "close",
                "High": "high",
                "Low": "low",
                "Volume": "volume",
            })

            # Convert index (date) to column
            hist = hist.reset_index()
            hist["date"] = hist["Date"].dt.strftime("%Y-%m-%d")

            # Calculate change_pct
            hist["change_pct"] = hist["close"].pct_change() * 100

            # Sort by date
            hist = hist.sort_values("date")

            # Take last N days
            hist = hist.tail(days)

            data = hist[["date", "open", "close", "high", "low", "volume", "change_pct"]].to_dict("records")

            return {
                "symbol": symbol,
                "period": period,
                "data": data
            }

        try:
            return _yf_cache.on_error_return_stale(cache_key, fetch_kline, max_stale_seconds=3600)
        except YFRateLimitError:
            return {"symbol": symbol, "error": "Rate limited by Yahoo Finance, please try again later"}
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_realtime_quote(symbol: str) -> dict:
        """Get real-time quote for a US stock via Yahoo Finance (with 2-minute cache)."""
        cache_key = f"realtime:{symbol.upper()}"

        def fetch_quote() -> dict:
            yf_symbol = _us_symbol_to_yf_code(symbol)
            with _ProxyContext():
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                fast_info = ticker.fast_info

            if info is None or info.get("regularMarketPrice") is None:
                raise YFRateLimitError(f"Rate limited for {symbol} quote")

            def safe_float(val):
                try:
                    return float(val) if val is not None else 0.0
                except (TypeError, ValueError):
                    return 0.0

            current_price = info.get("regularMarketPrice", 0)
            prev_close = info.get("regularMarketPreviousClose", 0)
            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0

            return {
                "symbol": symbol,
                "name": info.get("shortName", "未知"),
                "price": safe_float(current_price),
                "change_pct": change_pct,
                "volume": safe_float(info.get("regularMarketVolume")),
                "amount": 0.0,  # Not available in yfinance
                "high": safe_float(info.get("regularMarketDayHigh")),
                "low": safe_float(info.get("regularMarketDayLow")),
                "open": safe_float(info.get("regularMarketOpen")),
                "close_prev": safe_float(prev_close),
            }

        try:
            return _yf_cache.on_error_return_stale(cache_key, fetch_quote, max_stale_seconds=600)
        except YFRateLimitError:
            return {"symbol": symbol, "error": "Rate limited by Yahoo Finance, please try again later"}
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "too many" in error_str or "429" in error_str:
                return {"symbol": symbol, "error": "Rate limited by Yahoo Finance, please try again later"}
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_daily_basic(symbol: str, days: int = 30) -> dict:
        """Get daily basic metrics for US stock via Yahoo Finance (with 5-minute cache)."""
        cache_key = f"daily_basic:{symbol.upper()}:{days}"

        def fetch_basic() -> dict:
            yf_symbol = _us_symbol_to_yf_code(symbol)
            with _ProxyContext():
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info

            if info is None or info.get("regularMarketPrice") is None:
                raise YFRateLimitError(f"Rate limited for {symbol} daily_basic")

            def safe_float(val):
                try:
                    return float(val) if val is not None else None
                except (TypeError, ValueError):
                    return None

            # Yahoo Finance provides trailingPE, priceToBook, marketCap, dividendYield
            pe_ttm = info.get("trailingPE")
            pb = info.get("priceToBook")
            market_cap = info.get("marketCap")
            dividend_yield = info.get("dividendYield")

            # For historical records, we create a single record with latest data
            # Note: yfinance's info is point-in-time, not historical series
            trade_date = datetime.now().strftime("%Y-%m-%d")

            record = {
                "trade_date": trade_date,
                "pe_ttm": safe_float(pe_ttm),
                "pb": safe_float(pb),
                "turnover_rate": None,  # Not available in yfinance
                "total_mv": safe_float(market_cap),
                "circ_mv": safe_float(market_cap),  # Use market cap as approximation
            }

            return {
                "symbol": symbol,
                "data": [record],
                "latest": record,
            }

        try:
            return _yf_cache.on_error_return_stale(cache_key, fetch_basic, max_stale_seconds=3600)
        except YFRateLimitError:
            return {"symbol": symbol, "error": "Rate limited by Yahoo Finance, please try again later"}
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "too many" in error_str or "429" in error_str:
                return {"symbol": symbol, "error": "Rate limited by Yahoo Finance, please try again later"}
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_daily_basic_batch(symbols: List[str], days: int = 30) -> dict:
        """Get daily basic metrics for multiple US stock symbols in a single batch request."""
        import concurrent.futures

        results = []
        errors = []

        def fetch_single(symbol: str) -> dict:
            return USStockService.get_daily_basic(symbol, days)

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
        """Get basic US stock information for multiple symbols in a single batch request."""
        import concurrent.futures
        import time

        results = []
        errors = []
        start_time = time.time()

        def fetch_single(symbol: str) -> dict:
            s_start = time.time()
            result = USStockService.get_stock_info(symbol)
            logger.info(f"[美股] Batch fetch {symbol} completed in {time.time() - s_start:.2f}s")
            return result

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
                    logger.error(f"[美股] Batch fetch {symbol} exception: {e}")
                    errors.append({"symbol": symbol, "error": str(e)})

        logger.info(f"[美股] Batch info total time: {time.time() - start_time:.2f}s for {len(symbols)} symbols")
        return {"results": results, "errors": errors}


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
    if symbol.upper().endswith(".US") or _is_us_stock_symbol(symbol):
        return USStockService.get_daily_basic(symbol, days)
    else:
        return AShareService.get_daily_basic(symbol, days)


def _is_us_stock_symbol(symbol: str) -> bool:
    """Check if a symbol appears to be a US stock (not a 6-digit A-share code)."""
    symbol = symbol.strip().upper()
    # US stocks are typically 1-5 letters
    if symbol.endswith(".US"):
        return True
    if len(symbol) <= 5 and not symbol.isdigit():
        return True
    return False
