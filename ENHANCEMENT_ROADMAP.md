# Stock Trend Prediction Enhancement Roadmap

> Generated: 2026-04-12
> Project: quantitative_analysis (FastAPI + Next.js)

---

## Executive Summary

The current system predicts 2-week stock trends using **only** Tavily news search + LLM reasoning (MiniMax DeepAgent). It has no access to structured financial data beyond basic K-line prices. Research shows that combining structured quantitative data (money flow, valuation, technicals) with LLM-based sentiment analysis can improve prediction accuracy by **15-20%** over news-only approaches.

This roadmap is organized into **7 phases**, each self-contained and implementable independently. Phases are ordered by **impact-to-effort ratio** — do Phase 1 first for the biggest bang.

### Current State

| Component | Status | Details |
|-----------|--------|---------|
| K-line data (daily OHLCV) | Done | `pro.daily()` via Tushare |
| Technical indicators | Done | MACD(12,26,9), RSI(6,12,24), MA(5,10,20,60) |
| News sentiment | Done | Tavily search + MiniMax LLM agent |
| Money flow data | Done | Injected into AI agent via `get_moneyflow()`; rendered in `技术分析` panel |
| Main business composition (A-share) | Done | Tushare `fina_mainbz` → 按产品 / 按地区 / 按行业 / 跨期对比 panel (`<MainBusinessPanel />`) |
| Main business composition (HK / US) | Done | Futu `get_financials_revenue_breakdown` (proto 3228) → revenue-only 按产品 / 按地区 / 按行业 / 业务 / 跨期对比 panel; requires Futu OpenD v10.7.6708+ |
| Valuation metrics | Missing | No PE/PB/turnover data |
| Index/market context | Missing | No market-wide data |
| Financial fundamentals | Missing | No earnings/ROE data |
| Multi-factor scoring | Missing | No structured scoring system |
| Financial report analysis (财报分析) | Missing | No earnings/ROE data |
| Industry position (行业地位) | Missing | No market share/competitive position data |
| Government policy (政府策略) | Missing | No policy impact analysis |
| World events (世界大事) | Missing | No macro-global event analysis |
| Company development plans (公司发展计划) | Missing | No M&A/capital raising/strategic moves data |
| Sector analysis (板块分析) | Missing | No industry/sector trend data |
| Daily highlights (每日要闻) | Missing | No daily market news digest |

### Tushare Token Status

Current token: `89b0a6a...` — **verify your point level** before starting. Run:
```python
import tushare as ts
ts.set_token('your_token')
pro = ts.pro_api()
# Try each API to see what you have access to
```

### Key Files

| File | Purpose |
|------|---------|
| `backend/services/akshare_service.py` | Tushare data fetching + indicator calculation |
| `backend/services/stock_trend_agent.py` | LLM trend analysis agent (DeepAgent + Tavily) |
| `backend/services/tavily_search_tool.py` | Tavily web search tool |
| `backend/api/stock.py` | Stock data API endpoints |
| `backend/api/trend_prediction.py` | Prediction API endpoints |
| `backend/services/trend_prediction_service.py` | Prediction DB operations |
| `backend/services/task_queue.py` | Background task processing |
| `frontend/src/app/stock/[symbol]/page.tsx` | Stock detail page |
| `frontend/src/app/page.tsx` | Home page with analysis trigger |

---

## Phase 1: Enrich the LLM Agent with Existing Technical Data

**Goal**: Feed the existing K-line data and technical indicators into the LLM agent's context, so it makes decisions based on both news AND price data instead of news alone.

**Impact**: HIGH | **Effort**: LOW | **Tushare Points Required**: None (uses existing data)

### Why This Matters

Currently, `stock_trend_agent.py` receives ONLY the stock symbol and name. It searches for news via Tavily and makes predictions purely based on news sentiment. It never sees the actual price data, MACD signals, RSI levels, or moving average positions that are already computed in `akshare_service.py`. This is the single biggest gap.

### Changes Required

#### 1.1 Modify `analyze_stock_trend()` in `stock_trend_agent.py`

Before calling the LLM agent, fetch and format the stock's quantitative data:

```python
def analyze_stock_trend(symbol: str, name: str) -> Dict[str, Any]:
    # Step 1: Fetch K-line data (last 60 days)
    kline_result = AkshareService.get_kline_data(symbol, days=60)
    kline_data = kline_result.get("data", [])

    # Step 2: Calculate technical indicators
    indicators = AkshareService.calculate_indicators(kline_data)

    # Step 3: Format recent price summary (last 10 trading days)
    recent_prices = kline_data[-10:] if len(kline_data) >= 10 else kline_data

    # Step 4: Build structured data context string
    data_context = format_data_context(recent_prices, indicators)

    # Step 5: Pass to LLM agent as part of user message
    user_message = f"""请分析股票 {name} ({symbol}) 的未来2周趋势。

## 技术数据
{data_context}

请使用 tavily_search 工具搜索最新新闻，然后结合以上技术数据给出预测。
"""
```

