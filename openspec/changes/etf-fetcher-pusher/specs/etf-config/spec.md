## ADDED Requirements

### Requirement: All configuration is read from `.env` and process env, never from code
The system MUST read every configuration value from the environment (loaded via `python-dotenv` from `.env` if present). The `config` module MUST validate required keys at startup and MUST fail fast with a clear error if any are missing.

#### Scenario: Missing required key
- **WHEN** the system starts and `ETF_PIPELINE_SECRET` is not set
- **THEN** startup aborts with a logged error message naming the missing key

#### Scenario: Default values applied
- **WHEN** `TIME_WINDOW_SECONDS` is not set
- **THEN** the system uses the default value of 300

### Requirement: Configuration keys and defaults
The system MUST support the following keys:

| Key | Required | Default | Purpose |
|---|---|---|---|
| `DEPLOY_ROLE` | yes | — | Must be `LOCAL` (this change always runs as LOCAL) |
| `REMOTE_INGEST_URL` | yes | — | e.g. `https://8.153.90.28:443/api/etf/ingest` |
| `ETF_PIPELINE_SECRET` | yes | — | HMAC-SHA256 shared secret, 32+ bytes recommended |
| `LOCAL_DB_PATH` | no | `data/etf_local.db` | Local SQLite file path |
| `TIME_WINDOW_SECONDS` | no | `300` | HMAC timestamp window |
| `HTTP_TIMEOUT_SECONDS` | no | `15` | Per-request HTTP timeout |
| `YAHOOQUERY_MAX_RETRIES` | no | `3` | yahooquery retry cap |
| `YAHOOQUERY_BACKOFF_SECONDS` | no | `2` | yahooquery initial backoff |
| `SYMBOLS` | no | see default list below | Comma-separated ETF tickers |
| `FETCH_QUOTES_INTERVAL_MINUTES` | no | `5` | |
| `FETCH_QUOTES_OFFHOURS_INTERVAL_MINUTES` | no | `30` | Pre/post-market cadence |
| `FETCH_NEWS_INTERVAL_MINUTES` | no | `60` | |
| `PUSH_INTERVAL_SECONDS` | no | `30` | Push loop cadence |
| `BATCH_SIZE` | no | `500` | Max records per HTTP POST |
| `MARKET_TZ` | no | `US/Eastern` | For market-hours detection |
| `LOG_LEVEL` | no | `INFO` | Standard Python levels |
| `LOG_FILE` | no | `data/etf_local.log` | Rotating log file path |

#### Scenario: Default symbol list
- **WHEN** `SYMBOLS` is not set
- **THEN** the system uses: `QQQ,IVV,SPY,VTI,VOO,QQQM,SCHB,ITOT,VEA,VWO,BND,AGG,TLT,IEF,GLD,SLV,USO,UNG,ARKK,SOXX`

#### Scenario: Custom symbol list
- **WHEN** `SYMBOLS=QQQ,SPY` is set
- **THEN** the system fetches and pushes only those two symbols

### Requirement: `.env.example` documents all keys
The repo MUST contain `remote_data/.env.example` listing every key, its default, and a one-line description. Real `.env` files MUST be in `.gitignore`.

#### Scenario: Example file present
- **WHEN** a developer clones the repo
- **THEN** they can `cp remote_data/.env.example remote_data/.env` and edit values without consulting source code

#### Scenario: Real `.env` not committed
- **WHEN** `git status` is run
- **THEN** `remote_data/.env` is not shown as an untracked or tracked file
