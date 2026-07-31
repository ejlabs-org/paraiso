"""Whole-install snapshots and two-way sync.

A *snapshot* is one self-contained JSON dict holding every workspace plus the
active pointer. A :class:`Transport` moves that dict somewhere and back; core
ships only :class:`FilesystemTransport` (stdlib, no network). External services
(Dropbox, S3, ...) live in separate add-on packages that implement the same
protocol — see :func:`resolve_transport`.

``sync`` is pull -> merge -> push. Because :func:`~paraiso.merge.merge_workspaces`
is idempotent and convergent, running ``sync`` on several machines against one
shared snapshot brings them all to the same state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

from .core import Paraiso
from .merge import merge_workspaces
from .store import Store
from .util import now, to_iso

SNAPSHOT_VERSION = 1


@dataclass
class MergeReport:
    """What an apply/sync changed, per workspace, for human-readable output."""

    per_workspace: dict = field(default_factory=dict)  # name -> {added, updated, deleted}
    created: list = field(default_factory=list)        # names created locally

    def __str__(self) -> str:
        if not self.per_workspace and not self.created:
            return "Already up to date."
        lines = []
        for name, d in sorted(self.per_workspace.items()):
            tag = " (new)" if name in self.created else ""
            lines.append(
                f"  {name}{tag}: +{d['added']} added, "
                f"~{d['updated']} updated, -{d['deleted']} removed"
            )
        return "Sync complete:\n" + "\n".join(lines)


def build_snapshot(store: Store) -> dict:
    """Bundle every workspace and the active pointer into one dict."""
    return {
        "paraiso_snapshot": SNAPSHOT_VERSION,
        "exported_at": to_iso(now()),
        "active": store.active(),
        "workspaces": [store.load(name).to_dict() for name in store.spaces()],
    }


def _index(p: Paraiso) -> dict:
    """id -> updated_at for every record, so we can diff two workspaces."""
    idx = {}
    for bucket in (p._captures, p._items, p._areas, p._objectives):
        for rid, rec in bucket.items():
            idx[rid] = rec.updated_at
    return idx


def _diff(before: Paraiso, after: Paraiso) -> dict:
    b, a = _index(before), _index(after)
    added = len(set(a) - set(b))
    deleted = len(set(b) - set(a))
    updated = sum(1 for rid in set(a) & set(b) if a[rid] > b[rid])
    return {"added": added, "updated": updated, "deleted": deleted}


def apply_snapshot(store: Store, snapshot: dict) -> MergeReport:
    """Merge a snapshot into ``store`` (creating workspaces as needed)."""
    report = MergeReport()
    for ws in snapshot.get("workspaces", []):
        incoming = Paraiso.from_dict(ws)
        name = incoming.name
        if store.exists(name):
            before = store.load(name)
            merged = merge_workspaces(before, incoming)
            store.save(merged)
            report.per_workspace[name] = _diff(before, merged)
        else:
            store.save(incoming)
            report.created.append(name)
            report.per_workspace[name] = _diff(Paraiso(name), incoming)
    # Adopt the snapshot's active pointer only if we don't already have one.
    active = snapshot.get("active")
    if store.active() is None and active and store.exists(active):
        store.set_active(active)
    return report


class Transport(Protocol):
    """Where a snapshot lives between machines. Implement to add a backend."""

    def pull(self) -> Optional[dict]:
        """Return the remote snapshot, or ``None`` if there isn't one yet."""
        ...

    def push(self, snapshot: dict) -> None:
        """Store ``snapshot`` as the new remote state."""
        ...


class FilesystemTransport:
    """A snapshot stored as a single JSON file (point it at a synced folder)."""

    def __init__(self, path) -> None:
        self.path = Path(path)

    def pull(self) -> Optional[dict]:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def push(self, snapshot: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def sync(store: Store, transport: Transport) -> MergeReport:
    """Pull -> merge -> push. The one operation you run to stay in sync."""
    remote = transport.pull()
    report = apply_snapshot(store, remote) if remote else MergeReport()
    transport.push(build_snapshot(store))
    return report