#### 1.2 Create `format_data_context()` helper

```python
def format_data_context(recent_prices: list, indicators: dict) -> str:
    """Format quantitative data as readable text for LLM context."""
    lines = []

    # Recent price trend
    if recent_prices:
        first = recent_prices[0]
        last = recent_prices[-1]
        change = ((last['close'] - first['close']) / first['close']) * 100
        lines.append(f"近10日走势: 从{first['close']}到{last['close']}, 涨跌幅{change:.2f}%")
        lines.append(f"最新收盘价: {last['close']}, 最高: {last['high']}, 最低: {last['low']}")

        # Volume trend
        avg_vol = sum(p['volume'] for p in recent_prices) / len(recent_prices)
        last_vol = recent_prices[-1]['volume']
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
        lines.append(f"成交量比: {vol_ratio:.2f} (>1放量, <1缩量)")

    # MACD signals
    macd = indicators.get("macd", {})
    if macd:
        dif, dea, hist = macd.get("dif", 0), macd.get("dea", 0), macd.get("hist", 0)
        signal = "金叉(看多)" if dif > dea else "死叉(看空)"
        lines.append(f"MACD: DIF={dif:.4f}, DEA={dea:.4f}, 柱状={hist:.4f}, 信号={signal}")

    # RSI signals
    rsi = indicators.get("rsi", {})
    if rsi:
        rsi6 = rsi.get("rsi6", 50)
        zone = "超买区(>80)" if rsi6 > 80 else "超卖区(<20)" if rsi6 < 20 else "正常区间"
        lines.append(f"RSI(6): {rsi6:.2f} - {zone}")

    # MA signals
    ma = indicators.get("ma", {})
    if ma and recent_prices:
        price = recent_prices[-1]['close']
        ma5 = ma.get("ma5", 0)
        ma20 = ma.get("ma20", 0)
        above_ma5 = "在5日均线上方" if price > ma5 else "在5日均线下方"
        above_ma20 = "在20日均线上方" if price > ma20 else "在20日均线下方"
        lines.append(f"均线: {above_ma5}, {above_ma20}")

    return "\n".join(lines)
```

#### 1.3 Update the System Prompt

Add instructions for the LLM to use technical data:

```
## Your Process

1. **Analyze the provided technical data**: Review the K-line data, MACD, RSI, and MA signals provided in the message.
2. **Search for stock-specific news**: Use tavily_search for recent news.
3. **Search for macro environment**: Use tavily_search for macro factors.
4. **Combine technical + sentiment analysis**: Weight technical signals (40%) and news sentiment (60%) to form your prediction.
5. **Return prediction JSON**.
```

#### 1.4 No Frontend Changes Needed

The prediction output format (`trend_direction`, `confidence`, `summary`) stays the same.

---

## Phase 2: Add Daily Valuation Metrics (daily_basic)

**Goal**: Add PE ratio, PB ratio, turnover rate, total market value, and circulation market value to each stock's data and feed it to the LLM agent.

**Impact**: HIGH | **Effort**: LOW | **Tushare Points Required**: 120+ (basic access)

### Why This Matters

`daily_basic` provides critical valuation context. A stock with RSI=30 and PE at 5-year low is a much stronger buy signal than RSI=30 alone. Turnover rate (换手率) is one of the most effective short-term predictive features in A-share markets.

### Changes Required

#### 2.1 Add `get_daily_basic()` to `akshare_service.py`

```python
@staticmethod
def get_daily_basic(symbol: str, days: int = 30) -> dict:
    """Get daily basic metrics (PE, PB, turnover, market cap)."""
    try:
        ts_code = _symbol_to_ts_code(symbol)
        pro = ts.pro_api()

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        df = pro.daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,trade_date,turnover_rate,pe_ttm,pb,ps_ttm,total_mv,circ_mv,dv_ratio'
        )

        if df is None or df.empty:
            return {"symbol": symbol, "error": "No daily_basic data"}

        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
        df = df.sort_values("trade_date").tail(days)

        return {
            "symbol": symbol,
            "data": df.to_dict("records"),
            "latest": df.iloc[-1].to_dict()
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}
```

