"""remote_data.fetcher: yahooquery-backed ETF data fetchers.

One module per data_type, each exposing a `fetch_<x>(symbols, ...)` function
returning normalized record dicts. Downstream store / pusher layers MUST NOT
import yahooquery directly.
"""

from remote_data.fetcher import (  # noqa: F401
    etf_equity_holdings,
    etf_esg,
    etf_fundamentals,
    etf_holdings,
    etf_news,
    etf_performance,
    etf_quote,
    etf_sector_weightings,
)
from remote_data.fetcher.etf_equity_holdings import fetch_equity_holdings
from remote_data.fetcher.etf_esg import fetch_esg
from remote_data.fetcher.etf_fundamentals import fetch_fundamentals
from remote_data.fetcher.etf_holdings import fetch_holdings
from remote_data.fetcher.etf_news import fetch_news
from remote_data.fetcher.etf_performance import fetch_performance
from remote_data.fetcher.etf_quote import fetch_quotes
from remote_data.fetcher.etf_sector_weightings import fetch_sector_weightings