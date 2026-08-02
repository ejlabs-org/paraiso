"""PARAISO — one calm home for everything on your mind.

An open, dependency-free Python foundation for PARAISO-style capture and
organization (Projects, Areas, Resources, Archive, Inbox, Seeds, Objectives).
The framework extends Tiago Forte's PARA. This package is not tied to any app;
it is meant as a shared base other tools can build on.

Quick start::

    import paraiso

    p = paraiso.Paraiso("Personal")
    writing = p.create_area("Writing", tags=["essay"])
    c = p.capture("someday: write an essay about calm systems")
    p.file(c, "seed", title="Essay: calm systems", area=writing)

The user always decides where a capture goes. AI is an optional, bring-your-own
layer: implement :class:`Classifier` and pass it to :class:`Paraiso` when you
want suggestions.
"""

from __future__ import annotations

from ._version import __version__
from .classifier import (
    Classifier,
    KeywordClassifier,
    ManualClassifier,
    Suggestion,
)
from .cli import main
from .core import Paraiso
from .errors import (
    AlreadyProcessedError,
    AmbiguousIdError,
    AreaNotFoundError,
    CaptureNotFoundError,
    InvalidBucketError,
    ItemNotFoundError,
    NotFoundError,
    ObjectiveNotFoundError,
    ParaisoError,
    SpaceExistsError,
    SpaceNotFoundError,
)
from .framework import PIECES, Bucket, Piece, describe
from .merge import merge_workspaces
from .models import Area, Capture, Item, Objective
from .shell import ParaisoShell
from .store import Store
# NB: import names from .sync but NOT the `sync` function itself — binding a
# top-level name `sync` would shadow the `paraiso.sync` submodule. The
# orchestrator stays reachable as `paraiso.sync.sync`.
from .sync import (
    FilesystemTransport,
    MergeReport,
    Transport,
    apply_snapshot,
    build_snapshot,
)

__all__ = [
    "__version__",
    # framework
    "Bucket",
    "Piece",
    "PIECES",
    "describe",
    # models
    "Area",
    "Capture",
    "Item",
    "Objective",
    # core + storage
    "Paraiso",
    "Store",
    # sync
    "merge_workspaces",
    "build_snapshot",
    "apply_snapshot",
    "Transport",
    "FilesystemTransport",
    "MergeReport",
    # interactive shell
    "ParaisoShell",
    # classification (bring-your-own AI)
    "Classifier",
    "Suggestion",
    "ManualClassifier",
    "KeywordClassifier",
    # errors
    "ParaisoError",
    "NotFoundError",
    "CaptureNotFoundError",
    "ItemNotFoundError",
    "AreaNotFoundError",
    "ObjectiveNotFoundError",
    "InvalidBucketError",
    "AmbiguousIdError",
    "AlreadyProcessedError",
    "SpaceExistsError",
    "SpaceNotFoundError",
    # cli
    "main",
]
