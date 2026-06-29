## ADDED Requirements

### Requirement: Scheduler runs fetches on configured cadence
The system SHALL use APScheduler (or equivalent in-process scheduler) to invoke each fetcher function at the cadence defined in `.env` defaults. Defaults:

| Job | Default cadence |
|---|---|
| `fetch_quotes` | every 5 minutes (market hours), every 30 minutes (pre/post-market) |
| `fetch_news` | every 60 minutes |
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

### Requirement: Pusher runs as a continuous loop independent of fetchers
The push loop MUST run as a separate job (default: every 30 seconds) that scans for `pushed_at IS NULL` rows and ships them, decoupled from fetch cadence.

#### Scenario: Push loop runs
- **WHEN** 30 seconds elapse since the last push cycle
- **THEN** the pusher scans for pending rows across all data types and ships them per the etf-pusher spec

#### Scenario: Decoupled from fetchers
- **WHEN** a fetcher fails and writes no records
- **THEN** the push loop still runs and ships any records that are pending from previous cycles

### Requirement: Backfill task populates 2 years of fundamentals on first run
The system MUST run a one-shot backfill on startup if the `etf_fundamentals` table is empty. The backfill SHALL fetch the current snapshot for all symbols in `SYMBOLS` and SHALL additionally attempt to fetch up to 2 years of `valuation_measures` history per symbol (acknowledged in design that this returns no data for ETFs and ~2 years of quarterly data for any symbol that happens to be a stock — the result is written regardless).

#### Scenario: Empty table on first run
- **WHEN** the system starts and `etf_fundamentals` is empty
- **THEN** the backfill task runs, populates the table with current snapshot rows for all symbols, and writes a `backfill_complete` row to `fetch_log`

#### Scenario: Table not empty
- **WHEN** the system starts and `etf_fundamentals` already has rows
- **THEN** the backfill task is skipped

### Requirement: Scheduler is single-process and resilient to job failure
The scheduler MUST run all jobs in the same process. A job that raises MUST NOT crash the process; the error MUST be logged to `fetch_log` (for fetch jobs) or `push_log` (for the push loop) and the next tick of that job MUST proceed normally.

#### Scenario: Job raises
- **WHEN** `fetch_quotes` raises an unhandled exception
- **THEN** the exception is caught, logged with traceback, written to `fetch_log`, and the scheduler continues to the next scheduled job

#### Scenario: Process restart resumes schedule
- **WHEN** the process is killed and restarted
- **THEN** all jobs resume per their configured cadence; no manual intervention is required
