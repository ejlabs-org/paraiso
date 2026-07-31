"""Tiny terminal color helpers — 24-bit ANSI, standard library only.

No ``rich``, no ``colorama``. Colors turn themselves off when output isn't a
terminal, when ``NO_COLOR`` is set, or on a ``dumb`` terminal, so piped and CI
output stays clean.
"""

from __future__ import annotations

import os
import sys
from typing import IO, Optional

_RESET = "\033[0m"


def color_enabled(stream: Optional[IO] = None) -> bool:
    """True when it's safe and useful to emit ANSI color to ``stream``."""
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def paint(text: str, hex_color: str, *, bold: bool = False, enabled: bool = True) -> str:
    """Wrap ``text`` in a 24-bit foreground color (a no-op when disabled)."""
    if not enabled:
        return text
    r, g, b = _rgb(hex_color)
    lead = "\033[1m" if bold else ""
    return f"{lead}\033[38;2;{r};{g};{b}m{text}{_RESET}"


def dim(text: str, *, enabled: bool = True) -> str:
    return f"\033[2m{text}{_RESET}" if enabled else text


def prompt(text: str, hex_color: str, *, bold: bool = False, enabled: bool = True) -> str:
    """Colored text for a readline prompt. Wraps the escapes in the zero-width
    markers (``\\001``/``\\002``) readline needs to keep line-editing width math
    correct — otherwise long lines and history recall get corrupted."""
    if not enabled:
        return text
    r, g, b = _rgb(hex_color)
    lead = "\033[1m" if bold else ""
    return f"\001{lead}\033[38;2;{r};{g};{b}m\002{text}\001{_RESET}\002"


def swatch(hex_color: str, *, enabled: bool = True) -> str:
    """A filled dot in the given color — a compact color chip."""
    return paint("●", hex_color, enabled=enabled)
