"""Small internal helpers: ids and timestamps. No external dependencies."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


def new_id(prefix: str) -> str:
    """A short, readable, collision-resistant id like ``itm_9f3c1a2b4d5e``."""
    return f"{prefix}_{uuid4().hex[:12]}"


def short_id(entity_id: str, width: int = 8) -> str:
    """A fixed-width display form of an id: ``prefix_`` + the first ``width``
    characters of the random part. Keeps listings aligned even when ids differ
    in length (e.g. native 12-hex ids vs longer imported ones). Ids with no
    prefix, or a shorter random part, are returned unchanged."""
    prefix, sep, rest = entity_id.partition("_")
    if not sep or len(rest) <= width:
        return entity_id
    return f"{prefix}_{rest[:width]}"


def now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)
