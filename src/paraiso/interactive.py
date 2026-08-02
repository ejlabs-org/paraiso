"""Guided, keypress-driven flows for the CLI and shell.

This is where sorting stops being "type a command with ids" and becomes "look at
a capture, press a key for the bucket, pick an area from a list." Presentation
layer only — the core library never imports this.

On a real POSIX terminal, bucket choices are single keypresses (no Enter). Menus
and titles are read as lines so they work anywhere, including when stdin is piped
(which is also how the tests drive these flows).
"""

from __future__ import annotations

import select
import sys
from typing import Optional

from . import palette, term
from .core import Paraiso
from .models import Area, Item
from .store import Store

try:  # single-keypress support (POSIX only)
    import termios
    import tty

    _HAS_TERMIOS = True
except ImportError:  # pragma: no cover - Windows / no tty
    _HAS_TERMIOS = False

_BUCKET_KEYS = {"p": "project", "r": "resource", "s": "seed", "a": "archive"}

# Sentinel returned by the pickers when the user chooses to leave a value as-is.
KEEP = object()

# Sentinel returned when the user presses Esc to cancel the current step/flow.
CANCEL = object()


def read_key(prompt: str = "") -> str:
    """Read a single keypress (lower-cased). Falls back to a line off stdin when
    there's no real terminal, so piped input and tests still work."""
    if prompt:
        sys.stdout.write(prompt)
        sys.stdout.flush()
    if not (_HAS_TERMIOS and sys.stdin.isatty()):
        line = sys.stdin.readline()
        return _normalize_key(line.strip()[:1])
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        # Esc alone vs. an arrow/nav escape sequence: if more bytes are waiting,
        # it's a sequence — drain them so they aren't read as a bare Esc.
        seq = _drain(fd) if ch == "\x1b" else ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if seq:  # an escape sequence (arrow, etc.) — not a key any flow acts on
        sys.stdout.write("\n")
        sys.stdout.flush()
        return (ch + seq).lower()
    key = _normalize_key(ch)  # may raise KeyboardInterrupt
    sys.stdout.write("\n" if key in ("", "esc") else ch + "\n")
    sys.stdout.flush()
    return key


def _drain(fd) -> str:
    """Read any bytes already waiting on ``fd`` without blocking (used to slurp
    the tail of an escape sequence right after an initial ``\\x1b``)."""
    out = ""
    while select.select([fd], [], [], 0)[0]:
        out += sys.stdin.read(1)
    return out


def _normalize_key(ch: str) -> str:
    """Map a raw keypress to a logical key.

    In raw terminal mode Enter arrives as a carriage return (``\\r``), so it must
    be normalized to ``""`` — the value every flow treats as "done"/"keep".
    """
    if ch in ("\x03", "\x04"):  # Ctrl-C / Ctrl-D
        raise KeyboardInterrupt
    if ch in ("\r", "\n", ""):  # Enter (or EOF)
        return ""
    if ch == "\x1b":  # Escape — cancel the current step/flow
        return "esc"
    return ch.lower()


def confirm(prompt: str, assume_yes: bool = False) -> bool:
    """Yes/No confirmation. Non-interactive callers must pass ``--yes``."""
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(f"{prompt} (re-run with --yes to confirm)")
        return False
    return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")


# -- pickers ---------------------------------------------------------------


def choose_bucket(color: bool, *, allow_keep: bool = False):
    """Single-key bucket picker. Returns a bucket value, :data:`CANCEL` on Esc/``q``,
    or (when ``allow_keep``) :data:`KEEP` on Enter (leave the bucket unchanged)."""
    hint = "[p] project  [r] resource  [s] seed  [a] archive"
    hint += "   [Enter] keep  [Esc] cancel" if allow_keep else "   [Esc] cancel"
    print("  " + term.dim(hint, enabled=color))
    while True:
        key = read_key("  bucket › ")
        if key in ("q", "esc"):
            return CANCEL
        if key == "":
            if allow_keep:
                return KEEP
            continue  # a bucket is required here — ignore a stray Enter
        if key in _BUCKET_KEYS:
            return _BUCKET_KEYS[key]


