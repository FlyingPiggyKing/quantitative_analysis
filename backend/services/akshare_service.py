"""Stock data service using Tushare Pro API."""
import os
from pathlib import Path
from dotenv import load_dotenv
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# Load .env before reading environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Tushare token from environment variable
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
if TUSHARE_TOKEN:
    ts.set_token(TUSHARE_TOKEN)


def _symbol_to_ts_code(symbol: str) -> str:
    """Convert symbol to Tushare ts_code format."""
    symbol = symbol.strip()

    if "." in symbol:
        return symbol.upper()

    if len(symbol) == 6:
        if symbol.startswith(('6', '9', '5')):
            return f"{symbol}.SH"
        else:
            return f"{symbol}.SZ"
    return symbol


class AkshareService:
    """Service wrapper for Tushare stock data API."""

    @staticmethod
    def get_stock_info(symbol: str) -> dict:
        """Get basic stock information."""
        try:
            ts_code = _symbol_to_ts_code(symbol)

            # Try realtime quotes first (more reliable, no rate limit for basic info)
            try:
                quotes = ts.get_realtime_quotes(symbol)
                if quotes is not None and not quotes.empty:
                    name = quotes.iloc[0].get("name", "未知")
                    if name and name != "unknown":
                        return {
                            "symbol": symbol,
                            "name": name,
                            "market": "未知",
                            "sector": "未知",
                        }
            except:
                pass

            # Fallback to stock_basic (rate limited)
            try:
                df = ts.pro_api().stock_basic(ts_code=ts_code, fields='ts_code,symbol,name,area,industry,market,list_date')
                if df is not None and not df.empty:
                    row = df.iloc[0]
                    return {
                        "symbol": symbol,
                        "name": row.get("name", "未知"),
                        "market": row.get("market", "未知"),
                        "sector": row.get("industry", "未知"),
                    }
            except Exception as e:
                if "权限" not in str(e) and "每分钟" not in str(e):
                    raise

            # Last resort: try daily to verify stock exists
            try:
                df = ts.pro_api().daily(ts_code=ts_code, start_date='20260401', end_date='20260406')
                if df is not None and not df.empty:
                    return {
                        "symbol": symbol,
                        "name": f"股票{symbol}",
                        "market": "未知",
                        "sector": "未知",
                    }
            except:
                pass

            return {"symbol": symbol, "error": "Stock not found"}
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    @staticmethod
    def get_kline_data(
        symbol: str,
        days: int = 100,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> dict:
        """Get K-line data for a stock."""
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
        """Get real-time quote for a stock."""
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
        rsi6 = AkshareService._rsi(closes, 6)
        rsi12 = AkshareService._rsi(closes, 12)
        rsi24 = AkshareService._rsi(closes, 24)

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

    @staticmethod
    def _rsi(prices, period: int = 14) -> list:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.dropna().values.tolist()

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
    def get_valuation_data(symbol: str, days: int = 100) -> dict:
        """Get PE, PB, and turnover rate data from Tushare daily_basic endpoint."""
        try:
            ts_code = _symbol_to_ts_code(symbol)
            pro = ts.pro_api()

            # Determine date range
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            # Fetch daily_basic data (includes pe, pb, turnover_rate)
            df = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return {"symbol": symbol, "error": "No valuation data found"}

            # Convert date format
            df["date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")

            # Sort by date
            df = df.sort_values("date")

            # Take last N days
            df = df.tail(days)

            # Get current (most recent) values
            latest = df.iloc[-1]
            current = {
                "pe": float(latest["pe"]) if pd.notna(latest["pe"]) else None,
                "pb": float(latest["pb"]) if pd.notna(latest["pb"]) else None,
                "turnover_rate": float(latest["turnover_rate"]) if pd.notna(latest["turnover_rate"]) else None,
            }

            # Build history array
            history = []
            for _, row in df.iterrows():
                history.append({
                    "date": row["date"],
                    "pe": float(row["pe"]) if pd.notna(row["pe"]) else None,
                    "pb": float(row["pb"]) if pd.notna(row["pb"]) else None,
                })

            return {
                "symbol": symbol,
                "current": current,
                "history": history,
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}
