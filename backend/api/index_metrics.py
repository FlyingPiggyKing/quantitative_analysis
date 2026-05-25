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

# SW Level-2 sub-industries for each Level-1 industry
# Mapping parent Level-1 ts_code to list of sub-industries
SW_SUB_INDUSTRY_MAP = {
    "801010.SI": [  # 农林牧渔
        {"name": "种植业", "ts_code": "801011.SI"},
        {"name": "林业", "ts_code": "801013.SI"},
        {"name": "渔业", "ts_code": "801012.SI"},
        {"name": "畜牧业", "ts_code": "801014.SI"},
        {"name": "农业综合", "ts_code": "801016.SI"},
        {"name": "农产品加工", "ts_code": "801015.SI"},
    ],
    "801020.SI": [  # 采掘
        {"name": "煤炭开采", "ts_code": "801021.SI"},
        {"name": "石油开采", "ts_code": "801023.SI"},
        {"name": "金属采选", "ts_code": "801024.SI"},
        {"name": "非金属采选", "ts_code": "801025.SI"},
    ],
    "801030.SI": [  # 化工
        {"name": "化学制品", "ts_code": "801032.SI"},
        {"name": "化学原料", "ts_code": "801031.SI"},
        {"name": "化学纤维", "ts_code": "801033.SI"},
        {"name": "石油化工", "ts_code": "801034.SI"},
    ],
    "801040.SI": [  # 钢铁
        {"name": "钢铁", "ts_code": "801041.SI"},
    ],
    "801050.SI": [  # 有色金属
        {"name": "金属非金属", "ts_code": "801051.SI"},
        {"name": "稀有金属", "ts_code": "801056.SI"},
    ],
    "801080.SI": [  # 电子
        {"name": "半导体", "ts_code": "801081.SI"},
        {"name": "元件", "ts_code": "801082.SI"},
        {"name": "光学光电子", "ts_code": "801083.SI"},
        {"name": "其他电子", "ts_code": "801084.SI"},
    ],
    "801110.SI": [  # 汽车
        {"name": "汽车整车", "ts_code": "801111.SI"},
        {"name": "汽车零部件", "ts_code": "801112.SI"},
        {"name": "汽车服务", "ts_code": "801113.SI"},
    ],
    "801120.SI": [  # 家用电器
        {"name": "白色家电", "ts_code": "801121.SI"},
        {"name": "黑色家电", "ts_code": "801122.SI"},
        {"name": "小家电", "ts_code": "801123.SI"},
    ],
    "801130.SI": [  # 食品饮料
        {"name": "食品加工", "ts_code": "801131.SI"},
        {"name": "饮料制造", "ts_code": "801132.SI"},
        {"name": "白酒", "ts_code": "801133.SI"},
    ],
    "801140.SI": [  # 纺织服装
        {"name": "纺织制造", "ts_code": "801141.SI"},
        {"name": "服装家纺", "ts_code": "801142.SI"},
        {"name": "饰品", "ts_code": "801143.SI"},
    ],
    "801150.SI": [  # 轻工制造
        {"name": "造纸", "ts_code": "801151.SI"},
        {"name": "包装印刷", "ts_code": "801152.SI"},
        {"name": "家用轻工", "ts_code": "801153.SI"},
    ],
    "801160.SI": [  # 医药生物
        {"name": "化学制药", "ts_code": "801161.SI"},
        {"name": "中药", "ts_code": "801162.SI"},
        {"name": "生物制品", "ts_code": "801163.SI"},
        {"name": "医疗器械", "ts_code": "801164.SI"},
        {"name": "医药商业", "ts_code": "801165.SI"},
    ],
    "801170.SI": [  # 公用事业
        {"name": "电力", "ts_code": "801171.SI"},
        {"name": "燃气", "ts_code": "801172.SI"},
        {"name": "水务", "ts_code": "801173.SI"},
    ],
    "801180.SI": [  # 交通运输
        {"name": "港口航运", "ts_code": "801181.SI"},
        {"name": "公路铁路", "ts_code": "801182.SI"},
        {"name": "航空机场", "ts_code": "801183.SI"},
        {"name": "物流", "ts_code": "801184.SI"},
    ],
    "801190.SI": [  # 房地产
        {"name": "房地产开发", "ts_code": "801191.SI"},
        {"name": "房地产服务", "ts_code": "801192.SI"},
    ],
    "801200.SI": [  # 商业贸易
        {"name": "零售", "ts_code": "801201.SI"},
        {"name": "批发", "ts_code": "801202.SI"},
        {"name": "商业物业经营", "ts_code": "801203.SI"},
    ],
    "801210.SI": [  # 休闲服务
        {"name": "旅游", "ts_code": "801211.SI"},
        {"name": "酒店餐饮", "ts_code": "801212.SI"},
        {"name": "休闲服务", "ts_code": "801213.SI"},
    ],
    "801220.SI": [  # 银行
        {"name": "银行", "ts_code": "801221.SI"},
    ],
    "801230.SI": [  # 非银金融
        {"name": "证券", "ts_code": "801231.SI"},
        {"name": "保险", "ts_code": "801232.SI"},
        {"name": "多元金融", "ts_code": "801233.SI"},
    ],
    "801710.SI": [  # 建筑材料
        {"name": "水泥制造", "ts_code": "801711.SI"},
        {"name": "玻璃制造", "ts_code": "801712.SI"},
        {"name": "其他建材", "ts_code": "801713.SI"},
    ],
    "801720.SI": [  # 建筑装饰
        {"name": "房屋建设", "ts_code": "801721.SI"},
        {"name": "装修装饰", "ts_code": "801722.SI"},
        {"name": "园林工程", "ts_code": "801723.SI"},
        {"name": "基础建设", "ts_code": "801724.SI"},
    ],
    "801730.SI": [  # 电气设备
        {"name": "电机", "ts_code": "801731.SI"},
        {"name": "电气自动化设备", "ts_code": "801732.SI"},
        {"name": "电源设备", "ts_code": "801733.SI"},
        {"name": "高低压设备", "ts_code": "801734.SI"},
    ],
    "801740.SI": [  # 国防军工
        {"name": "航天装备", "ts_code": "801741.SI"},
        {"name": "航空装备", "ts_code": "801742.SI"},
        {"name": "地面兵装", "ts_code": "801743.SI"},
        {"name": "船舶制造", "ts_code": "801744.SI"},
    ],
    "801750.SI": [  # 计算机
        {"name": "计算机设备", "ts_code": "801751.SI"},
        {"name": "软件开发", "ts_code": "801752.SI"},
        {"name": "IT服务", "ts_code": "801753.SI"},
    ],
    "801760.SI": [  # 传媒
        {"name": "广告营销", "ts_code": "801761.SI"},
        {"name": "影视院线", "ts_code": "801762.SI"},
        {"name": "游戏", "ts_code": "801763.SI"},
        {"name": "出版", "ts_code": "801764.SI"},
    ],
    "801770.SI": [  # 通信
        {"name": "通信设备", "ts_code": "801771.SI"},
        {"name": "通信服务", "ts_code": "801772.SI"},
        {"name": "通信运营", "ts_code": "801773.SI"},
    ],
    "801780.SI": [  # 机械设备
        {"name": "通用设备", "ts_code": "801781.SI"},
        {"name": "专用设备", "ts_code": "801782.SI"},
        {"name": "仪器仪表", "ts_code": "801783.SI"},
    ],
    "801790.SI": [  # 综合
        {"name": "综合", "ts_code": "801791.SI"},
    ],
}


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

# Add sub-industries to lookup (they use same SW API as Level-1)
for sub_industries in SW_SUB_INDUSTRY_MAP.values():
    for sub in sub_industries:
        ALL_INDEX_LOOKUP[sub["ts_code"]] = {"name": sub["name"], "ts_code": sub["ts_code"], "source": "sw"}

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


@router.get("/industry/subindustry")
async def get_subindustry_list(
    ts_code: str = Query(..., description="Level-1 industry ts_code, e.g., 801010.SI")
):
    """Get list of sub-industries for a given Level-1 SW industry."""
    sub_industries = SW_SUB_INDUSTRY_MAP.get(ts_code, [])
    return {"sub_industries": sub_industries}


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
