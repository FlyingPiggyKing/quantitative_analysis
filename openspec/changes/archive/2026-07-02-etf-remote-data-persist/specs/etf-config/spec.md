## ADDED Requirements

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
