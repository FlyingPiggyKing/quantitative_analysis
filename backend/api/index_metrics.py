"""Index metrics API routes."""
from datetime import datetime, timedelta
from functools import lru_cache
import os
import numpy as np
import tushare as ts
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/index", tags=["index"])

# Common SW Level-1 industries (申万一级行业) - with source for API lookup
# Reference: 申万行业分类代码
SW_INDUSTRY_LIST = [
    {"name": "农林牧渔", "ts_code": "801010.SI", "source": "sw"},
    {"name": "采掘", "ts_code": "801020.SI", "source": "sw"},
    {"name": "化工", "ts_code": "801030.SI", "source": "sw"},
    {"name": "钢铁", "ts_code": "801040.SI", "source": "sw"},
    {"name": "有色金属", "ts_code": "801050.SI", "source": "sw"},
    {"name": "电子", "ts_code": "801080.SI", "source": "sw"},
    {"name": "汽车", "ts_code": "801110.SI", "source": "sw"},
    {"name": "家用电器", "ts_code": "801120.SI", "source": "sw"},
    {"name": "食品饮料", "ts_code": "801130.SI", "source": "sw"},
    {"name": "纺织服装", "ts_code": "801140.SI", "source": "sw"},
    {"name": "轻工制造", "ts_code": "801150.SI", "source": "sw"},
    {"name": "医药生物", "ts_code": "801160.SI", "source": "sw"},
    {"name": "公用事业", "ts_code": "801170.SI", "source": "sw"},
    {"name": "交通运输", "ts_code": "801180.SI", "source": "sw"},
    {"name": "房地产", "ts_code": "801190.SI", "source": "sw"},
    {"name": "商业贸易", "ts_code": "801200.SI", "source": "sw"},
    {"name": "休闲服务", "ts_code": "801210.SI", "source": "sw"},
    {"name": "银行", "ts_code": "801220.SI", "source": "sw"},
    {"name": "非银金融", "ts_code": "801230.SI", "source": "sw"},
    {"name": "建筑材料", "ts_code": "801710.SI", "source": "sw"},
    {"name": "建筑装饰", "ts_code": "801720.SI", "source": "sw"},
    {"name": "电气设备", "ts_code": "801730.SI", "source": "sw"},
    {"name": "国防军工", "ts_code": "801740.SI", "source": "sw"},
    {"name": "计算机", "ts_code": "801750.SI", "source": "sw"},
    {"name": "传媒", "ts_code": "801760.SI", "source": "sw"},
    {"name": "通信", "ts_code": "801770.SI", "source": "sw"},
    {"name": "机械设备", "ts_code": "801780.SI", "source": "sw"},
    {"name": "综合", "ts_code": "801790.SI", "source": "sw"},
]

# SW Industry Indices list in display order
# Using 4 SW industry indices to represent tech sector
SW_INDEX_LIST = [
    {"name": "半导体", "ts_code": "801081.SI", "source": "sw"},
    {"name": "航天装备Ⅱ", "ts_code": "801741.SI", "source": "sw"},
    {"name": "模拟芯片设计", "ts_code": "850815.SI", "source": "sw"},
    {"name": "横向通用软件", "ts_code": "851042.SI", "source": "sw"},
]

# A-share broad indices (using index_dailybasic)
BROAD_INDEX_LIST = [
    {"name": "创业板指", "ts_code": "399006.SZ", "launch_date": "20100601", "source": "dailybasic"},
    {"name": "上证指数", "ts_code": "000001.SH", "launch_date": "19910715", "source": "dailybasic"},
    {"name": "深证成指", "ts_code": "399001.SZ", "launch_date": "19950201", "source": "dailybasic"},
    {"name": "沪深300", "ts_code": "000300.SH", "launch_date": "20050408", "source": "dailybasic"},
    {"name": "中证500", "ts_code": "000905.SH", "launch_date": "20070115", "source": "dailybasic"},
]

# Combined index list
INDEX_LIST = SW_INDEX_LIST + BROAD_INDEX_LIST

# Combined lookup: all indices and industries
ALL_INDEX_LOOKUP = {idx["ts_code"]: idx for idx in INDEX_LIST}
ALL_INDEX_LOOKUP.update({ind["ts_code"]: ind for ind in SW_INDUSTRY_LIST})

# Cache key format: index_metrics:{ts_code}:{years}:{date}
_cache_store = {}


def _get_cache_key(ts_code: str, years: int) -> str:
    today = datetime.now().strftime("%Y%m%d")
    return f"index_metrics:{ts_code}:{years}:{today}"


def _is_cache_valid(cache_key: str) -> bool:
    return cache_key in _cache_store


def _get_cached(cache_key: str):
    return _cache_store.get(cache_key)


def _set_cached(cache_key: str, data):
    _cache_store[cache_key] = data


@lru_cache(maxsize=1)
def _get_tushare_token() -> str:
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        raise ValueError("TUSHARE_TOKEN not set in environment")
    return token


