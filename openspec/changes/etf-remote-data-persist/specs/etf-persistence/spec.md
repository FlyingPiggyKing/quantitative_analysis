## ADDED Requirements

### Requirement: Database file and tables are created idempotently on startup
The system MUST create the SQLite file at `REMOTE_DB_PATH` (default `./data/etf_remote.db`) if it does not exist, and MUST execute `backend/migrations/etf_schema.sql` on every startup. The schema MUST use `CREATE TABLE IF NOT EXISTS` so repeated startup is safe.

#### Scenario: First run
- **WHEN** the backend starts and `data/etf_remote.db` does not exist
- **THEN** the file is created and all 9 tables (8 data + 1 ingest_log) are created

#### Scenario: Subsequent run
- **WHEN** the backend starts and `data/etf_remote.db` already exists with all tables
- **THEN** startup is a no-op for the schema (IF NOT EXISTS prevents errors)

### Requirement: Per-data-type table schemas
The schema MUST create the following tables with these columns (others like `created_at` may be added but MUST NOT conflict with these):

| Table | Columns |
|---|---|
| `etf_quote` | `symbol TEXT, ts TEXT, price REAL, pre_market_price REAL, post_market_price REAL, volume INTEGER, PRIMARY KEY (symbol, ts)` |
| `etf_fundamentals` | `symbol TEXT, as_of TEXT, pe REAL, pb REAL, dividend_yield REAL, dividend_rate REAL, PRIMARY KEY (symbol, as_of)` |
| `etf_holdings` | `symbol TEXT, as_of_date TEXT, payload_json TEXT, PRIMARY KEY (symbol, as_of_date)` |
| `etf_sector_weights` | `symbol TEXT, as_of_date TEXT, payload_json TEXT, PRIMARY KEY (symbol, as_of_date)` |
| `etf_performance` | `symbol TEXT, as_of_date TEXT, ytd REAL, 1y REAL, 3y REAL, 5y REAL, 10y REAL, PRIMARY KEY (symbol, as_of_date)` |
| `etf_equity_holdings` | `symbol TEXT, as_of_date TEXT, payload_json TEXT, PRIMARY KEY (symbol, as_of_date)` |
| `etf_esg` | `symbol TEXT, as_of_date TEXT, payload_json TEXT, PRIMARY KEY (symbol, as_of_date)` |
| `etf_news` | `url TEXT PRIMARY KEY, symbol TEXT, title TEXT, publisher TEXT, published_at TEXT, summary TEXT` |
| `etf_ingest_log` | `id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, data_type TEXT, source_ip TEXT, accepted INTEGER, rejected INTEGER, received_at TEXT` |

#### Scenario: Tables exist
- **WHEN** the schema is executed
- **THEN** all 9 tables are present in the database (verifiable via `sqlite_master`)

### Requirement: UPSERT semantics by primary key
The persistence service MUST use SQLite `INSERT ... ON CONFLICT(primary_key) DO UPDATE` (or the SQLite ≥ 3.24 `UPSERT` syntax) for all tables except `etf_news`. For `etf_news` the service MUST use `INSERT OR IGNORE` so duplicate URLs are dropped silently.

#### Scenario: Duplicate quote
- **WHEN** the same `(symbol, ts, price)` is pushed twice
- **THEN** the second push overwrites the first (UPSERT) — there is exactly one row in the table

#### Scenario: Duplicate news URL
- **WHEN** the same `url` is pushed twice
- **THEN** the second push is silently ignored (INSERT OR IGNORE) — the original row's `summary` is preserved

#### Scenario: Different timestamp same symbol
- **WHEN** quotes for `(QQQ, 03:14)` and `(QQQ, 03:15)` are pushed
- **THEN** both rows exist in `etf_quote` — UPSERT does not collapse different PKs

### Requirement: `payload_json` columns store the raw `records` array verbatim
For `etf_holdings`, `etf_sector_weights`, `etf_equity_holdings`, `etf_esg`, the persistence service MUST store the entire `holdings` / `sectors` / `esg` array as a JSON-serialized TEXT in the `payload_json` column. The remote DB does NOT need a typed schema for these nested arrays; consumers read and parse the JSON.

#### Scenario: Top10 holdings stored
- **WHEN** a batch with 10 holdings is pushed
- **THEN** the `payload_json` column contains a JSON array of 10 objects, with `weight_pct` preserved as numbers

### Requirement: Read operations are available to the read API
The persistence service MUST expose typed read methods used by `etf-read-api`:
- `get_latest_quote(symbol, limit)` → list of quote rows
- `get_fundamentals(symbol)` → single row (latest `as_of`)
- `get_holdings(symbol)` → single row
- `get_sector_weights(symbol)` → single row
- `get_equity_holdings(symbol)` → single row
- `get_performance(symbol)` → single row
- `get_esg(symbol)` → single row
- `get_news(symbol, page, page_size)` → list, ordered by `published_at DESC`
- `list_symbols()` → distinct symbol set across all tables

#### Scenario: Fetching latest quote
- **WHEN** `get_latest_quote("QQQ", limit=10)` is called
- **THEN** the most recent 10 quote rows (by `ts` desc) are returned

#### Scenario: No data for a symbol
- **WHEN** `get_fundamentals("UNKNOWN")` is called
- **THEN** the method returns `None` (or empty list, depending on the contract per-method) and the read API returns HTTP 404
