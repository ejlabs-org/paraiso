"""Reconcile two PARAISO workspaces into one (record-level last-writer-wins).

The merge is *pure*: it reads two :class:`~paraiso.core.Paraiso` workspaces and
returns a brand-new one, mutating neither input. Reconciliation is by record
``id``:

- a record present on only one side is kept;
- a record present on both sides: the newer ``updated_at`` wins;
- a tombstone (a recorded deletion) removes a record unless a *strictly newer*
  edit out-lives it;
- tombstone maps are unioned, newer timestamp winning on collision.

Because the tie-break is a timestamp, the outcome is order-independent
(``merge(a, b)`` and ``merge(b, a)`` converge) and idempotent.
"""

from __future__ import annotations

from .core import Paraiso
from .util import from_iso, now


def _pick_newer(local, incoming):
    """Return whichever of two same-id records has the newer ``updated_at``."""
    if local is None:
        return incoming
    if incoming is None:
        return local
    return incoming if incoming.updated_at >= local.updated_at else local


def _merge_bucket(local: dict, incoming: dict, tombstones: dict) -> dict:
    """Union two id->record maps, LWW on collisions, then apply tombstones."""
    merged: dict = {}
    for rid in set(local) | set(incoming):
        record = _pick_newer(local.get(rid), incoming.get(rid))
        ts = tombstones.get(rid)
        if ts is not None:
            deleted_at = from_iso(ts)
            # A strictly-newer edit out-lives the delete; otherwise drop it.
            if record.updated_at <= deleted_at:
                continue
        merged[rid] = record
    return merged


def _merge_tombstones(local: dict, incoming: dict) -> dict:
    merged = dict(local)
    for rid, ts in incoming.items():
        current = merged.get(rid)
        if current is None or from_iso(ts) > from_iso(current):
            merged[rid] = ts
    return merged


def merge_workspaces(local: Paraiso, incoming: Paraiso) -> Paraiso:
    """Merge ``incoming`` into ``local`` and return a new workspace."""
    out = Paraiso(local.name, local.description)
    out.created_at = min(local.created_at, incoming.created_at)
    out.updated_at = now()
    tombs = _merge_tombstones(local._tombstones, incoming._tombstones)
    out._captures = _merge_bucket(local._captures, incoming._captures, tombs)
    out._items = _merge_bucket(local._items, incoming._items, tombs)
    out._areas = _merge_bucket(local._areas, incoming._areas, tombs)
    out._objectives = _merge_bucket(local._objectives, incoming._objectives, tombs)
    out._tombstones = tombs
    return out
