## 1. Spec

- [x] 1.1 Create `specs/etf-health-endpoint/spec.md` documenting the `/health` endpoint contract

## 2. Code fix

- [x] 2.1 Edit `remote_data/health.py`: replace `_HealthHandler.conn_factory` (class-level callable) with `_HealthHandler.db_path` (class-level string)
- [x] 2.2 Edit `remote_data/health.py` `do_GET`: call `local_db.connect(self.db_path)` instead of `self.conn_factory()`
- [x] 2.3 Edit `remote_data/health.py` `make_server`: set `_HealthHandler.db_path = db_path` instead of the lambda assignment
- [x] 2.4 Verify the fix on the overseas box: restart daemon, `curl -sS http://127.0.0.1:8001/health` returns 200 with the JSON payload

## 3. Deploy

- [x] 3.1 Commit the fix to the repo (`etf-fetcher-pusher-health-fix` branch or main)
- [x] 3.2 Pull on the overseas box, restart the daemon