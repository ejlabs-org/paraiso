"""The :class:`Paraiso` workspace: one calm home for capture and structure.

A workspace holds an Inbox of raw captures plus filed Items, and the Areas and
Objectives that organize them. The core loop is:

    p = Paraiso("Personal")
    c = p.capture("call the dentist")     # lands in the Inbox, unsorted
    p.file(c, "project", title="Book dentist appointment")  # you decide

Everything a person can do is a method here; persistence and multiple
workspaces live in :mod:`paraiso.store`.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from . import palette
from .classifier import Classifier, ManualClassifier, Suggestion
from .errors import (
    AlreadyProcessedError,
    AmbiguousIdError,
    AreaNotFoundError,
    CaptureNotFoundError,
    ItemNotFoundError,
    ObjectiveNotFoundError,
)
from .framework import Bucket
from .models import Area, Capture, Item, Objective
from .util import from_iso, now, to_iso

# Accept an entity or its id anywhere one is expected.
AreaRef = Union[Area, str, None]
ObjectiveRef = Union[Objective, str, None]
CaptureRef = Union[Capture, str]


def _match_id(mapping: dict, ref: str) -> Optional[str]:
    """Resolve ``ref`` to a full id in ``mapping``: an exact match, else a unique
    prefix (git-style). Returns ``None`` when nothing matches; raises
    :class:`AmbiguousIdError` when a prefix matches more than one id."""
    if ref in mapping:
        return ref
    hits = [k for k in mapping if k.startswith(ref)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise AmbiguousIdError(
            f"Id {ref!r} matches {len(hits)} entities; use more characters."
        )
    return None


def _show(ref) -> str:
    """The id to name in an error message, whether given an entity or an id."""
    return getattr(ref, "id", ref)


class Paraiso:
    """A single PARAISO workspace."""

    def __init__(
        self,
        name: str,
        description: str = "",
        *,
        classifier: Optional[Classifier] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.classifier: Classifier = classifier or ManualClassifier()
        self._captures: dict[str, Capture] = {}
        self._items: dict[str, Item] = {}
        self._areas: dict[str, Area] = {}
        self._objectives: dict[str, Objective] = {}
        self._tombstones: dict[str, str] = {}
        self.created_at = now()
        self.updated_at = now()

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"Paraiso(name={self.name!r}, inbox={len(self.inbox)}, "
            f"items={len(self._items)}, areas={len(self._areas)}, "
            f"objectives={len(self._objectives)})"
        )

    # -- Inbox / capture ---------------------------------------------------

    def capture(self, text: str, *, source: str = "manual", note: str = "") -> Capture:
        """Drop a raw thought into the Inbox. No decision required."""
        text = text.strip()
        if not text:
            raise ValueError("Capture text cannot be empty.")
        capture = Capture(text=text, source=source, note=note)
        self._captures[capture.id] = capture
        self._touch()
        return capture

    # ``add`` reads naturally as an alias for capturing into the inbox.
    add = capture

    @property
    def inbox(self) -> list[Capture]:
        """Captures still waiting to be sorted, oldest first."""
        return sorted(
            (c for c in self._captures.values() if not c.processed),
            key=lambda c: c.created_at,
        )

    @property
    def captures(self) -> list[Capture]:
        return list(self._captures.values())

    def discard(self, capture: CaptureRef) -> None:
        """Throw a capture away without filing it."""
        c = self._resolve_capture(capture)
        del self._captures[c.id]
        self._tombstone(c.id)
        self._touch()

    # -- Filing (the user decides) ----------------------------------------

    def file(
        self,
        capture: CaptureRef,
        bucket: Union[Bucket, str],
        *,
        title: Optional[str] = None,
        summary: str = "",
        content: str = "",
        area: AreaRef = None,
        objective: ObjectiveRef = None,
        tags: Optional[list[str]] = None,
    ) -> Item:
        """Turn a capture into a filed :class:`Item`. Closes the capture."""
        c = self._resolve_capture(capture)
        if c.processed:
            raise AlreadyProcessedError(f"Capture {c.id} is already filed.")
        item = self._build_item(
            title=title or c.text.splitlines()[0][:120],
            bucket=bucket,
            summary=summary,
            content=content or c.text,
            area=area,
            objective=objective,
            tags=tags,
            source_capture_id=c.id,
        )
        c.processed = True
        c.item_id = item.id
        c.updated_at = now()
        self._touch()
        return item

    def add_item(
        self,
        title: str,
        bucket: Union[Bucket, str],
        *,
        summary: str = "",
        content: str = "",
        area: AreaRef = None,
        objective: ObjectiveRef = None,
        tags: Optional[list[str]] = None,
    ) -> Item:
        """Create a filed item directly, without going through the Inbox."""
        item = self._build_item(
            title=title,
            bucket=bucket,
            summary=summary,
            content=content,
            area=area,
            objective=objective,
            tags=tags,
            source_capture_id=None,
        )
        self._touch()
        return item

    def _build_item(
        self,
        *,
        title: str,
        bucket: Union[Bucket, str],
        summary: str,
        content: str,
        area: AreaRef,
        objective: ObjectiveRef,
        tags: Optional[list[str]],
        source_capture_id: Optional[str],
    ) -> Item:
        item = Item(
            title=title,
            bucket=Bucket.coerce(bucket),
            summary=summary,
            content=content,
            area_id=self._area_id(area),
            objective_id=self._objective_id(objective),
            tags=list(tags or []),
            source_capture_id=source_capture_id,
        )
        self._items[item.id] = item
        return item

    def move(self, item: Union[Item, str], bucket: Union[Bucket, str]) -> Item:
        """Reclassify an item into a different bucket."""
        it = self._resolve_item(item)
        it.bucket = Bucket.coerce(bucket)
        it.updated_at = now()
        self._touch()
        return it

    def set_item_area(self, item: Union[Item, str], area: AreaRef) -> Item:
        """Attach an item to an Area, or pass ``None`` to detach it."""
        it = self._resolve_item(item)
        it.area_id = self._area_id(area)
        it.updated_at = now()
        self._touch()
        return it

    def update_item(
        self,
        item: Union[Item, str],
        *,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> Item:
        """Edit a filed item's text fields. Only the arguments you pass are
        changed; the rest are left as-is. Bucket and Area have their own methods
        (:meth:`move`, :meth:`set_item_area`)."""
        it = self._resolve_item(item)
        if title is not None:
            it.title = title
        if summary is not None:
            it.summary = summary
        if content is not None:
            it.content = content
        if tags is not None:
            it.tags = list(tags)
        it.updated_at = now()
        self._touch()
        return it

    # -- Deleting ----------------------------------------------------------

    def delete_item(self, item: Union[Item, str]) -> None:
        """Permanently delete a filed item (the only destructive action here)."""
        it = self._resolve_item(item)
        del self._items[it.id]
        for capture in self._captures.values():
            if capture.item_id == it.id:
                capture.item_id = None  # its lineage pointer now dangles; clear it
                capture.updated_at = now()
        self._tombstone(it.id)
        self._touch()

    def delete_area(self, area: AreaRef) -> None:
        """Delete an Area but keep its content: items and objectives detach.

        This mirrors PARAISO's rule that deleting an Area never destroys what
        was filed under it — those items simply lose their Area.
        """
        aid = self._area_id(area)
        del self._areas[aid]
        for it in self._items.values():
            if it.area_id == aid:
                it.area_id = None
                it.updated_at = now()
        for obj in self._objectives.values():
            if obj.area_id == aid:
                obj.area_id = None
                obj.updated_at = now()
        self._tombstone(aid)
        self._touch()

    # -- Areas & Objectives (human-created) --------------------------------

    def create_area(
        self,
        name: str,
        *,
        description: str = "",
        tags: Optional[list[str]] = None,
        color: Optional[str] = None,
    ) -> Area:
        # Auto-assign a distinct palette color (cycling), unless one is given.
        chosen = color or palette.pick_area_color(len(self._areas))
        area = Area(
            name=name, description=description, color=chosen, tags=list(tags or [])
        )
        self._areas[area.id] = area
        self._touch()
        return area

    def update_area(
        self,
        area: AreaRef,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Area:
        """Edit an existing Area's name, description, color, or tags."""
        a = self._areas[self._area_id(area)]
        if name is not None:
            a.name = name
        if description is not None:
            a.description = description
        if color is not None:
            a.color = color
        if tags is not None:
            a.tags = list(tags)
        a.updated_at = now()
        self._touch()
        return a

    def create_objective(
        self, title: str, *, description: str = "", area: AreaRef = None
    ) -> Objective:
        objective = Objective(
            title=title, description=description, area_id=self._area_id(area)
        )
        self._objectives[objective.id] = objective
        self._touch()
        return objective

    # -- Classification (AI later; abstains by default) --------------------

    def suggest(
        self, capture: CaptureRef, *, classifier: Optional[Classifier] = None
    ) -> Optional[Suggestion]:
        """Ask a classifier where a capture might belong. Advisory only."""
        c = self._resolve_capture(capture)
        clf = classifier or self.classifier
        return clf.classify(
            c, areas=self.areas, objectives=self.objectives
        )

    def accept(self, capture: CaptureRef, suggestion: Suggestion) -> Item:
        """File a capture using a suggestion the user has chosen to accept."""
        c = self._resolve_capture(capture)
        return self.file(
            c,
            suggestion.bucket,
            title=suggestion.title,
            summary=suggestion.summary,
            area=suggestion.area_id,
            objective=suggestion.objective_id,
            tags=suggestion.tags,
        )

    # -- Queries -----------------------------------------------------------

    @property
    def items(self) -> list[Item]:
        return list(self._items.values())

    @property
    def areas(self) -> list[Area]:
        return list(self._areas.values())

    @property
    def objectives(self) -> list[Objective]:
        return list(self._objectives.values())

    @property
    def tombstones(self) -> dict[str, str]:
        """Ids of deleted records → ISO deletion timestamp (for sync)."""
        return dict(self._tombstones)

    def items_in(self, bucket: Union[Bucket, str]) -> list[Item]:
        target = Bucket.coerce(bucket)
        return [i for i in self._items.values() if i.bucket is target]

    def items_for_area(self, area: AreaRef) -> list[Item]:
        aid = self._area_id(area)
        return [i for i in self._items.values() if i.area_id == aid]

    def items_for_objective(self, objective: ObjectiveRef) -> list[Item]:
        oid = self._objective_id(objective)
        return [i for i in self._items.values() if i.objective_id == oid]

    def get_capture(self, capture_id: str) -> Capture:
        return self._resolve_capture(capture_id)

    def get_item(self, item_id: str) -> Item:
        return self._resolve_item(item_id)

    def get_area(self, area_id: str) -> Area:
        aid = _match_id(self._areas, area_id)
        if aid is None:
            raise AreaNotFoundError(f"No area with id {area_id!r}.")
        return self._areas[aid]

    def get_objective(self, objective_id: str) -> Objective:
        oid = _match_id(self._objectives, objective_id)
        if oid is None:
            raise ObjectiveNotFoundError(f"No objective with id {objective_id!r}.")
        return self._objectives[oid]

    def summary(self) -> dict[str, Any]:
        """Counts for a quick overview (used by the CLI)."""
        return {
            "name": self.name,
            "inbox": len(self.inbox),
            "items": len(self._items),
            "buckets": {b.label: len(self.items_in(b)) for b in Bucket},
            "areas": len(self._areas),
            "objectives": len(self._objectives),
        }

    # -- Serialization -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "name": self.name,
            "description": self.description,
            "created_at": to_iso(self.created_at),
            "updated_at": to_iso(self.updated_at),
            "captures": [c.to_dict() for c in self._captures.values()],
            "items": [i.to_dict() for i in self._items.values()],
            "areas": [a.to_dict() for a in self._areas.values()],
            "objectives": [o.to_dict() for o in self._objectives.values()],
            "tombstones": dict(self._tombstones),
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], *, classifier: Optional[Classifier] = None
    ) -> "Paraiso":
        p = cls(data["name"], data.get("description", ""), classifier=classifier)
        p.created_at = from_iso(data.get("created_at")) or now()
        p.updated_at = from_iso(data.get("updated_at")) or now()
        p._captures = {c["id"]: Capture.from_dict(c) for c in data.get("captures", [])}
        p._items = {i["id"]: Item.from_dict(i) for i in data.get("items", [])}
        p._areas = {a["id"]: Area.from_dict(a) for a in data.get("areas", [])}
        p._objectives = {
            o["id"]: Objective.from_dict(o) for o in data.get("objectives", [])
        }
        p._tombstones = dict(data.get("tombstones", {}))
        return p

    # -- Internals ---------------------------------------------------------

    def _touch(self) -> None:
        self.updated_at = now()

    def _tombstone(self, entity_id: str) -> None:
        self._tombstones[entity_id] = to_iso(now())

    def _resolve_capture(self, ref: CaptureRef) -> Capture:
        cid = ref.id if isinstance(ref, Capture) else _match_id(self._captures, ref)
        if cid is None or cid not in self._captures:
            raise CaptureNotFoundError(f"No capture with id {_show(ref)!r}.")
        return self._captures[cid]

    def _resolve_item(self, ref: Union[Item, str]) -> Item:
        iid = ref.id if isinstance(ref, Item) else _match_id(self._items, ref)
        if iid is None or iid not in self._items:
            raise ItemNotFoundError(f"No item with id {_show(ref)!r}.")
        return self._items[iid]

    def _area_id(self, ref: AreaRef) -> Optional[str]:
        if ref is None:
            return None
        aid = ref.id if isinstance(ref, Area) else _match_id(self._areas, ref)
        if aid is None or aid not in self._areas:
            raise AreaNotFoundError(f"No area with id {_show(ref)!r}.")
        return aid

    def _objective_id(self, ref: ObjectiveRef) -> Optional[str]:
        if ref is None:
            return None
        oid = ref.id if isinstance(ref, Objective) else _match_id(self._objectives, ref)
        if oid is None or oid not in self._objectives:
            raise ObjectiveNotFoundError(f"No objective with id {_show(ref)!r}.")
        return oid
