-- remote_data/store/schema.sql
-- All tables for the local SQLite store. Applied by local_db.init().
-- Idempotent: every CREATE uses IF NOT EXISTS.

-- =====================================================================
-- Business tables (one per data_type). Each carries `pushed_at` as the
-- push-retry cursor and `failed_at` to mark dead-lettered records.
-- =====================================================================

CREATE TABLE IF NOT EXISTS etf_quote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,                       -- ISO8601 UTC, e.g. 2026-06-29T13:30:00Z
    price REAL,
    pre_market_price REAL,
    post_market_price REAL,
    volume INTEGER,
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(symbol, ts)
);

CREATE TABLE IF NOT EXISTS etf_fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of TEXT NOT NULL,                    -- ISO8601 UTC
    pe REAL,
    pb REAL,
    dividend_yield REAL,
    dividend_rate REAL,
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(symbol, as_of)
);

CREATE TABLE IF NOT EXISTS etf_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,               -- ISO8601 UTC date
    payload_json TEXT NOT NULL,             -- JSON array of {symbol, name, weight_pct}
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(symbol, as_of_date)
);

CREATE TABLE IF NOT EXISTS etf_sector_weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    payload_json TEXT NOT NULL,             -- JSON array of {sector, weight_pct}
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(symbol, as_of_date)
);

CREATE TABLE IF NOT EXISTS etf_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    ytd_return REAL,
    return_1y REAL,
    return_3y REAL,
    return_5y REAL,
    return_10y REAL,
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(symbol, as_of_date)
);

CREATE TABLE IF NOT EXISTS etf_equity_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    payload_json TEXT NOT NULL,             -- JSON array with per-holding PE/PB/PS
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(symbol, as_of_date)
);

CREATE TABLE IF NOT EXISTS etf_esg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    total_esg REAL,
    environment REAL,
    social REAL,
    governance REAL,
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(symbol, as_of_date)
);

CREATE TABLE IF NOT EXISTS etf_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,                      -- PK surrogate from upstream
    symbol TEXT NOT NULL,
    title TEXT,
    publisher TEXT,
    published_at TEXT NOT NULL,             -- ISO8601 UTC
    summary TEXT,
    pushed_at TEXT,
    failed_at TEXT,
    UNIQUE(url)
);

-- =====================================================================
-- Audit / dead-letter tables
-- =====================================================================

CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,                       -- ISO8601 UTC
    data_type TEXT NOT NULL,
    symbol TEXT,                            -- nullable for whole-job failures
    status TEXT NOT NULL,                   -- 'ok' | 'error'
    error TEXT,
    row_count INTEGER
);

CREATE TABLE IF NOT EXISTS push_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_at TEXT NOT NULL,
    data_type TEXT NOT NULL,
    batch_id TEXT,
    http_status INTEGER,
    retry_count INTEGER,
    error TEXT,
    row_count INTEGER
);

CREATE TABLE IF NOT EXISTS etf_dead_letter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dead_lettered_at TEXT NOT NULL,
    data_type TEXT NOT NULL,
    source_id INTEGER,                      -- FK-ish to the business table row
    batch_id TEXT,
    payload_json TEXT NOT NULL,
    response_status INTEGER,
    response_body TEXT
);

-- Indexes that the push loop + prune use.
CREATE INDEX IF NOT EXISTS idx_etf_quote_pushed_at ON etf_quote(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_quote_ts ON etf_quote(ts);
CREATE INDEX IF NOT EXISTS idx_etf_fundamentals_pushed_at ON etf_fundamentals(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_holdings_pushed_at ON etf_holdings(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_sector_weights_pushed_at ON etf_sector_weights(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_performance_pushed_at ON etf_performance(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_equity_holdings_pushed_at ON etf_equity_holdings(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_esg_pushed_at ON etf_esg(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_news_pushed_at ON etf_news(pushed_at);
CREATE INDEX IF NOT EXISTS idx_etf_news_published_at ON etf_news(published_at);
CREATE INDEX IF NOT EXISTS idx_push_log_sent_at ON push_log(sent_at);