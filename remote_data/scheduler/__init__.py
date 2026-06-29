"""remote_data.scheduler: APScheduler wiring."""

from remote_data.scheduler.jobs import (  # noqa: F401
    build_scheduler,
    market_status,
    quote_interval_minutes,
    make_fetch_job,
    make_push_job,
    safe_run,
)