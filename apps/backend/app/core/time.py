"""Time helpers for backend UTC timestamps."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """Normalize naive or timezone-aware datetimes into aware UTC values."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def seconds_between(start: datetime | None, end: datetime | None) -> float | None:
    """Return elapsed seconds between two datetimes after UTC normalization."""
    start_utc = as_utc(start)
    end_utc = as_utc(end)
    if start_utc is None or end_utc is None:
        return None
    return (end_utc - start_utc).total_seconds()
