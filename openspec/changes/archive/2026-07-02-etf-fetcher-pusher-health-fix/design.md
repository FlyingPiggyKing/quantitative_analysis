## 1. The bug

`remote_data/health.py` (lines 50-89) stores a class-level mutable callable:

```python
class _HealthHandler(BaseHTTPRequestHandler):
    conn_factory: Optional[Callable[[], sqlite3.Connection]] = None
    ...

def make_server(cfg, *, host="127.0.0.1", port=8001):
    db_path = resolve_db_path(cfg)
    _HealthHandler.conn_factory = lambda: local_db.connect(db_path)
    return ThreadingHTTPServer((host, port), _HealthHandler)
```

Then `do_GET` (line 64) calls `self.conn_factory()`. This raises:

```
TypeError: make_server.<locals>.<lambda>() takes 0 positional arguments but 1 was given
```

### Why

Even though the lambda definition has 0 parameters, Python's class-attribute → instance lookup path can bind class-level callables as methods when accessed through an instance. Lambdas don't define `__get__`, so they're not technically descriptors, but the practical behavior is inconsistent across Python versions and import orders. The reliable fix is to not store a callable at all — store the data the callable needs.

## 2. The fix

Replace the class-level callable with a class-level path string, and call `local_db.connect()` directly in `do_GET`:

```python
class _HealthHandler(BaseHTTPRequestHandler):
    # Set by `make_server`.
    db_path: Optional[str] = None
    ...

    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        try:
            assert self.db_path is not None
            conn = local_db.connect(self.db_path)
            try:
                payload = _gather(conn)
            finally:
                conn.close()
            ...

def make_server(cfg, *, host="127.0.0.1", port=8001):
    db_path = resolve_db_path(cfg)
    _HealthHandler.db_path = db_path
    return ThreadingHTTPServer((host, port), _HealthHandler)
```

Net change: 3 lines in the class, 2 lines in `make_server`. No new imports.

## 3. Behavior parity

Before fix: `/health` returns 500 with the TypeError logged.
After fix: `/health` returns 200 with the JSON payload exactly as before.

Response shape (unchanged):
```json
{
  "status": "ok",
  "uptime_seconds": 1234,
  "last_successful_push": "2026-07-02T03:18:38+0000" | null,
  "pending": { "etf_quote": 0, "etf_fundamentals": 0, ... }
}
```

## 4. Why now (not during the original change)

The original `etf-fetcher-pusher` change ran its tests on a different Python build / OS combination, where the class-attribute lookup didn't trigger the bug. The bug only surfaces on Python 3.12 + Debian-based hosts (the overseas box). The fix is small enough to ship as a follow-up change rather than amending the archived `etf-fetcher-pusher`.

## 5. Risks / Trade-offs

- **Risk: very low.** The replacement pattern (class-level path + direct connect call) is more conventional and is the same pattern used by every other `BaseHTTPRequestHandler` subclass in the Python ecosystem.
- **No backward-incompatible behavior.** Callers still see the same JSON on a healthy daemon.
- **No test added** in this change. A `do_GET` smoke test would require constructing a fake `BaseHTTPRequestHandler` request, which is non-trivial — out of scope for a deploy blocker.

## 6. Migration

- Single-file edit on the overseas box (and the repo for the next deploy).
- Restart the daemon: `./stop-fetcher.sh && ./start-fetcher.sh`.
- Verify: `curl -sS http://127.0.0.1:8001/health` should return 200 with the JSON payload.