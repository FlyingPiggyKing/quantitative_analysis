## ADDED Requirements

### Requirement: Daemon exposes a local `/health` HTTP endpoint
The overseas pusher daemon SHALL run an HTTP server bound to `127.0.0.1` (loopback only — not exposed to the public network) on `HEALTH_PORT` (default `8001`). The server SHALL accept `GET /health` and return `200 OK` with a JSON body describing the daemon's liveness.

#### Scenario: Healthy daemon
- **WHEN** `curl -sS http://127.0.0.1:8001/health` is called and the daemon is running
- **THEN** the response is `200 OK` with body:
  ```json
  {
    "status": "ok",
    "uptime_seconds": 1234,
    "last_successful_push": "2026-07-02T03:18:38+0000",
    "pending": { "etf_quote": 0, "etf_fundamentals": 0, ... }
  }
  ```
- **AND** `last_successful_push` is `null` if no successful push has occurred yet

#### Scenario: Unknown path
- **WHEN** `curl -sS http://127.0.0.1:8001/foo` is called
- **THEN** the response is `404 Not Found`

#### Scenario: Endpoint can be disabled
- **WHEN** `ENABLE_HEALTH_ENDPOINT=0` is set in `.env`
- **THEN** the daemon does not bind the health server (no port 8001 listener)

### Requirement: Endpoint is loopback-only
The health server MUST bind to `127.0.0.1` (or another loopback address). It MUST NOT be reachable from the public network.

#### Scenario: External request is refused
- **WHEN** a request arrives at `<public-ip>:8001/health` from outside the box
- **THEN** the connection is refused (port not bound on the public interface)

### Requirement: Endpoint reads from the local SQLite store
The endpoint MUST read live data from `LOCAL_DB_PATH` (resolved via `resolve_db_path(cfg)`) on every request. The `pending` map MUST contain an entry for every business table with `pushed_at IS NULL AND failed_at IS NULL`.

#### Scenario: Pending counts reflect current state
- **WHEN** there are 5 `etf_quote` rows with `pushed_at IS NULL`
- **THEN** `pending.etf_quote` in the response equals `5`

### Requirement: Endpoint errors are logged, not raised
If reading from the SQLite store fails, the endpoint MUST log the exception and return `500 Internal Server Error`. The daemon's main push loop MUST NOT be affected by health endpoint errors.

#### Scenario: SQLite read failure
- **WHEN** the SQLite file is locked or missing
- **THEN** the endpoint returns `500` and writes an `ERROR` log line via `logger.exception(...)`
- **AND** the daemon's main loop continues running unaffected

### Requirement: Implementation MUST use a path attribute, not a class-level callable
The endpoint SHALL be implemented using Python's `http.server.BaseHTTPRequestHandler` (or `ThreadingHTTPServer` for concurrency). The handler MUST read the database path via a class-level string attribute (`db_path: Optional[str]`). The handler MUST NOT store a class-level callable for connection creation — calling such a callable via `self.<name>()` may bind it as a method and raise a `TypeError`. The handler MUST instead call `local_db.connect(self.db_path)` directly.

#### Scenario: Handler stores path, not callable
- **WHEN** the handler is constructed by `make_server(cfg)`
- **THEN** `_HealthHandler.db_path` is set to the resolved DB path string
- **AND** `do_GET` calls `local_db.connect(self.db_path)` directly