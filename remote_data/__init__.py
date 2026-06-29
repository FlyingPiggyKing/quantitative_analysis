"""remote_data: overseas-machine data pipeline (fetcher + store + pusher + scheduler).

This package is the ONLY entry point on the overseas machine. It MUST NOT
import from `backend/` or `frontend/` — deployment topology assumes the
overseas box carries only this package.
"""

__version__ = "0.1.0"