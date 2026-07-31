"""The classification seam — where AI plugs in later.

PARAISO's rule is that **the user decides**. A classifier only ever *suggests*;
nothing is filed until a person accepts. Today the default
:class:`ManualClassifier` suggests nothing at all. Tomorrow you bring your own:
implement :class:`Classifier` around whatever model you like (OpenAI, Anthropic,
a local LLM, a rules engine) and hand it to :class:`~paraiso.core.Paraiso`.

The contract is deliberately tiny and dependency-free:

    class MyLLM:
        def classify(self, capture, *, areas, objectives):
            ...
            return Suggestion(bucket=Bucket.PROJECT, area_id=..., rationale="...")

A classifier must never invent Areas or Objectives; it may only reference ones
passed to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from .framework import Bucket
from .models import Area, Capture, Objective


@dataclass
class Suggestion:
    """A proposed home for a capture. Advisory only — a person confirms it."""

    bucket: Bucket
    title: Optional[str] = None
    summary: str = ""
    area_id: Optional[str] = None
    objective_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    rationale: str = ""
    confidence: Optional[float] = None


@runtime_checkable
class Classifier(Protocol):
    """Anything that can propose where a capture belongs.

    Implementations receive the capture plus the workspace's current Areas and
    Objectives (for grounding) and return a :class:`Suggestion`, or ``None`` to
    abstain.
    """

    def classify(
        self,
        capture: Capture,
        *,
        areas: list[Area],
        objectives: list[Objective],
    ) -> Optional[Suggestion]:
        ...


class ManualClassifier:
    """The default: suggests nothing, because the user decides everything.

    This keeps the workspace fully functional with no AI configured, and marks
    the exact place a real classifier slots in.
    """

    def classify(
        self,
        capture: Capture,
        *,
        areas: list[Area],
        objectives: list[Objective],
    ) -> Optional[Suggestion]:
        return None


class KeywordClassifier:
    """A tiny, offline example classifier — no AI, no network.

    It matches an Area when one of its tags (or a word from its name) appears in
    the capture text, and proposes filing the item as a Seed (the calmest,
    lowest-pressure bucket) inside that Area. It exists to show the shape of a
    real classifier and to make the pipeline testable without a model.
    """

    def __init__(self, default_bucket: Bucket = Bucket.SEED) -> None:
        self.default_bucket = default_bucket

    def classify(
        self,
        capture: Capture,
        *,
        areas: list[Area],
        objectives: list[Objective],
    ) -> Optional[Suggestion]:
        words = {w.strip(".,!?:;\"'()").lower() for w in capture.text.split()}
        for area in areas:
            signals = {t.lower() for t in area.tags} | {
                part.lower() for part in area.name.split()
            }
            hit = words & signals
            if hit:
                return Suggestion(
                    bucket=self.default_bucket,
                    area_id=area.id,
                    title=capture.text.splitlines()[0][:80],
                    rationale=f"Matched Area '{area.name}' on {sorted(hit)}.",
                    confidence=0.5,
                )
        return None
