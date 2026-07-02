## Why

The overseas pusher daemon exposes a `/health` HTTP endpoint on `127.0.0.1:8001` so an operator (or `curl`) can confirm the daemon is alive. After the `etf-fetcher-pusher` change was archived, a pre-existing bug in `remote_data/health.py` surfaced during deployment:

- The handler class (`_HealthHandler`) stores a class-level mutable attribute `conn_factory` set to a 0-arg lambda that returns `local_db.connect(db_path)`.
- When `do_GET` reads it via `self.conn_factory()`, Python occasionally binds it as a method (the lambda has no `__get__` but the class-level assignment makes it ambiguous), causing a `TypeError: <lambda>() takes 0 positional arguments but 1 was given` on every health check.
- This is a soft failure: the daemon keeps running, the pusher loop works, but `/health` returns 500. Operators can't distinguish "daemon down" from "daemon up but health endpoint broken."

This change fixes the bug by replacing the class-level callable with a class-level `db_path` string and calling `local_db.connect(self.db_path)` directly in `do_GET`. It also adds a spec for the health endpoint (which was previously undocumented — only mentioned in `design.md` and `tasks.md` of the original change).

## What Changes

- **Fix** `remote_data/health.py`: replace `conn_factory: Callable[[], sqlite3.Connection]` (class-level mutable callable) with `db_path: Optional[str]` (class-level mutable string), and call `local_db.connect(self.db_path)` in `do_GET`.
- **Add** `openspec/changes/etf-fetcher-pusher-health-fix/specs/etf-health-endpoint/spec.md` documenting the endpoint's contract (port, response shape, scoping).
- No behavior change visible to callers: `/health` continues to return the same JSON shape.

## Capabilities

### New Capabilities

- `etf-health-endpoint`: contract for the daemon's `GET /health` endpoint (bind address, response shape, opt-out via `ENABLE_HEALTH_ENDPOINT`).

### Modified Capabilities

None. This change is a bugfix in a file outside the `etf-remote-data-persist` scope; it touches the archived `etf-fetcher-pusher` change's `remote_data/health.py` only.

## Impact

- **Affected code**: `remote_data/health.py` (one class + one factory function).
- **No DB or schema changes.**
- **No config changes.** `ENABLE_HEALTH_ENDPOINT` and `HEALTH_PORT` are unchanged.
- **No API changes** (the health endpoint is internal/loopback; no caller depends on its prior broken behavior).
- **Risk**: low. The fix replaces one mutable-attribute pattern with a more standard one. The daemon's main loop and push pipeline are untouched.
- **Test coverage**: `remote_data/health.py` has no existing tests in the repo. Adding a smoke test that creates the handler and calls `do_GET` against a fake request would be nice-to-have but out of scope for this deploy-blocker fix.