def choose_area(
    current: Paraiso,
    color: bool,
    *,
    allow_keep: bool = False,
    current_area_id: Optional[str] = None,
):
    """Numbered Area picker. Returns an area id, ``None`` for no Area, or (when
    ``allow_keep``) :data:`KEEP` to leave it unchanged. Creates Areas inline."""
    areas = current.areas
    if not areas:
        name = input("  area name (blank for none) › ").strip()
        return current.create_area(name).id if name else None
    print("  area:")
    if allow_keep:
        cur = next((a for a in areas if a.id == current_area_id), None)
        print(f"    k) keep current ({cur.name if cur else 'none'})")
    print("    0) none")
    for i, area in enumerate(areas, 1):
        print(f"    {i}) {term.swatch(area.color, enabled=color)} {area.name}")
    print("    n) new area")
    keep_hint = "[k] keep  " if allow_keep else ""
    print("  " + term.dim(f"{keep_hint}[0] none  [n] new  [Esc] cancel", enabled=color))

    def _new_area():
        name = input("  new area name › ").strip()
        return current.create_area(name).id if name else None

    # ≤9 areas fit single-key selection (Esc-cancellable); more need typed input.
    if len(areas) <= 9:
        while True:
            key = read_key("  area › ")
            if key == "esc":
                return CANCEL
            if allow_keep and key == "k":
                return KEEP
            if key in ("", "0"):
                return KEEP if (allow_keep and key == "") else None
            if key == "n":
                return _new_area()
            if key.isdigit() and 1 <= int(key) <= len(areas):
                return areas[int(key) - 1].id
    choice = input("  area › ").strip().lower()
    if choice in ("q", "esc"):
        return CANCEL
    if allow_keep and choice in ("", "k"):
        return KEEP
    if choice in ("", "0"):
        return None
    if choice == "n":
        return _new_area()
    if choice.isdigit() and 1 <= int(choice) <= len(areas):
        return areas[int(choice) - 1].id
    return None


