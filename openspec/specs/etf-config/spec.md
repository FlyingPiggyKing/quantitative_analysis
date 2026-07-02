# etf-config Specification

## Purpose
TBD - created by archiving change etf-fetcher-pusher. Update Purpose after archive.
## Requirements
### Requirement: All configuration is read from `.env` and process env, never from code
The system MUST read every configuration value from the environment (loaded via `python-dotenv` from `.env` if present). The `config` module MUST validate required keys at startup and MUST fail fast with a clear error if any are missing.

#### Scenario: Missing required key
- **WHEN** the system starts and `ETF_PIPELINE_SECRET` is not set
- **THEN** startup aborts with a logged error message naming the missing key

#### Scenario: Default values applied
- **WHEN** `TIME_WINDOW_SECONDS` is not set
- **THEN** the system uses the default value of 300

### Requirement: Fetcher configuration keys and defaults
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

### Requirement: New backend env keys are validated at startup
The system MUST read the new configuration from environment variables, fail-fast if any required key is missing, and apply documented defaults for optional keys. Validation MUST run during FastAPI startup so the process aborts before serving any request.

#### Scenario: All required keys present
- **WHEN** the backend starts with `ETF_PIPELINE_SECRET`, `INGEST_MAX_REQUESTS_PER_DAY`, `REMOTE_DB_PATH`, `TIME_WINDOW_SECONDS` all set
- **THEN** startup proceeds and the ETF router is registered

#### Scenario: Missing required key
- **WHEN** the backend starts without `ETF_PIPELINE_SECRET`
- **THEN** startup aborts with a clear error message naming the missing variable

### Requirement: Backend configuration keys and defaults
The system MUST support the following keys:

| Key | Required | Default | Purpose |
|---|---|---|---|
| `ETF_PIPELINE_SECRET` | yes | — | HMAC-SHA256 shared secret, 32+ bytes recommended (must match the value in `etf-fetcher-pusher`'s `remote_data/.env`) |
| `REMOTE_DB_PATH` | no | `./data/etf_remote.db` | SQLite file path for ETF data |
| `TIME_WINDOW_SECONDS` | no | `300` | HMAC timestamp window, must match `etf-fetcher-pusher` |
| `INGEST_MAX_REQUESTS_PER_DAY` | no | `50000` | Per-IP 24h sliding window cap |
| `INGEST_MAX_BODY_BYTES` | no | `1048576` | 1 MB body cap |
| `RATE_LIMIT_FLUSH_SECONDS` | no | `60` | How often the rate-limit state is persisted to SQLite |
| `LOG_LEVEL` | no | `INFO` | (inherited from existing backend) |

#### Scenario: Defaults applied
- **WHEN** `TIME_WINDOW_SECONDS` is not set
- **THEN** the system uses 300 (5 minutes)

#### Scenario: Custom body limit
- **WHEN** `INGEST_MAX_BODY_BYTES=524288` is set
- **THEN** the endpoint rejects bodies larger than 512 KB with HTTP 413

### Requirement: `.env.example` documents all new keys
The repo's `backend/.env.example` MUST be updated to include every new key (and existing keys remain). Each line MUST include a one-line description and a `# example:` comment for non-obvious values.

#### Scenario: New keys in example
- **WHEN** a developer clones the repo and copies `backend/.env.example` to `backend/.env`
- **THEN** all required keys are present and documented

### Requirement: Secret value is never logged
The system MUST NOT log the value of `ETF_PIPELINE_SECRET` (or any secret-like env var) at any log level. Startup messages that reference the secret MUST only mention its presence (`"secret: <set>"` or `"secret: <missing>"`), never the value.

#### Scenario: Secret absent from logs
- **WHEN** the backend starts successfully
- **THEN** no log line contains the value of `ETF_PIPELINE_SECRET`

