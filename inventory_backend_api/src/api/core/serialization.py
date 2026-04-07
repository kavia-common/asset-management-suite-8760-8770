from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID


# PUBLIC_INTERFACE
def now_utc() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


# PUBLIC_INTERFACE
def to_uuid(value: str) -> UUID:
    """Convert a string to UUID (raises ValueError if invalid)."""
    try:
        return UUID(value)
    except Exception as exc:  # noqa: BLE001 - convert any errors to ValueError
        raise ValueError("Invalid UUID") from exc