def pick_area(current: Paraiso, color: bool, title: str) -> Optional[Area]:
    """Numbered Area picker. Returns the chosen Area or ``None``."""
    areas = current.areas
    if not areas:
        print("No Areas yet. Add one with `area add <name>`.")
        return None
    print(title)
    for i, area in enumerate(areas, 1):
        count = len(current.items_for_area(area))
        print(f"  {i}) {term.swatch(area.color, enabled=color)} {area.name}  {term.dim(f'({count})', enabled=color)}")
    choice = input("  › ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(areas):
        return areas[int(choice) - 1]
    return None


def pick_area_or_all(current: Paraiso, color: bool, title: str) -> Optional[str]:
    """Pick an Area to filter by. Returns an area id, or ``None`` for "all areas"
    (also the result of cancelling). Single-keypress when there are ≤9 Areas."""
    areas = current.areas
    if not areas:
        print("No Areas yet.")
        return None
    print(title)
    print("    0) all areas")
    for i, area in enumerate(areas, 1):
        count = len(current.items_for_area(area))
        print(f"    {i}) {term.swatch(area.color, enabled=color)} {area.name}  {term.dim(f'({count})', enabled=color)}")
    print("  " + term.dim("[0] all  [Esc] cancel", enabled=color))
    if len(areas) <= 9:
        while True:
            key = read_key("  › ")
            if key in ("esc", "", "0"):
                return None
            if key.isdigit() and 1 <= int(key) <= len(areas):
                return areas[int(key) - 1].id
    choice = input("  › ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(areas):
        return areas[int(choice) - 1].id
    return None


def choose_palette_color(color: bool, *, current_hex: Optional[str] = None) -> Optional[str]:
    """Pick one of the predefined Area colors (never a free-form hex)."""
    print("  color:")
    for i, hexc in enumerate(palette.AREA_COLORS, 1):
        mark = term.dim("  (current)", enabled=color) if hexc == current_hex else ""
        print(f"    {i}) {term.swatch(hexc, enabled=color)} {hexc}{mark}")
    choice = input("  color › ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(palette.AREA_COLORS):
        return palette.AREA_COLORS[int(choice) - 1]
    return None


def pick_item(current: Paraiso, color: bool, title: str) -> Optional[Item]:
    """Numbered picker over all filed items. Returns the chosen Item or ``None``."""
    items = current.items
    if not items:
        print("No items yet.")
        return None
    print(title)
    for i, item in enumerate(items, 1):
        dot = term.paint("●", palette.BUCKET_COLORS[item.bucket.value], enabled=color)
        print(f"  {i}) {dot} {item.title}  {term.dim(item.bucket.label, enabled=color)}")
    choice = input("  › ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        return items[int(choice) - 1]
    return None


def confirm_title(capture_text: str, color: bool):
    """Confirm an item's title with a single keypress. Enter keeps the default
    (the capture's first line), ``e`` opens typed editing, Esc returns
    :data:`CANCEL`. Returns the chosen title string, or :data:`CANCEL`."""
    default = capture_text.splitlines()[0][:120]
    print("  " + term.dim(f"title [{default}]   [Enter] keep · [e] edit · [Esc] cancel", enabled=color))
    while True:
        key = read_key("  › ")
        if key in ("q", "esc"):
            return CANCEL
        if key == "":
            return default
        if key == "e":
            typed = input("  title › ").strip()
            return typed or default


def _action_bar(color: bool) -> str:
    """The per-capture control line in triage. Returns 'file' / 'skip' /
    'discard' / 'quit'."""
    print("  " + term.dim("[Enter] file   [s] skip   [d] discard   [Esc] quit", enabled=color))
    while True:
        key = read_key("  › ")
        if key in ("q", "esc"):
            return "quit"
        if key == "":
            return "file"
        if key == "s":
            return "skip"
        if key == "d":
            return "discard"


def _clear_if_tty() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")


# -- flows -----------------------------------------------------------------


def triage(store: Store, *, color: Optional[bool] = None) -> int:
    """Walk the Inbox one capture at a time: confirm the title, pick an Area,
    choose a bucket. Every step is a keypress; Esc backs out (of the capture
    mid-filing, or of the whole flow at the action bar). The fast, calm way to
    empty an Inbox."""
    current = store.current()
    if current is None:
        print("No active workspace. Create one with `new <name>`.")
        return 0
    color = term.color_enabled() if color is None else color
    inbox = current.inbox
    if not inbox:
        print("Inbox is empty. Nothing to sort.")
        return 0

    _clear_if_tty()
    total = len(inbox)
    filed = 0
    try:
        for idx, capture in enumerate(inbox, 1):
            print(term.dim(f"Sorting {idx}/{total}", enabled=color))
            print(term.paint(f"• {capture.text}", palette.DEFAULT_ACCENT, bold=True, enabled=color))

            action = _action_bar(color)
            if action == "quit":
                break
            if action == "skip":
                print(term.dim("  skipped\n", enabled=color))
                continue
            if action == "discard":
                current.discard(capture)
                store.save(current)
                print(term.dim("  discarded\n", enabled=color))
                continue

            title = confirm_title(capture.text, color)
            if title is CANCEL:
                print(term.dim("  skipped\n", enabled=color))
                continue
            area = choose_area(current, color)
            if area is CANCEL:
                print(term.dim("  skipped\n", enabled=color))
                continue
            bucket = choose_bucket(color)
            if bucket is CANCEL:
                print(term.dim("  skipped\n", enabled=color))
                continue

            item = current.file(capture, bucket, title=title, area=area)
            store.save(current)
            filed += 1
            dest = item.bucket.label + (
                f" · {current.get_area(item.area_id).name}" if item.area_id else ""
            )
            print(term.paint(f"  → {dest}\n", palette.BUCKET_COLORS[bucket], enabled=color))
    except KeyboardInterrupt:
        print("\nStopped.")

    remaining = len(current.inbox)
    print(f"Filed {filed}. {remaining} still in the Inbox.")
    return 0


def move_flow(store: Store, *, color: Optional[bool] = None) -> int:
    """Interactive re-home: pick an item, then change its bucket and/or Area.
    Either can be left as-is by choosing "keep"."""
    current = store.current()
    if current is None:
        print("No active workspace.")
        return 0
    color = term.color_enabled() if color is None else color
    item = pick_item(current, color, "Move which item?")
    if item is None:
        print("Cancelled.")
        return 0

    amap = {a.id: a for a in current.areas}
    cur_area = amap.get(item.area_id)
    now = f"{item.bucket.label}" + (f" · {cur_area.name}" if cur_area else "")
    print("  " + term.dim(f"currently: {now}", enabled=color))

    bucket = choose_bucket(color, allow_keep=True)
    if bucket is CANCEL:
        print("Cancelled.")
        return 0
    if bucket is not KEEP:
        current.move(item, bucket)

    area_choice = choose_area(current, color, allow_keep=True, current_area_id=item.area_id)
    if area_choice is CANCEL:
        print("Cancelled.")
        return 0
    if area_choice is not KEEP:
        current.set_item_area(item, area_choice)

    store.save(current)
    dest = item.bucket.label + (
        f" · {current.get_area(item.area_id).name}" if item.area_id else ""
    )
    print(term.paint(f"Moved '{item.title}' → {dest}.", palette.BUCKET_COLORS[item.bucket.value], enabled=color))
    return 0


def edit_area_flow(store: Store, *, color: Optional[bool] = None, area_id: Optional[str] = None) -> int:
    """Edit an Area: rename, recolor (from the palette), or change tags."""
    current = store.current()
    if current is None:
        print("No active workspace.")
        return 0
    color = term.color_enabled() if color is None else color
    area = current.get_area(area_id) if area_id else pick_area(current, color, "Edit which Area?")
    if area is None:
        print("Cancelled.")
        return 0
    while True:
        tags = f"  {term.dim('[' + ', '.join(area.tags) + ']', enabled=color)}" if area.tags else ""
        print(
            f"\n  {term.swatch(area.color, enabled=color)} "
            f"{term.paint(area.name, area.color, bold=True, enabled=color)}{tags}"
        )
        print("  " + term.dim("[n] rename   [c] color   [t] tags   [Enter] done   [Esc] cancel", enabled=color))
        key = read_key("  edit › ")
        if key in ("", "q", "esc"):
            break
        if key == "n":
            name = input("  new name › ").strip()
            if name:
                current.update_area(area, name=name)
        elif key == "c":
            hexc = choose_palette_color(color, current_hex=area.color)
            if hexc:
                current.update_area(area, color=hexc)
        elif key == "t":
            raw = input("  tags (comma-separated) › ").strip()
            current.update_area(area, tags=[t.strip() for t in raw.split(",") if t.strip()])
    store.save(current)
    print(f"Updated Area {term.swatch(area.color, enabled=color)} {area.name}.")
    return 0


def delete_flow(store: Store, *, color: Optional[bool] = None) -> int:
    """Interactive delete: pick an item from a list, confirm, remove it."""
    current = store.current()
    if current is None:
        print("No active workspace.")
        return 0
    color = term.color_enabled() if color is None else color
    item = pick_item(current, color, "Delete which item?")
    if item is None:
        print("Cancelled.")
        return 0
    if not confirm(f"Delete '{item.title}'? This can't be undone."):
        print("Cancelled.")
        return 0
    current.delete_item(item)
    store.save(current)
    print(f"Deleted '{item.title}'.")
    return 0
