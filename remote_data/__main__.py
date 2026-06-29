"""Allow `python -m remote_data` to invoke the daemon."""

from remote_data.main import main

raise SystemExit(main())