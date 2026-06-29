# remote_data — Overseas Machine Data Pipeline

This package runs **only** on the overseas server. Its job:

1. Pull ETF data from Yahoo Finance (via `yahooquery`).
2. Persist every record to a local SQLite database at `data/etf_local.db`.
3. Push records to the Chinese ingest endpoint (`REMOTE_INGEST_URL`) over HMAC-signed HTTPS.

The package is self-contained: it never imports `backend/` or `frontend/`.

---

## Quick start (recommended: systemd, production)

```bash
cd remote_data
uv sync
cp .env.example .env
$EDITOR .env                    # fill REMOTE_INGEST_URL, ETF_PIPELINE_SECRET, SYMBOLS

# 1) Bootstrap DB (idempotent — safe to re-run)
uv run python remote_data/scripts/init_local_db.py

# 2) Install the systemd unit from example below, then:
sudo systemctl daemon-reload
sudo systemctl enable --now remote-data.service
sudo journalctl -u remote-data.service -f
```

The daemon calls `local_db.init()` again on startup, so step 1 is only needed for
fresh deployments / disaster recovery / CI smoke tests.

---

## Quick start (no systemd — dev machine / ad-hoc)

```bash
cd /path/to/repo
./scripts/start-etf-fetcher.sh
```

`start-etf-fetcher.sh` runs `init_local_db.py` first and then
`python -m remote_data` in the foreground. Use this when systemd is unavailable
(mac dev box, containers, debugging). The bootstrap contract is identical to
the systemd path.

You can also run the bare entry point — `main.py`'s startup hook calls
`local_db.init()` before the scheduler starts, so the schema is guaranteed to
exist:

```bash
uv run python -m remote_data
```

---

## Configuration

See [`.env.example`](.env.example) for the full list. All keys are loaded via
`python-dotenv` from `remote_data/.env`. Required:

| Key | Example |
|---|---|
| `DEPLOY_ROLE` | `LOCAL` (always) |
| `REMOTE_INGEST_URL` | `https://8.153.90.28:443/api/etf/ingest` |
| `ETF_PIPELINE_SECRET` | 32+ byte random string — must match the ingest side |

---

## systemd unit example

`/etc/systemd/system/remote-data.service`:

```ini
[Unit]
Description=ETF data pipeline (overseas machine)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/quantitative_analysis
ExecStart=/opt/quantitative_analysis/remote_data/.venv/bin/python -m remote_data
Restart=on-failure
RestartSec=30
StartLimitIntervalSec=120
StartLimitBurst=3

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

---

## Bootstrap entry points (three paths converge on the same schema)

| Path | When to use |
|---|---|
| `main.py` startup hook | Always invoked when daemon starts (systemd or `python -m remote_data`) |
| `remote_data/scripts/init_local_db.py` | Standalone — disaster recovery, CI smoke tests, replica bootstrap |
| `scripts/start-etf-fetcher.sh` | No-systemd deployments, ad-hoc foreground runs |

All three call `local_db.init()` which is idempotent (safe on fresh filesystem,
on a fully initialized DB, and on a partial DB).

---

## Operations

- **Logs**: `data/etf_local.log` (rotating, 10MB × 5) + stdout
- **DB inspect**: `sqlite3 data/etf_local.db ".tables"`
- **Pending pushes**: `sqlite3 data/etf_local.db "SELECT data_type, COUNT(*) FROM etf_quote WHERE pushed_at IS NULL GROUP BY data_type"`
- **Health check (if enabled)**: `curl http://127.0.0.1:8001/health`

---

## Retention

The store runs a daily prune job (see `etf-scheduler` spec):

| Table | Retention |
|---|---|
| `etf_quote` | 90 days (by `ts`) |
| `etf_news` | 30 days (by `published_at`) |
| `push_log` | 30 days |

---

## Tests

```bash
cd remote_data
uv run pytest
```