def get_sw_pe_history(ts_code: str, years: int = 10) -> list:
    """Fetch PE history for SW industry index using sw_daily API."""
    pro = ts.pro_api(_get_tushare_token())

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

    df = pro.sw_daily(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        fields="trade_date,pe"
    )

    # Filter valid PE values (not null, not negative)
    df = df[df["pe"].notna() & (df["pe"] > 0)]
    df = df.sort_values("trade_date")

    return df.to_dict("records")


def get_broad_index_pe_history(ts_code: str, years: int = 10, launch_date: str = "19000101") -> list:
    """Fetch PE-TTM history for broad index using index_dailybasic API."""
    pro = ts.pro_api(_get_tushare_token())

    end_date = datetime.now().strftime("%Y%m%d")
    calculated_start = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

    # Use the later of calculated_start or launch_date
    start_date = max(calculated_start, launch_date)

    df = pro.index_dailybasic(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        fields="trade_date,pe_ttm"
    )

    # Filter valid PE-TTM values (not null, not negative)
    df = df[df["pe_ttm"].notna() & (df["pe_ttm"] > 0)]
    df = df.sort_values("trade_date")

    return df.to_dict("records")


def calculate_pe_percentile(pe_history: list, pe_field: str = "pe_ttm") -> dict:
    """Calculate opportunity/danger values and current percentile from PE history."""
    if not pe_history:
        return {
            "current_pe": None,
            "opportunity": None,
            "danger": None,
            "current_percentile": None,
            "historical_high": None,
            "historical_low": None,
        }

    pe_values = np.array([item[pe_field] for item in pe_history])
    sorted_pe = np.sort(pe_values)
    current_pe = pe_values[-1]  # Most recent

    opportunity = float(np.percentile(sorted_pe, 30))
    danger = float(np.percentile(sorted_pe, 70))

    # Calculate percentile: what percentage of historical values are below current
    current_idx = np.searchsorted(sorted_pe, current_pe)
    current_percentile = float(current_idx / len(sorted_pe) * 100)

    return {
        "current_pe": round(float(current_pe), 2),
        "opportunity": round(opportunity, 2),
        "danger": round(danger, 2),
        "current_percentile": round(current_percentile, 2),
        "historical_high": round(float(sorted_pe.max()), 2),
        "historical_low": round(float(sorted_pe.min()), 2),
    }


@router.get("/metrics")
async def get_index_metrics(
    ts_code: str = Query(..., description="Index ts_code, e.g., 801081.SI or 000688.SH"),
    years: int = Query(default=10, ge=5, le=10, description="Time range in years (5 or 10)")
):
    """Get PE metrics for an index including opportunity/danger values and current percentile.

    Supports both SW industry indices (sw_daily) and broad indices (index_dailybasic).
    """
    cache_key = _get_cache_key(ts_code, years)

    # Check cache first
    if _is_cache_valid(cache_key):
        return _get_cached(cache_key)

    # Find the index info
    index_info = ALL_INDEX_LOOKUP.get(ts_code)

    if not index_info:
        return {"error": f"Index {ts_code} not found", "ts_code": ts_code}

    source = index_info.get("source", "dailybasic")

    # Fetch data based on source
    if source == "sw":
        pe_history = get_sw_pe_history(ts_code, years)
        result = calculate_pe_percentile(pe_history, pe_field="pe")
    else:
        launch_date = index_info.get("launch_date", "19000101")
        pe_history = get_broad_index_pe_history(ts_code, years, launch_date)
        result = calculate_pe_percentile(pe_history, pe_field="pe_ttm")

    result["ts_code"] = ts_code
    result["name"] = index_info["name"]
    result["years"] = years

    # Cache the result
    _set_cached(cache_key, result)

    return result


@router.get("/list")
async def get_index_list():
    """Get list of available indices with their basic info."""
    return {"indices": INDEX_LIST}


@router.get("/industry/list")
async def get_industry_list():
    """Get list of SW industries for selection."""
    return {"industries": SW_INDUSTRY_LIST}


@router.get("/history")
async def get_index_pe_history(
    ts_code: str = Query(..., description="Index ts_code, e.g., 801081.SI or 399006.SZ"),
    years: int = Query(default=10, ge=5, le=10, description="Time range in years (5 or 10)")
):
    """Get historical PE data for an index, used for charting.

    Returns time series data with trade_date and pe values.
    """
    # Find the index info
    index_info = ALL_INDEX_LOOKUP.get(ts_code)

    if not index_info:
        return {"error": f"Index {ts_code} not found", "ts_code": ts_code, "data": []}

    source = index_info.get("source", "dailybasic")

    # Fetch data based on source
    if source == "sw":
        pe_history = get_sw_pe_history(ts_code, years)
        # Transform to response format
        data = [
            {"trade_date": item["trade_date"], "pe": item["pe"]}
            for item in pe_history
            if item["pe"] > 0
        ]
    else:
        launch_date = index_info.get("launch_date", "19000101")
        pe_history = get_broad_index_pe_history(ts_code, years, launch_date)
        # Transform to response format
        data = [
            {"trade_date": item["trade_date"], "pe": item["pe_ttm"]}
            for item in pe_history
            if item["pe_ttm"] > 0
        ]

    return {
        "ts_code": ts_code,
        "name": index_info["name"],
        "years": years,
        "data": data,
    }
