"""The data records PARAISO works with.

All four are plain dataclasses with ``to_dict``/``from_dict`` for JSON
round-tripping. Ids and timestamps default themselves, so the smallest possible
construction is e.g. ``Area("Health")`` or ``Capture("call the dentist")``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from . import palette
from .framework import Bucket
from .util import from_iso, new_id, now, to_iso


@dataclass
class Capture:
    """A raw thought sitting in the Inbox, not yet filed.

    A capture is closed either by filing it (which sets :attr:`item_id` and
    ``processed = True``) or by discarding it.
    """

    text: str
    id: str = field(default_factory=lambda: new_id("cap"))
    source: str = "manual"  # manual | voice | email | import | ...
    note: str = ""
    processed: bool = False
    item_id: Optional[str] = None  # the Item this capture became, if filed
    created_at: datetime = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "note": self.note,
            "processed": self.processed,
            "item_id": self.item_id,
            "created_at": to_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Capture":
        return cls(
            text=data["text"],
            id=data["id"],
            source=data.get("source", "manual"),
            note=data.get("note", ""),
            processed=data.get("processed", False),
            item_id=data.get("item_id"),
            created_at=from_iso(data.get("created_at")) or now(),
        )


@dataclass
class Item:
    """A filed piece of knowledge living in exactly one :class:`Bucket`.

    It may belong to an Area and/or advance an Objective, but neither is
    required — structure is always optional.
    """

    title: str
    bucket: Bucket
    id: str = field(default_factory=lambda: new_id("itm"))
    summary: str = ""
    content: str = ""
    area_id: Optional[str] = None
    objective_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    source_capture_id: Optional[str] = None
    status: str = "active"  # active | archived
    created_at: datetime = field(default_factory=now)
    updated_at: datetime = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "bucket": self.bucket.value,
            "summary": self.summary,
            "content": self.content,
            "area_id": self.area_id,
            "objective_id": self.objective_id,
            "tags": list(self.tags),
            "source_capture_id": self.source_capture_id,
            "status": self.status,
            "created_at": to_iso(self.created_at),
            "updated_at": to_iso(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Item":
        return cls(
            title=data["title"],
            bucket=Bucket.coerce(data["bucket"]),
            id=data["id"],
            summary=data.get("summary", ""),
            content=data.get("content", ""),
            area_id=data.get("area_id"),
            objective_id=data.get("objective_id"),
            tags=list(data.get("tags", [])),
            source_capture_id=data.get("source_capture_id"),
            status=data.get("status", "active"),
            created_at=from_iso(data.get("created_at")) or now(),
            updated_at=from_iso(data.get("updated_at")) or now(),
        )


@dataclass
class Area:
    """A human-defined domain of life (Health, Finances, a client).

    Areas are created only by people — a classifier may suggest that an item
    belongs to an existing Area, but it must never invent one.
    """

    name: str
    id: str = field(default_factory=lambda: new_id("area"))
    description: str = ""
    color: str = palette.DEFAULT_ACCENT
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "tags": list(self.tags),
            "created_at": to_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Area":
        return cls(
            name=data["name"],
            id=data["id"],
            description=data.get("description", ""),
            color=data.get("color", palette.DEFAULT_ACCENT),
            tags=list(data.get("tags", [])),
            created_at=from_iso(data.get("created_at")) or now(),
        )


@dataclass
class Objective:
    """A directional goal that items *advance*. You never file into one."""

    title: str
    id: str = field(default_factory=lambda: new_id("obj"))
    description: str = ""
    area_id: Optional[str] = None
    status: str = "active"  # active | completed | archived
    created_at: datetime = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "area_id": self.area_id,
            "status": self.status,
            "created_at": to_iso(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Objective":
        return cls(
            title=data["title"],
            id=data["id"],
            description=data.get("description", ""),
            area_id=data.get("area_id"),
            status=data.get("status", "active"),
            created_at=from_iso(data.get("created_at")) or now(),
        )