#### 2.2 Add API Endpoint in `stock.py`

```python
@router.get("/api/stock/{symbol}/valuation")
async def get_stock_valuation(symbol: str, days: int = Query(default=30, ge=1, le=365)):
    return AkshareService.get_daily_basic(symbol, days)
```

#### 2.3 Integrate into LLM Agent Context

In `format_data_context()`, add:

```python
# Valuation metrics
if valuation_data:
    latest = valuation_data.get("latest", {})
    lines.append(f"PE(TTM): {latest.get('pe_ttm', 'N/A')}")
    lines.append(f"PB: {latest.get('pb', 'N/A')}")
    lines.append(f"换手率: {latest.get('turnover_rate', 'N/A')}%")
    lines.append(f"总市值: {latest.get('total_mv', 'N/A')}万元")
```

#### 2.4 Frontend: Show Valuation on Stock Detail Page

Add a "Valuation" section to the stock detail page showing:
- PE(TTM) with historical chart (mini sparkline)
- PB ratio
- Turnover rate
- Total market cap

---

## Phase 3: Add Market Context (Index Data + Interest Rates)

**Goal**: Provide market-wide context so the LLM can assess whether the overall market supports or hinders a stock's trend.

**Impact**: MEDIUM-HIGH | **Effort**: LOW | **Tushare Points Required**: 120+ (basic access)

### Why This Matters

Research shows that ~60-70% of individual stock movement correlates with the broader market. A bullish stock signal during a market downturn is far less reliable. Northbound capital sentiment and market index trends are among the strongest leading indicators for A-shares.

### Changes Required

#### 3.1 Add `get_index_daily()` to `akshare_service.py`

```python
@staticmethod
def get_index_daily(index_code: str = "000001.SH", days: int = 30) -> dict:
    """Get index daily data (default: Shanghai Composite 上证指数)."""
    try:
        pro = ts.pro_api()
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        df = pro.index_daily(
            ts_code=index_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,trade_date,close,open,high,low,vol,amount,pct_chg'
        )

        if df is None or df.empty:
            return {"index": index_code, "error": "No index data"}

        df = df.sort_values("trade_date").tail(days)
        return {
            "index": index_code,
            "data": df.to_dict("records"),
            "latest": df.iloc[-1].to_dict(),
            "trend_5d": df.tail(5)["pct_chg"].sum(),  # 5-day cumulative change
            "trend_20d": df.tail(20)["pct_chg"].sum(),  # 20-day cumulative change
        }
    except Exception as e:
        return {"index": index_code, "error": str(e)}
```

#### 3.2 Add `get_shibor()` for Interest Rate Context

```python
@staticmethod
def get_shibor(days: int = 30) -> dict:
    """Get SHIBOR interest rate data."""
    try:
        pro = ts.pro_api()
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        df = pro.shibor(start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            return {"error": "No SHIBOR data"}

        df = df.sort_values("date").tail(days)
        return {
            "data": df.to_dict("records"),
            "latest_on": df.iloc[-1].get("on", None),  # overnight rate
            "latest_1w": df.iloc[-1].get("1w", None),   # 1-week rate
        }
    except Exception as e:
        return {"error": str(e)}
```

#### 3.3 Integrate into LLM Agent Context

Add to the user message:

```python
# Market context
market_context = []
index_sh = AkshareService.get_index_daily("000001.SH", days=20)
if "error" not in index_sh:
    market_context.append(f"上证指数: 最新{index_sh['latest']['close']}, 5日涨跌{index_sh['trend_5d']:.2f}%, 20日涨跌{index_sh['trend_20d']:.2f}%")

index_sz = AkshareService.get_index_daily("399001.SZ", days=20)
if "error" not in index_sz:
    market_context.append(f"深证成指: 最新{index_sz['latest']['close']}, 5日涨跌{index_sz['trend_5d']:.2f}%")

shibor = AkshareService.get_shibor(days=10)
if "error" not in shibor:
    market_context.append(f"SHIBOR隔夜: {shibor['latest_on']}%, 1周: {shibor['latest_1w']}%")
```

#### 3.4 No Frontend Changes Required for This Phase

Market context is consumed by the LLM agent. Optionally, add a "Market Overview" widget to the home page later.

---

## Phase 4: Enhanced Technical Indicators (KDJ, BOLL, Volume-Price)

**Goal**: Add KDJ, Bollinger Bands, volume-price divergence detection, and OBV to the indicator set. These complement MACD/RSI and significantly improve short-term signal quality.

**Impact**: MEDIUM | **Effort**: MEDIUM | **Tushare Points Required**: None (calculated locally)

