from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


# PUBLIC_INTERFACE
def now_utc() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


# PUBLIC_INTERFACE
def to_object_id(value: str) -> ObjectId:
    """Convert a string to ObjectId (raises ValueError if invalid)."""
    try:
        return ObjectId(value)
    except Exception as exc:  # noqa: BLE001 - convert any bson errors to ValueError
        raise ValueError("Invalid ObjectId") from exc


# PUBLIC_INTERFACE
def mongo_to_api(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert a MongoDB document into JSON-friendly API dict."""
    out: dict[str, Any] = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for k, v in list(out.items()):
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
    return out
