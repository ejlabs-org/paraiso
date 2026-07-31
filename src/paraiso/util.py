"""Small internal helpers: ids and timestamps. No external dependencies."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


def new_id(prefix: str) -> str:
    """A short, readable, collision-resistant id like ``itm_9f3c1a2b4d5e``."""
    return f"{prefix}_{uuid4().hex[:12]}"


def now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)