### Why This Matters

- **KDJ** is the most widely followed short-term indicator in A-share markets
- **Bollinger Bands** identify volatility squeeze/expansion patterns
- **Volume-Price Divergence** (量价背离) is one of the most reliable reversal signals
- **OBV** (On Balance Volume) tracks cumulative buying/selling pressure

### Changes Required

#### 4.1 Add Indicators to `calculate_indicators()` in `akshare_service.py`

```python
# KDJ (9, 3, 3)
def _kdj(high, low, close, n=9, m1=3, m2=3):
    low_n = low.rolling(n).min()
    high_n = high.rolling(n).max()
    rsv = (close - low_n) / (high_n - low_n) * 100
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

# Bollinger Bands (20, 2)
def _bollinger(close, n=20, k=2):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std()
    upper = mid + k * std
    lower = mid - k * std
    return upper, mid, lower

# OBV (On Balance Volume)
def _obv(close, volume):
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i-1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=close.index)

# Volume-Price Divergence Detection
def _detect_divergence(close, volume, window=10):
    """Detect if price and volume are diverging (bearish/bullish signal)."""
    recent_close = close.tail(window)
    recent_vol = volume.tail(window)
    price_trend = recent_close.iloc[-1] - recent_close.iloc[0]
    vol_trend = recent_vol.iloc[-1] - recent_vol.mean()

    if price_trend > 0 and vol_trend < 0:
        return "顶背离(价升量缩,看空信号)"
    elif price_trend < 0 and vol_trend > 0:
        return "底背离(价跌量增,看多信号)"
    return "无背离"
```

#### 4.2 Add to Indicator Return Value

```python
return {
    "macd": { ... },  # existing
    "rsi": { ... },   # existing
    "ma": { ... },    # existing
    "kdj": {
        "k": float(k.iloc[-1]),
        "d": float(d.iloc[-1]),
        "j": float(j.iloc[-1]),
        "signal": "超买" if j.iloc[-1] > 100 else "超卖" if j.iloc[-1] < 0 else "正常"
    },
    "boll": {
        "upper": float(upper.iloc[-1]),
        "mid": float(mid.iloc[-1]),
        "lower": float(lower.iloc[-1]),
        "position": "上轨附近" if close.iloc[-1] > upper.iloc[-1] * 0.98 else
                    "下轨附近" if close.iloc[-1] < lower.iloc[-1] * 1.02 else "中轨区间"
    },
    "volume_price": {
        "divergence": divergence_signal,
        "volume_ratio": vol_ratio,  # today vs 10-day avg
    }
}
```

#### 4.3 Frontend: Add KDJ and BOLL Charts to Stock Detail Page

Add toggleable indicator panels below the existing K-line chart:
- KDJ sub-chart (similar to MACD display)
- Bollinger Bands overlay on K-line chart
- Volume bar coloring (red for up-days, green for down-days)

#### 4.4 Integrate into LLM Agent Context

Add KDJ/BOLL/divergence signals to `format_data_context()`:

```python
kdj = indicators.get("kdj", {})
if kdj:
    lines.append(f"KDJ: K={kdj['k']:.2f}, D={kdj['d']:.2f}, J={kdj['j']:.2f}, 状态={kdj['signal']}")

boll = indicators.get("boll", {})
if boll:
    lines.append(f"布林带: 上轨={boll['upper']:.2f}, 中轨={boll['mid']:.2f}, 下轨={boll['lower']:.2f}, 位置={boll['position']}")

vp = indicators.get("volume_price", {})
if vp:
    lines.append(f"量价关系: {vp['divergence']}, 量比={vp['volume_ratio']:.2f}")
```

---

## Phase 5: Multi-Factor Scoring System

**Goal**: Build a structured scoring system that combines all data sources into a weighted composite score, independent of the LLM. The LLM agent then receives both the raw data AND the composite score.

**Impact**: HIGH | **Effort**: MEDIUM | **Tushare Points Required**: Depends on which factors are available

### Why This Matters

An LLM can hallucinate or misweight signals. A deterministic scoring system provides a reliable baseline. The LLM then serves as a "second opinion" that can adjust the score based on news/events the scoring system can't capture.

### Architecture

