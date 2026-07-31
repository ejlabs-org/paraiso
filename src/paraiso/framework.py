"""The PARAISO framework itself, as data.

PARAISO extends Tiago Forte's PARA method (Projects, Areas, Resources, Archive)
with three additions: an **Inbox** for raw capture, **Seeds** for not-yet-ideas,
and **Objectives** for direction. The seven pieces play three different roles:

- **buckets** are the destinations an item can be *filed into*
  (Projects, Resources, Seeds, Archive);
- **inbox** is the staging area every capture lands in before it is filed;
- **organizers** are cross-cutting (Areas group items; Objectives are advanced
  by them). You never file *into* an organizer.

Only the four buckets are represented by :class:`Bucket`; Inbox, Areas, and
Objectives are modelled as their own things in :mod:`paraiso.models`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import InvalidBucketError


class Bucket(str, Enum):
    """A fileable PARAISO destination for an :class:`~paraiso.models.Item`."""

    PROJECT = "project"
    RESOURCE = "resource"
    SEED = "seed"
    ARCHIVE = "archive"

    @property
    def label(self) -> str:
        return {
            "project": "Projects",
            "resource": "Resources",
            "seed": "Seeds",
            "archive": "Archive",
        }[self.value]

    @classmethod
    def coerce(cls, value: "Bucket | str") -> "Bucket":
        """Accept a :class:`Bucket`, its value, or a friendly alias.

        ``"seeds"`` maps to ``SEED`` and ``"projects"``/``"resources"`` to their
        singular buckets, so callers can pass whatever reads naturally.
        """
        if isinstance(value, Bucket):
            return value
        key = str(value).strip().lower()
        aliases = {"seeds": "seed", "projects": "project", "resources": "resource"}
        key = aliases.get(key, key)
        try:
            return cls(key)
        except ValueError as exc:
            allowed = ", ".join(b.value for b in cls)
            raise InvalidBucketError(
                f"{value!r} is not a PARAISO bucket. Choose one of: {allowed}."
            ) from exc


@dataclass(frozen=True)
class Piece:
    """One letter of PARAISO and the role it plays."""

    letter: str
    name: str
    kind: str  # "bucket" | "inbox" | "organizer"
    summary: str


PIECES: tuple[Piece, ...] = (
    Piece("P", "Projects", "bucket", "Things with a finish line."),
    Piece("A", "Areas", "organizer", "Ongoing parts of life you maintain."),
    Piece("R", "Resources", "bucket", "Reference you might want later."),
    Piece("A", "Archive", "bucket", "Done or dormant, and still findable."),
    Piece("I", "Inbox", "inbox", "Where every raw capture lands first."),
    Piece("S", "Seeds", "bucket", "Ideas you let grow, with no pressure."),
    Piece("O", "Objectives", "organizer", "The direction you're moving toward."),
)


def describe() -> str:
    """A short, printable explanation of the framework (used by the CLI)."""
    lines = ["PARAISO — one calm home for everything on your mind.", ""]
    width = max(len(p.name) for p in PIECES)
    for piece in PIECES:
        lines.append(f"  {piece.letter}  {piece.name.ljust(width)}  {piece.summary}")
    lines.append("")
    lines.append("Buckets (file into): Projects, Resources, Seeds, Archive.")
    lines.append("Inbox stages raw capture. Areas and Objectives organize across buckets.")
    return "\n".join(lines)
