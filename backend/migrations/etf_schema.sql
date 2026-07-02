-- ETF remote ingest schema.
-- Executed idempotently on every backend startup.
-- All tables use CREATE TABLE IF NOT EXISTS so the file is safe to re-run.

-- Time-series price points. PK = (symbol, ts). UPSERT overwrites on conflict.
CREATE TABLE IF NOT EXISTS etf_quote (
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    price REAL,
    pre_market_price REAL,
    post_market_price REAL,
    volume INTEGER,
    PRIMARY KEY (symbol, ts)
);

-- Daily fundamentals snapshot. PK = (symbol, as_of). UPSERT overwrites.
CREATE TABLE IF NOT EXISTS etf_fundamentals (
    symbol TEXT NOT NULL,
    as_of TEXT NOT NULL,
    pe REAL,
    pb REAL,
    dividend_yield REAL,
    dividend_rate REAL,
    PRIMARY KEY (symbol, as_of)
);

-- Top-N holdings stored as raw JSON in payload_json. PK = (symbol, as_of_date).
CREATE TABLE IF NOT EXISTS etf_holdings (
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (symbol, as_of_date)
);

-- Sector weight breakdown stored as raw JSON in payload_json. PK = (symbol, as_of_date).
CREATE TABLE IF NOT EXISTS etf_sector_weights (
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (symbol, as_of_date)
);

-- Multi-period performance (ytd, 1y, 3y, 5y, 10y). PK = (symbol, as_of_date).
CREATE TABLE IF NOT EXISTS etf_performance (
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    ytd REAL,
    "1y" REAL,
    "3y" REAL,
    "5y" REAL,
    "10y" REAL,
    PRIMARY KEY (symbol, as_of_date)
);

-- Equity-level PE/PB/PS holdings stored as raw JSON. PK = (symbol, as_of_date).
CREATE TABLE IF NOT EXISTS etf_equity_holdings (
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (symbol, as_of_date)
);

-- ESG scores stored as raw JSON. PK = (symbol, as_of_date).
CREATE TABLE IF NOT EXISTS etf_esg (
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (symbol, as_of_date)
);

-- News items. PK = url; INSERT OR IGNORE on conflict (drop duplicates).
CREATE TABLE IF NOT EXISTS etf_news (
    url TEXT PRIMARY KEY,
    symbol TEXT,
    title TEXT,
    publisher TEXT,
    published_at TEXT,
    summary TEXT
);

-- Audit log of every call that passed HMAC auth. One row per ingest call.
CREATE TABLE IF NOT EXISTS etf_ingest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT,
    data_type TEXT,
    source_ip TEXT,
    accepted INTEGER DEFAULT 0,
    rejected INTEGER DEFAULT 0,
    received_at TEXT
);

-- Rate-limit state for restart survival. One row per source IP with the
-- 24h sliding-window start and current count.
CREATE TABLE IF NOT EXISTS rate_limit_state (
    ip TEXT PRIMARY KEY,
    window_start TEXT NOT NULL,
    count INTEGER NOT NULL
);

-- Indexes for the most common read patterns.
CREATE INDEX IF NOT EXISTS idx_etf_quote_symbol_ts ON etf_quote(symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_etf_news_symbol_published ON etf_news(symbol, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_etf_ingest_log_received ON etf_ingest_log(received_at DESC);