```
Raw Data Sources
├── Technical Score (30%)
│   ├── MACD signal direction (+/-)
│   ├── RSI zone (overbought/oversold/neutral)
│   ├── KDJ signal (+/-)
│   ├── MA alignment (bullish/bearish)
│   ├── BOLL position
│   └── Volume-price divergence
├── Valuation Score (20%)
│   ├── PE percentile (vs historical)
│   ├── PB percentile (vs historical)
│   └── Turnover rate trend
├── Market Environment Score (15%)
│   ├── Index trend (5d, 20d)
│   ├── Market breadth (if available)
│   └── Interest rate direction
├── Sentiment Score (25%)
│   ├── News sentiment (from Tavily + LLM)
│   └── News volume/heat
└── Money Flow Score (10%) — Phase 6
    ├── Northbound capital flow
    └── Main force net inflow
```

### Changes Required

#### 5.1 Create `backend/services/scoring_service.py`

```python
class StockScoringService:
    """Multi-factor scoring system for stock trend prediction."""

    @staticmethod
    def calculate_technical_score(indicators: dict) -> dict:
        """Score: -100 to +100 based on technical indicators."""
        score = 0
        signals = []

        # MACD (weight: 25%)
        macd = indicators.get("macd", {})
        if macd.get("hist", 0) > 0:
            score += 25
            signals.append("MACD柱状正值(+)")
        else:
            score -= 25
            signals.append("MACD柱状负值(-)")

        # RSI (weight: 20%)
        rsi6 = indicators.get("rsi", {}).get("rsi6", 50)
        if rsi6 < 30:
            score += 20  # oversold = buy signal
            signals.append(f"RSI超卖{rsi6:.0f}(+)")
        elif rsi6 > 70:
            score -= 20  # overbought = sell signal
            signals.append(f"RSI超买{rsi6:.0f}(-)")

        # KDJ (weight: 20%)
        kdj = indicators.get("kdj", {})
        j_val = kdj.get("j", 50)
        if j_val < 20:
            score += 20
            signals.append("KDJ超卖(+)")
        elif j_val > 80:
            score -= 20
            signals.append("KDJ超买(-)")

        # MA alignment (weight: 20%)
        ma = indicators.get("ma", {})
        if ma.get("ma5", 0) > ma.get("ma20", 0):
            score += 20
            signals.append("均线多头排列(+)")
        else:
            score -= 20
            signals.append("均线空头排列(-)")

        # Volume-price (weight: 15%)
        vp = indicators.get("volume_price", {})
        div = vp.get("divergence", "")
        if "底背离" in div:
            score += 15
            signals.append("底背离(+)")
        elif "顶背离" in div:
            score -= 15
            signals.append("顶背离(-)")

        return {"score": max(-100, min(100, score)), "signals": signals}

    @staticmethod
    def calculate_valuation_score(valuation: dict) -> dict:
        """Score based on PE/PB percentile and turnover."""
        # Implementation: compare current PE/PB to historical range
        ...

    @staticmethod
    def calculate_market_score(index_data: dict, shibor_data: dict) -> dict:
        """Score based on market environment."""
        ...

    @staticmethod
    def calculate_composite_score(
        technical: dict, valuation: dict, market: dict, sentiment: dict
    ) -> dict:
        """Weighted composite score."""
        weights = {
            "technical": 0.30,
            "valuation": 0.20,
            "market": 0.15,
            "sentiment": 0.25,
            "money_flow": 0.10,  # Phase 6
        }
        composite = (
            technical["score"] * weights["technical"]
            + valuation["score"] * weights["valuation"]
            + market["score"] * weights["market"]
            + sentiment["score"] * weights["sentiment"]
        )
        direction = "up" if composite > 15 else "down" if composite < -15 else "neutral"
        return {
            "composite_score": round(composite, 1),
            "direction": direction,
            "breakdown": {
                "technical": technical,
                "valuation": valuation,
                "market": market,
                "sentiment": sentiment,
            }
        }
```

#### 5.2 Modify `analyze_stock_trend()` to Use Dual-System

```python
def analyze_stock_trend(symbol: str, name: str) -> Dict[str, Any]:
    # Step 1: Calculate quantitative score
    quant_score = StockScoringService.calculate_composite_score(...)

    # Step 2: Run LLM agent (with all data context)
    llm_prediction = run_llm_agent(symbol, name, data_context)

    # Step 3: Combine — quant score as baseline, LLM can adjust +/-20
    final_direction = reconcile(quant_score, llm_prediction)
    final_confidence = calculate_confidence(quant_score, llm_prediction)

    return {
        "symbol": symbol,
        "name": name,
        "trend_direction": final_direction,
        "confidence": final_confidence,
        "summary": llm_prediction["summary"],
        "quant_score": quant_score,  # NEW: include breakdown
    }
```

#### 5.3 Update Database Schema

