"""Naive-UTC clock helper. The DB stores naive UTC datetimes, so keep them naive."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC time as a naive datetime (replacement for deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
