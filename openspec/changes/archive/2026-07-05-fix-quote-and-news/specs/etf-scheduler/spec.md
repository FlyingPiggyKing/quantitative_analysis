## MODIFIED Requirements

### Requirement: Scheduler runs fetches on configured cadence
The system SHALL use APScheduler (or equivalent in-process scheduler) to invoke each fetcher function at the cadence defined in `.env` defaults. Defaults:

| Job | Default cadence |
|---|---|
| `fetch_quotes` | every 5 minutes (market hours), every 30 minutes (pre/post-market) |
| `fetch_kline` | daily at 16:35 US/Eastern |
| `fetch_fundamentals` | daily at 16:40 US/Eastern |
| `fetch_performance` | daily at 16:45 US/Eastern |
| `fetch_holdings` | weekly on Sunday at 10:00 US/Eastern |
| `fetch_sector_weightings` | weekly on Sunday at 10:15 US/Eastern |
| `fetch_equity_holdings` | weekly on Sunday at 10:30 US/Eastern |
| `fetch_esg` | monthly on the 1st at 10:00 US/Eastern |

#### Scenario: Quote fetch fires on schedule
- **WHEN** the system clock crosses the configured quote tick time
- **THEN** `fetch_quotes` is invoked with the symbols from `SYMBOLS`; results are written to the local store and pushed via the pusher loop

#### Scenario: Configurable cadence
- **WHEN** `FETCH_QUOTES_INTERVAL_MINUTES=10` is set in `.env`
- **THEN** `fetch_quotes` fires every 10 minutes instead of the default 5

#### Scenario: News fetch is not scheduled
- **WHEN** the scheduler starts
- **THEN** no news fetch job is registered; `fetch_news` is not invoked on any cadence; this is the supported steady state until a future change re-introduces news ingestion from a different source