```sql
ALTER TABLE predictions ADD COLUMN quant_score REAL;
ALTER TABLE predictions ADD COLUMN score_breakdown TEXT;  -- JSON string
```

#### 5.4 Frontend: Show Score Breakdown

Add a "Score Breakdown" panel to the prediction display:
- Radar/spider chart showing each factor's contribution
- Color-coded bar for composite score (-100 red to +100 green)
- Individual factor scores with signal explanations

---

## Phase 6: Money Flow Data (Requires 2000+ Tushare Points)

**Goal**: Add northbound capital (北向资金) and individual stock money flow data. Research shows this improves A-share short-term prediction accuracy by 15-20%.

**Impact**: VERY HIGH | **Effort**: MEDIUM | **Tushare Points Required**: 2000+

### Why This Matters

Empirical studies show:
- Days with strong northbound inflows have 0.7-1.2% higher probability of subsequent price rise
- Technical patterns alone yield 0.4-0.6% edge
- Combined money flow + technicals improves accuracy by ~15-20%
- Northbound capital is considered "smart money" in A-share markets

### Prerequisite: Tushare Points

You need **2000+ points** to access `moneyflow` and `moneyflow_hsgt`. Ways to get points:
1. Complete profile: 120 points (baseline)
2. Refer users: +50 each
3. Write articles about tushare: 100-1000
4. Contribute code: 100-500
5. Community contributions: 50-500

### Changes Required

#### 6.1 Add Money Flow Functions to `akshare_service.py`

```python
@staticmethod
def get_moneyflow_hsgt(days: int = 30) -> dict:
    """Get northbound capital flow (沪深港通资金流向).
    Requires 2000+ tushare points.
    """
    try:
        pro = ts.pro_api()
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        df = pro.moneyflow_hsgt(
            start_date=start_date,
            end_date=end_date
        )
        # Fields: trade_date, ggt_ss (港股通上海), ggt_sz (港股通深圳),
        #         hgt (沪股通), sgt (深股通), north_money (北向资金), south_money

        if df is None or df.empty:
            return {"error": "No HSGT data (check tushare points >= 2000)"}

        df = df.sort_values("trade_date").tail(days)

        # Calculate trends
        north_5d = df.tail(5)["north_money"].sum()
        north_20d = df.tail(20)["north_money"].sum()

        return {
            "data": df.to_dict("records"),
            "latest": df.iloc[-1].to_dict(),
            "north_5d_total": north_5d,      # 5-day net flow
            "north_20d_total": north_20d,     # 20-day net flow
            "trend": "净流入" if north_5d > 0 else "净流出",
        }
    except Exception as e:
        return {"error": str(e)}


@staticmethod
def get_moneyflow(symbol: str, days: int = 20) -> dict:
    """Get individual stock money flow (个股资金流向).
    Requires 2000+ tushare points.
    """
    try:
        ts_code = _symbol_to_ts_code(symbol)
        pro = ts.pro_api()
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

        df = pro.moneyflow(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        # Fields: buy_elg_vol (特大单买入), sell_elg_vol, buy_lg_vol (大单买入),
        #         sell_lg_vol, buy_md_vol, sell_md_vol, buy_sm_vol, sell_sm_vol,
        #         net_mf_vol (净流入量), net_mf_amount (净流入额)

        if df is None or df.empty:
            return {"symbol": symbol, "error": "No moneyflow data"}

        df = df.sort_values("trade_date").tail(days)

        # Main force = extra-large + large orders
        df["main_net"] = (df["buy_elg_vol"] - df["sell_elg_vol"]) + (df["buy_lg_vol"] - df["sell_lg_vol"])

        return {
            "symbol": symbol,
            "data": df.to_dict("records"),
            "main_net_5d": df.tail(5)["main_net"].sum(),
            "main_net_10d": df.tail(10)["main_net"].sum(),
            "trend": "主力净流入" if df.tail(5)["main_net"].sum() > 0 else "主力净流出",
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}
```

#### 6.2 Add API Endpoints

```python
@router.get("/api/market/northbound")
async def get_northbound_flow(days: int = Query(default=30, ge=1, le=365)):
    return AkshareService.get_moneyflow_hsgt(days)

@router.get("/api/stock/{symbol}/moneyflow")
async def get_stock_moneyflow(symbol: str, days: int = Query(default=20, ge=1, le=180)):
    return AkshareService.get_moneyflow(symbol, days)
```

#### 6.3 Integrate into Scoring System

Add money flow score to `scoring_service.py`:

