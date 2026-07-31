"""Import/export a workspace as JSON.

Two formats are understood on import:

- **paraiso's own** export (what :meth:`Paraiso.to_dict` produces) — round-trips
  losslessly.
- a **PARA-style app export** shaped like ``{export_version, account, areas,
  objectives, items, inbox, ...}`` — mapped in best-effort. Items are placed by
  their ``module`` (``project``/``resource``/``seeds``/``archive``); Area and
  Objective links survive only when the export includes their ids.

This is a plain data adapter — it references no specific app, just the JSON
shape.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from . import palette
from .core import Paraiso
from .framework import Bucket
from .models import Area, Capture, Item, Objective

# Inbox statuses worth importing as live captures (the rest are closed history).
_OPEN_INBOX = {"unprocessed", "suggested", "transcribing"}


def load_export(path: str, *, name: Optional[str] = None) -> Paraiso:
    """Read a JSON export file and build a :class:`Paraiso` from it."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return from_export(data, name=name)


def from_export(data: dict[str, Any], *, name: Optional[str] = None) -> Paraiso:
    """Dispatch on the export shape."""
    if "export_version" in data or "account" in data:
        return _from_app_export(data, name=name)
    paraiso = Paraiso.from_dict(data)
    if name:
        paraiso.name = name
    return paraiso


def write_export(paraiso: Paraiso, path: str) -> None:
    """Write a workspace to ``path`` as paraiso's own JSON format."""
    Path(path).write_text(
        json.dumps(paraiso.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _from_app_export(data: dict[str, Any], *, name: Optional[str] = None) -> Paraiso:
    account = data.get("account") or {}
    paraiso = Paraiso(name or account.get("name") or "imported")

    for raw in data.get("areas", []):
        area = Area(
            name=raw.get("name", "Untitled"),
            description=raw.get("description", ""),
            color=raw.get("color") or palette.DEFAULT_ACCENT,
            tags=list(raw.get("tags") or []),
        )
        if raw.get("id"):
            area.id = raw["id"]
        paraiso._areas[area.id] = area

    for raw in data.get("objectives", []):
        obj = Objective(
            title=raw.get("title", "Untitled"),
            description=raw.get("description", ""),
            status=raw.get("status", "active"),
        )
        if raw.get("id"):
            obj.id = raw["id"]
        obj.area_id = raw.get("area_id") if raw.get("area_id") in paraiso._areas else None
        paraiso._objectives[obj.id] = obj

    for raw in data.get("items", []):
        try:
            bucket = Bucket.coerce(raw.get("module", "seed"))
        except Exception:
            bucket = Bucket.SEED
        item = Item(
            title=raw.get("title", "Untitled"),
            bucket=bucket,
            summary=raw.get("summary", ""),
            content=raw.get("content", ""),
            area_id=raw.get("area_id") if raw.get("area_id") in paraiso._areas else None,
            objective_id=(
                raw.get("objective_id")
                if raw.get("objective_id") in paraiso._objectives
                else None
            ),
            tags=list(raw.get("tags") or []),
            status=raw.get("status", "active"),
        )
        if raw.get("id"):
            item.id = raw["id"]
        paraiso._items[item.id] = item

    for raw in data.get("inbox", []):
        if raw.get("status") not in _OPEN_INBOX:
            continue
        text = (raw.get("raw_content") or raw.get("transcript") or "").strip()
        if not text:
            continue
        capture = Capture(text=text, source=raw.get("source", "import"), note=raw.get("note") or "")
        paraiso._captures[capture.id] = capture

    return paraiso
