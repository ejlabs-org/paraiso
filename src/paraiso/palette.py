"""The PARAISO color palette.

Seven calm, distinct hues — one per Area — plus a bucket mapping aligned to the
same colors used for each letter in the framework graphic. These are plain hex
strings; how (or whether) they're rendered is a presentation concern handled in
:mod:`paraiso.term`.
"""

from __future__ import annotations

# One color per Area, in a fixed order. New Areas cycle through these.
AREA_COLORS: tuple[str, ...] = (
    "#b0562f",  # rust
    "#bf8a2e",  # gold
    "#5f7d34",  # olive
    "#2f807a",  # teal
    "#3f6db0",  # blue
    "#6a54ad",  # violet
    "#a8486d",  # rose
)

# Neutral accent for anything without its own color.
DEFAULT_ACCENT = "#8f6f52"

# Bucket colors, chosen to match each bucket's letter in the PARAISO graphic
# (Projects = rust, Resources = olive, Seeds = violet, Archive = teal).
BUCKET_COLORS: dict[str, str] = {
    "project": "#b0562f",
    "resource": "#5f7d34",
    "seed": "#6a54ad",
    "archive": "#2f807a",
}

# One color per PARAISO piece, in framework.PIECES order (P A R A I S O).
PIECE_COLORS: tuple[str, ...] = AREA_COLORS


def pick_area_color(index: int) -> str:
    """The color a newly created Area should get, cycling through the palette."""
    return AREA_COLORS[index % len(AREA_COLORS)]


def color_for(key: str) -> str:
    """A stable palette color derived from a string (e.g. a workspace name), so
    the same name always shows in the same color."""
    total = sum(key.encode("utf-8")) if key else 0
    return AREA_COLORS[total % len(AREA_COLORS)]