```python
@staticmethod
def calculate_money_flow_score(stock_flow: dict, northbound_flow: dict) -> dict:
    score = 0
    signals = []

    # Northbound capital trend (weight: 50%)
    if northbound_flow.get("trend") == "净流入":
        score += 50
        signals.append(f"北向资金净流入(+)")
    else:
        score -= 50
        signals.append(f"北向资金净流出(-)")

    # Individual stock main force (weight: 50%)
    if stock_flow.get("trend") == "主力净流入":
        score += 50
        signals.append("主力资金净流入(+)")
    else:
        score -= 50
        signals.append("主力资金净流出(-)")

    return {"score": max(-100, min(100, score)), "signals": signals}
```

Update composite weights to include money_flow at 10% (reduce others proportionally).

#### 6.4 Frontend: Money Flow Dashboard

Add to stock detail page:
- Northbound capital flow chart (bar chart, green for inflow, red for outflow)
- Individual stock money flow breakdown (pie chart: extra-large/large/medium/small orders)
- "Smart Money" indicator badge on stock cards

---

## Phase 7: Financial Fundamentals (Requires 2000+ Tushare Points)

**Goal**: Add earnings data, financial indicators (ROE, growth rates), and earnings forecast/express data. This shifts prediction capability from pure short-term to medium-term (1-3 months).

**Impact**: MEDIUM | **Effort**: MEDIUM | **Tushare Points Required**: 2000-5000

### Why This Matters

Financial fundamentals are the strongest medium-term predictors. Earnings surprise events can trigger 10-20% price moves. ROE trend is the single best long-term stock selection metric (Warren Buffett's primary criterion).

### Changes Required

#### 7.1 Add Financial Data Functions to `akshare_service.py`

```python
@staticmethod
def get_fina_indicator(symbol: str, periods: int = 4) -> dict:
    """Get key financial indicators for last N quarters."""
    try:
        ts_code = _symbol_to_ts_code(symbol)
        pro = ts.pro_api()

        df = pro.fina_indicator(
            ts_code=ts_code,
            fields='ts_code,ann_date,end_date,roe,roe_dt,grossprofit_margin,'
                   'netprofit_yoy,or_yoy,debt_to_assets,current_ratio'
        )

        if df is None or df.empty:
            return {"symbol": symbol, "error": "No financial data"}

        df = df.sort_values("end_date", ascending=False).head(periods)

        return {
            "symbol": symbol,
            "data": df.to_dict("records"),
            "latest": df.iloc[0].to_dict(),
            "roe_trend": "improving" if len(df) >= 2 and df.iloc[0]["roe"] > df.iloc[1]["roe"] else "declining",
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


@staticmethod
def get_earnings_forecast(symbol: str) -> dict:
    """Get earnings forecast/express (业绩预告/快报) for early signals."""
    try:
        ts_code = _symbol_to_ts_code(symbol)
        pro = ts.pro_api()

        df = pro.forecast(ts_code=ts_code)
        if df is not None and not df.empty:
            latest = df.sort_values("ann_date", ascending=False).iloc[0]
            return {
                "symbol": symbol,
                "type": latest.get("type", ""),  # 预增/预减/扭亏/首亏/续盈/续亏/略增/略减
                "net_profit_min": latest.get("net_profit_min", None),
                "net_profit_max": latest.get("net_profit_max", None),
                "summary": latest.get("summary", ""),
            }
        return {"symbol": symbol, "error": "No forecast data"}
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}
```

#### 7.2 Integrate into LLM Agent Context

```python
# Financial context
if fina_data and "error" not in fina_data:
    latest = fina_data["latest"]
    lines.append(f"ROE: {latest.get('roe', 'N/A')}%, 趋势: {fina_data['roe_trend']}")
    lines.append(f"净利润同比: {latest.get('netprofit_yoy', 'N/A')}%")
    lines.append(f"毛利率: {latest.get('grossprofit_margin', 'N/A')}%")
    lines.append(f"资产负债率: {latest.get('debt_to_assets', 'N/A')}%")

if forecast_data and "error" not in forecast_data:
    lines.append(f"业绩预告: {forecast_data['type']} - {forecast_data['summary'][:100]}")
```

#### 7.3 Frontend: Financials Tab

Add a "Fundamentals" tab to the stock detail page:
- Quarterly ROE chart
- Revenue and profit growth bars
- Key ratios table (ROE, debt ratio, gross margin, current ratio)
- Earnings forecast badge (if available)

---

## Implementation Priority & Timeline Suggestion

| Phase | Title | Priority | Dependencies | Key Benefit |
|-------|-------|----------|--------------|-------------|
| **1** | Enrich LLM with Technical Data | P0 | None | Biggest single improvement — zero cost |
| **2** | Daily Valuation Metrics | P0 | None | PE/turnover are top predictive features |
| **3** | Market Context | P1 | None | Market correlation is ~60-70% of stock movement |
| **4** | Enhanced Technical Indicators | P1 | None | KDJ is most-watched A-share indicator |
| **5** | Multi-Factor Scoring | P1 | Phases 1-4 | Deterministic baseline reduces LLM hallucination |
| **6** | Money Flow Data | P2 | 2000+ tushare points | Strongest short-term predictor, but gated |
| **7** | Financial Fundamentals | P2 | 2000+ tushare points | Medium-term prediction capability |

### Suggested Day-by-Day Schedule

- **Day 1**: Phase 1 (feed existing data to LLM — fast win)
- **Day 2**: Phase 2 (add daily_basic valuation data)
- **Day 3**: Phase 3 (add index + SHIBOR market context)
- **Day 4**: Phase 4 (add KDJ, BOLL, volume-price indicators)
- **Day 5**: Phase 5 (build multi-factor scoring system)
- **Day 6**: Phase 6 (money flow — if tushare points allow)
- **Day 7**: Phase 7 (financial fundamentals — if tushare points allow)

---

## Architecture After All Phases

```
┌─────────────────────────────────────────────────┐
│                 Frontend (Next.js)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ K-line   │ │ Score    │ │ Money Flow       │ │
│  │ Chart    │ │ Dashboard│ │ Chart            │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└───────────────────┬─────────────────────────────┘
                    │ API
┌───────────────────┴─────────────────────────────┐
│              Backend (FastAPI)                    │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │         Multi-Factor Scoring Engine          │ │
│  │  Technical(30%) + Valuation(20%) + Market    │ │
│  │  (15%) + Sentiment(25%) + MoneyFlow(10%)    │ │
│  └─────────────────────┬───────────────────────┘ │
│                        │                         │
│  ┌─────────────┐ ┌─────┴──────┐ ┌─────────────┐ │
│  │ Tushare     │ │ DeepAgent  │ │ Tavily      │ │
│  │ Data Layer  │ │ (MiniMax)  │ │ Search      │ │
│  │             │ │            │ │             │ │
│  │ - daily     │ │ Receives:  │ │ - News      │ │
│  │ - daily_bsc │ │ - Quant    │ │ - Macro     │ │
│  │ - index     │ │   Score    │ │ - Sentiment │ │
│  │ - moneyflow │ │ - Raw Data │ │             │ │
│  │ - fina_ind  │ │ - News     │ │             │ │
│  │ - shibor    │ │            │ │             │ │
│  └─────────────┘ └────────────┘ └─────────────┘ │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │           SQLite Database                    │ │
│  │  predictions + scores + watchlist            │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## Appendix A: Tushare API Quick Reference

| API | Function | Points | Phase |
|-----|----------|--------|-------|
| `daily` | Daily OHLCV | 120 | Already used |
| `daily_basic` | PE/PB/turnover/mktcap | 120 | Phase 2 |
| `index_daily` | Index daily data | 120 | Phase 3 |
| `shibor` | Interest rates | 120 | Phase 3 |
| `moneyflow_hsgt` | Northbound capital | 2000 | Phase 6 |
| `moneyflow` | Stock money flow | 2000 | Phase 6 |
| `fina_indicator` | ROE/margins/growth | 2000 | Phase 7 |
| `forecast` | Earnings forecast | 2000 | Phase 7 |
| `income` | Income statement | 2000 | Phase 7 |
| `margin_detail` | Margin trading | 2000 | Future |
| `stk_holdernumber` | Shareholder count | 600 | Future |
| `top10_holders` | Major shareholders | 2000 | Future |

## Appendix B: Risk Notes

1. **Tushare rate limits**: 120-point accounts are limited to basic frequency. Add retry logic with exponential backoff for all Tushare calls.
2. **Data freshness**: daily_basic and moneyflow are typically available after market close (~16:00 CST). Schedule data fetching accordingly.
3. **Factor decay**: Research shows A-share factors erode once widely known. The scoring weights should be periodically reviewed and rebalanced.
4. **LLM limitations**: MiniMax M2.7 may not deeply understand financial data. Consider upgrading to a stronger model (e.g., DeepSeek-V3, Qwen-2.5) for the analysis agent if results are unsatisfactory.
5. **Backtesting**: Before trusting the scoring system, implement historical backtesting (compare predictions vs actual outcomes) to validate the factor weights. This is a good Phase 5.5 addition.
