"""A small, dependency-free command line for PARAISO.

    paraiso new personal          # create + switch to a workspace
    paraiso spaces                # list workspaces (active one starred)
    paraiso use work              # switch active workspace
    paraiso capture "buy mulch"   # drop a thought in the Inbox
    paraiso inbox                 # see what's waiting to be sorted
    paraiso area add Health --tags fitness,sleep
    paraiso file cap_ab12 --bucket project --title "Book dentist"
    paraiso projects              # browse a bucket (also: resources/seeds/archive)
    paraiso tree                  # colorful overview of everything
    paraiso framework             # what PARAISO stands for

Persistence lives in ~/.paraiso (override with $PARAISO_HOME).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import framework, interactive, palette, term
from ._version import __version__
from .core import Paraiso
from .errors import ParaisoError
from .framework import Bucket
from .models import Area, Item
from .store import Store
from .util import short_id


# Sentinel: `-a` given with no value means "prompt me for an Area".
_PROMPT_AREA = "\x00prompt-area"


def _tags(value: Optional[str]) -> list[str]:
    return [t.strip() for t in (value or "").split(",") if t.strip()]


def _require_current(store: Store) -> Paraiso:
    current = store.current()
    if current is None:
        raise ParaisoError(
            "No active workspace. Create one with `paraiso new <name>`."
        )
    return current


# -- rendering helpers (color turns itself off for pipes/CI) ---------------


def _area_map(current: Paraiso) -> dict[str, Area]:
    return {a.id: a for a in current.areas}


def _by_area(amap: dict[str, Area]):
    """Shared Browse ordering: group items by Area name (area-less items last),
    then by title. Used by every browse view so they read the same way."""
    def key(item: Item):
        area = amap.get(item.area_id) if item.area_id else None
        if area is None:
            return (1, "", item.title.lower())
        return (0, area.name.lower(), item.title.lower())
    return key


def _fmt_item(item: Item, amap: dict[str, Area], color: bool, *, dot: bool = True) -> str:
    parts = []
    if dot:
        parts.append(term.paint("●", palette.BUCKET_COLORS[item.bucket.value], enabled=color))
    parts.append(term.dim(short_id(item.id), enabled=color))
    parts.append(item.title)
    area = amap.get(item.area_id) if item.area_id else None
    if area is not None:
        parts.append(f"{term.swatch(area.color, enabled=color)} {area.name}")
    if item.tags:
        parts.append(term.dim(" ".join(f"#{t}" for t in item.tags), enabled=color))
    return "  ".join(parts)


def _clear_if_tty() -> None:
    """Clear the screen for full "page" views — but only on a real terminal."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")


def _pick_or_get_area(current: Paraiso, area_id, color: bool, prompt: str):
    if area_id:
        return current.get_area(area_id)  # raises AreaNotFoundError → 1
    return interactive.pick_area(current, color, prompt)


def _area_detail(current: Paraiso, area: Area, color: bool) -> None:
    """A single Area's page: its color, tags, items by bucket, and objectives."""
    _clear_if_tty()
    print(term.paint(f"● {area.name}", area.color, bold=True, enabled=color))
    if area.description:
        print("  " + area.description)
    if area.tags:
        print("  " + term.dim(" ".join(f"#{t}" for t in area.tags), enabled=color))
    print()
    items = current.items_for_area(area)
    shown = False
    for bucket in Bucket:
        b_items = [i for i in items if i.bucket is bucket]
        if not b_items:
            continue
        shown = True
        print(term.paint(f"{bucket.label} ({len(b_items)})", palette.BUCKET_COLORS[bucket.value], bold=True, enabled=color))
        for item in sorted(b_items, key=lambda i: i.title.lower()):
            print(f"  {item.title}")
    objectives = [o for o in current.objectives if o.area_id == area.id]
    if objectives:
        shown = True
        print(term.paint("Objectives", palette.DEFAULT_ACCENT, bold=True, enabled=color))
        for obj in objectives:
            print(f"  {obj.title}")
    if not shown:
        print(term.dim("  Nothing filed here yet.", enabled=color))


def _cmd_framework(args, store: Store) -> int:
    color = term.color_enabled()
    if not color:
        print(framework.describe())
        return 0
    print("PARAISO — one calm home for everything on your mind.\n")
    width = max(len(p.name) for p in framework.PIECES)
    for piece, hexc in zip(framework.PIECES, palette.PIECE_COLORS):
        letter = term.paint(piece.letter, hexc, bold=True, enabled=color)
        name = term.paint(piece.name.ljust(width), hexc, enabled=color)
        print(f"  {letter}  {name}  {term.dim(piece.summary, enabled=color)}")
    return 0


def _cmd_spaces(args, store: Store) -> int:
    names = store.spaces()
    if not names:
        print("No workspaces yet. Create one with `paraiso new <name>`.")
        return 0
    active = store.active()
    for name in names:
        marker = "*" if name == active else " "
        print(f"{marker} {name}")
    return 0


def _cmd_new(args, store: Store) -> int:
    store.create(args.name, args.description or "")
    print(f"Created and switched to workspace {args.name!r}.")
    return 0


def _cmd_use(args, store: Store) -> int:
    store.use(args.name)
    print(f"Switched to workspace {args.name!r}.")
    return 0


def _cmd_rename(args, store: Store) -> int:
    # `rename NEW` renames the active workspace; `rename OLD NEW` renames OLD.
    if args.name2 is not None:
        old, new = args.name1, args.name2
    else:
        old, new = store.active(), args.name1
    if not old:
        raise ParaisoError("No active workspace. Try `rename <old> <new>`.")
    store.rename(old, new)
    print(f"Renamed workspace {old!r} → {new!r}.")
    return 0


def _cmd_capture(args, store: Store) -> int:
    current = _require_current(store)
    capture = current.capture(" ".join(args.text))
    store.save(current)
    print(f"Captured {capture.id}: {capture.text}")
    return 0


def _cmd_inbox(args, store: Store) -> int:
    current = _require_current(store)
    inbox = current.inbox
    if not inbox:
        print("Inbox is empty. Nothing to sort.")
        return 0
    color = term.color_enabled()
    for capture in inbox:
        print(f"{term.dim(short_id(capture.id), enabled=color)}  {capture.text}")
    return 0


def _cmd_file(args, store: Store) -> int:
    current = _require_current(store)
    item = current.file(
        args.capture_id,
        args.bucket,
        title=args.title,
        summary=args.summary or "",
        area=args.area,
        objective=args.objective,
        tags=_tags(args.tags),
    )
    store.save(current)
    print(f"Filed {item.id} into {item.bucket.label}: {item.title}")
    return 0


def _cmd_area(args, store: Store) -> int:
    current = _require_current(store)
    color = term.color_enabled()
    action = args.area_action
    if action == "add":
        area = current.create_area(args.name, tags=_tags(args.tags))
        store.save(current)
        print(f"Created Area {term.swatch(area.color, enabled=color)} {area.id}: {area.name}")
    elif action == "show":
        area = _pick_or_get_area(current, getattr(args, "id", None), color, "Explore which Area?")
        if area is not None:
            _area_detail(current, area, color)
    elif action == "edit":
        return interactive.edit_area_flow(store, area_id=getattr(args, "id", None))
    else:  # list — numbered, with item counts
        areas = current.areas
        if not areas:
            print("No Areas yet. Add one with `area add <name>`.")
        for i, area in enumerate(areas, 1):
            count = len(current.items_for_area(area))
            print(
                f"  {i}) {term.swatch(area.color, enabled=color)} {area.name}"
                f"  {term.dim(f'({count})', enabled=color)}  {term.dim(short_id(area.id), enabled=color)}"
            )
    return 0


def _cmd_objective(args, store: Store) -> int:
    current = _require_current(store)
    color = term.color_enabled()
    if args.objective_action == "add":
        obj = current.create_objective(args.title, area=args.area)
        store.save(current)
        print(f"Created Objective {obj.id}: {obj.title}")
    else:  # list
        objectives = current.objectives
        if not objectives:
            print("No Objectives yet.")
        amap = _area_map(current)
        for obj in objectives:
            advancing = len(current.items_for_objective(obj))
            area = amap.get(obj.area_id) if obj.area_id else None
            area_str = f"  {term.swatch(area.color, enabled=color)} {area.name}" if area else ""
            print(
                f"{term.dim(short_id(obj.id), enabled=color)}  {obj.title}"
                f"  {term.dim(f'({advancing} advancing · {obj.status})', enabled=color)}{area_str}"
            )
    return 0


def _cmd_items(args, store: Store) -> int:
    """List filed items. `--bucket`/`--area`/`--objective` narrow it; the
    `projects`/`resources`/`seeds`/`archive` shortcuts preset the bucket."""
    current = _require_current(store)
    color = term.color_enabled()
    bucket = getattr(args, "bucket", None)
    area = getattr(args, "area", None)
    objective = getattr(args, "objective", None)

    # Bare `-a` → prompt for an Area (or "all"); a value → resolve id/prefix.
    if area == _PROMPT_AREA:
        label = Bucket.coerce(bucket).label if bucket else "items"
        area = interactive.pick_area_or_all(current, color, f"Show {label} in which Area?")
    if area:
        area = current.get_area(area).id  # resolve id/prefix (raises if unknown)

    items = current.items
    if bucket:
        items = [i for i in items if i.bucket is Bucket.coerce(bucket)]
    if area:
        items = [i for i in items if i.area_id == area]
    if objective:
        items = [i for i in items if i.objective_id == objective]

    if bucket:
        label = Bucket.coerce(bucket).label
        print(term.paint(f"{label} ({len(items)})", palette.BUCKET_COLORS[Bucket.coerce(bucket).value], bold=True, enabled=color))
    if not items:
        print("  Nothing here yet." if bucket else "No items match." )
        return 0
    amap = _area_map(current)
    for item in sorted(items, key=_by_area(amap)):
        indent = "  " if bucket else ""
        # In a single-bucket view the header already shows the color.
        print(indent + _fmt_item(item, amap, color, dot=not bucket))
    return 0


def _cmd_tree(args, store: Store) -> int:
    """A colorful overview: each bucket with its items, then Inbox, Areas, Objectives."""
    current = _require_current(store)
    _clear_if_tty()
    color = term.color_enabled()
    amap = _area_map(current)

    bar = "=" * (len(current.name) + 4)
    print(term.paint(bar, palette.DEFAULT_ACCENT, enabled=color))
    print(term.paint(f"  {current.name}", palette.DEFAULT_ACCENT, bold=True, enabled=color))
    print(term.paint(bar, palette.DEFAULT_ACCENT, enabled=color))
    for bucket in Bucket:
        items = current.items_in(bucket)
        header = term.paint(f"{bucket.label} ({len(items)})", palette.BUCKET_COLORS[bucket.value], bold=True, enabled=color)
        print(header)
        for item in sorted(items, key=_by_area(amap)):
            area = amap.get(item.area_id) if item.area_id else None
            area_str = f"   {term.swatch(area.color, enabled=color)} {area.name}" if area else ""
            print(f"  {item.title}{area_str}")

    inbox = current.inbox
    print(term.paint(f"Inbox ({len(inbox)})", palette.DEFAULT_ACCENT, bold=True, enabled=color))
    for capture in inbox:
        print(f"  {capture.text}")

    if current.areas:
        print(term.paint("Areas", palette.DEFAULT_ACCENT, bold=True, enabled=color))
        for area in current.areas:
            count = len(current.items_for_area(area))
            print(f"  {term.swatch(area.color, enabled=color)} {area.name}  {term.dim(f'({count})', enabled=color)}")

    if current.objectives:
        print(term.paint("Objectives", palette.DEFAULT_ACCENT, bold=True, enabled=color))
        for obj in current.objectives:
            advancing = len(current.items_for_objective(obj))
            print(f"  {obj.title}  {term.dim(f'({advancing} advancing)', enabled=color)}")
    return 0


def _cmd_sort(args, store: Store) -> int:
    _require_current(store)
    return interactive.triage(store)


def _cmd_move(args, store: Store) -> int:
    current = _require_current(store)
    if args.item_id and args.bucket:
        item = current.move(args.item_id, args.bucket)
        if args.area is not None:
            current.set_item_area(item, args.area or None)
        store.save(current)
        color = term.color_enabled()
        print(term.paint(f"Moved '{item.title}' → {item.bucket.label}.", palette.BUCKET_COLORS[item.bucket.value], enabled=color))
        return 0
    # Not enough given — guide the user through it.
    return interactive.move_flow(store)


def _cmd_delete(args, store: Store) -> int:
    current = _require_current(store)
    if not args.id:
        return interactive.delete_flow(store)
    if args.id.startswith("area_"):
        area = current.get_area(args.id)
        if not interactive.confirm(
            f"Delete Area '{area.name}'? Its items are kept and detached.", args.yes
        ):
            print("Cancelled.")
            return 0
        current.delete_area(area)
        store.save(current)
        print(f"Deleted Area '{area.name}'. Its items were detached.")
    else:
        item = current.get_item(args.id)
        if not interactive.confirm(
            f"Delete item '{item.title}'? This can't be undone.", args.yes
        ):
            print("Cancelled.")
            return 0
        current.delete_item(item)
        store.save(current)
        print(f"Deleted item '{item.title}'.")
    return 0


def _cmd_import(args, store: Store) -> int:
    from . import portability

    try:
        paraiso = portability.load_export(args.file, name=args.name)
    except (OSError, ValueError) as exc:  # missing file / bad JSON
        raise ParaisoError(f"Couldn't read {args.file!r}: {exc}") from exc
    name = paraiso.name
    if store.exists(name) and not args.force:
        raise ParaisoError(f"Workspace {name!r} already exists. Use --name or --force.")
    store.save(paraiso)
    store.set_active(name)
    s = paraiso.summary()
    print(
        f"Imported into workspace {name!r}: {s['items']} items, "
        f"{s['areas']} areas, {s['objectives']} objectives, {s['inbox']} in Inbox."
    )
    return 0


def _cmd_export(args, store: Store) -> int:
    import json

    from . import portability

    current = _require_current(store)
    if args.file:
        portability.write_export(current, args.file)
        print(f"Exported {current.name!r} to {args.file}.")
    else:
        print(json.dumps(current.to_dict(), indent=2, ensure_ascii=False))
    return 0


def _cmd_backup(args, store: Store) -> int:
    import json

    from . import sync as sync_mod

    snapshot = sync_mod.build_snapshot(store)
    Path(args.file).write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    n = len(snapshot["workspaces"])
    print(f"Backed up {n} workspace(s) to {args.file}.")
    return 0


def _cmd_restore(args, store: Store) -> int:
    import json

    from . import sync as sync_mod

    try:
        snapshot = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ParaisoError(f"Couldn't read {args.file!r}: {exc}") from exc
    if snapshot.get("paraiso_snapshot") is None:
        raise ParaisoError(f"{args.file!r} is not a paraiso snapshot.")
    report = sync_mod.apply_snapshot(store, snapshot)
    print(report)
    return 0


def _cmd_sync(args, store: Store) -> int:
    from . import sync as sync_mod

    settings = store.sync_settings()
    name = args.via or settings.get("transport") or "filesystem"
    path = args.path or settings.get("path")
    transport = sync_mod.resolve_transport(name, path=path)
    report = sync_mod.sync(store, transport)
    store.set_sync_settings({"transport": name, "path": path})
    print(report)
    return 0


def _cmd_shell(args, store: Store) -> int:
    from .shell import ParaisoShell

    return ParaisoShell(store).run()


def _cmd_show(args, store: Store) -> int:
    current = _require_current(store)
    color = term.color_enabled()
    s = current.summary()
    print(f"{term.paint(s['name'], palette.DEFAULT_ACCENT, bold=True, enabled=color)}"
          f" — {s['inbox']} in Inbox, {s['items']} items")
    for bucket in Bucket:
        count = len(current.items_in(bucket))
        dot = term.paint("●", palette.BUCKET_COLORS[bucket.value], enabled=color)
        print(f"  {dot} {bucket.label}: {count}")
    print(f"  Areas: {s['areas']}    Objectives: {s['objectives']}")
    return 0


_EPILOG = """commands, by category:
  workspaces   spaces  new  use  rename
  capture      capture  inbox
  sort         sort  file  move  delete
  browse       tree  show  projects  resources  seeds  archive
  organize     area  objective       (bare = list; `add`/`show`/`edit` too)
  data         import  export  backup  restore  sync
  info         framework  shell
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paraiso",
        description="PARAISO: one calm home for everything on your mind.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"paraiso {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("framework", help="explain what PARAISO stands for").set_defaults(func=_cmd_framework)

    sub.add_parser("spaces", help="list workspaces").set_defaults(func=_cmd_spaces)

    p_new = sub.add_parser("new", help="create and switch to a workspace")
    p_new.add_argument("name")
    p_new.add_argument("--description", "-d")
    p_new.set_defaults(func=_cmd_new)

    p_use = sub.add_parser("use", help="switch the active workspace")
    p_use.add_argument("name")
    p_use.set_defaults(func=_cmd_use)

    p_rename = sub.add_parser("rename", help="rename the active workspace (or `rename <old> <new>`)")
    p_rename.add_argument("name1", metavar="new-name")
    p_rename.add_argument("name2", nargs="?", metavar="[new-name-if-renaming-another]")
    p_rename.set_defaults(func=_cmd_rename)

    p_cap = sub.add_parser("capture", help="drop a thought in the Inbox")
    p_cap.add_argument("text", nargs="+")
    p_cap.set_defaults(func=_cmd_capture)

    sub.add_parser("inbox", help="list unsorted captures").set_defaults(func=_cmd_inbox)

    p_file = sub.add_parser("file", help="file a capture into a bucket")
    p_file.add_argument("capture_id")
    p_file.add_argument("--bucket", "-b", required=True, help="project | resource | seed | archive")
    p_file.add_argument("--title", "-t")
    p_file.add_argument("--summary", "-s")
    p_file.add_argument("--area", "-a")
    p_file.add_argument("--objective", "-o")
    p_file.add_argument("--tags")
    p_file.set_defaults(func=_cmd_file)

    p_area = sub.add_parser("area", help="list Areas (also: add / show / edit)")
    area_sub = p_area.add_subparsers(dest="area_action")
    a_add = area_sub.add_parser("add")
    a_add.add_argument("name")
    a_add.add_argument("--tags")
    a_show = area_sub.add_parser("show")
    a_show.add_argument("id", nargs="?")
    a_edit = area_sub.add_parser("edit")
    a_edit.add_argument("id", nargs="?")
    area_sub.add_parser("list")
    p_area.set_defaults(func=_cmd_area, area_action="list")

    p_obj = sub.add_parser("objective", help="list Objectives (or `objective add <title>`)")
    obj_sub = p_obj.add_subparsers(dest="objective_action")
    o_add = obj_sub.add_parser("add")
    o_add.add_argument("title")
    o_add.add_argument("--area", "-a")
    obj_sub.add_parser("list")
    p_obj.set_defaults(func=_cmd_objective, objective_action="list")

    # Per-bucket browse shortcuts (the PARAISO pages). `-a` filters by Area:
    # bare `-a` prompts a picker; `-a <id-or-prefix>` filters directly.
    for _slug, _bucket in (
        ("projects", "project"),
        ("resources", "resource"),
        ("seeds", "seed"),
        ("archive", "archive"),
    ):
        p_bucket = sub.add_parser(_slug, help=f"list items in {_bucket.title()} (-a filters by Area)")
        p_bucket.add_argument(
            "-a", "--area", nargs="?", const=_PROMPT_AREA, default=None,
            help="area id/prefix to filter by, or bare -a to pick one",
        )
        p_bucket.set_defaults(func=_cmd_items, bucket=_bucket, objective=None)

    sub.add_parser("show", help="quick counts for the active workspace").set_defaults(func=_cmd_show)
    sub.add_parser("tree", help="colorful overview of everything").set_defaults(func=_cmd_tree)

    # Guided sorting + reclassify + delete.
    sub.add_parser("sort", help="sort the Inbox interactively (press a key per capture)").set_defaults(func=_cmd_sort)

    p_move = sub.add_parser("move", help="reclassify an item (interactive if no args)")
    p_move.add_argument("item_id", nargs="?")
    p_move.add_argument("bucket", nargs="?", help="project | resource | seed | archive")
    p_move.add_argument("--area", "-a")
    p_move.set_defaults(func=_cmd_move)

    p_del = sub.add_parser("delete", help="delete an item or Area (interactive if no id)")
    p_del.add_argument("id", nargs="?", help="item or area id (area keeps its items)")
    p_del.add_argument("--yes", "-y", action="store_true", help="skip the confirmation")
    p_del.set_defaults(func=_cmd_delete)

    # Data portability.
    p_import = sub.add_parser("import", help="import a workspace from a JSON export")
    p_import.add_argument("file")
    p_import.add_argument("--name", "-n", help="name for the imported workspace")
    p_import.add_argument("--force", "-f", action="store_true", help="overwrite an existing workspace")
    p_import.set_defaults(func=_cmd_import)

    p_export = sub.add_parser("export", help="export the active workspace as JSON")
    p_export.add_argument("file", nargs="?", help="output path (prints to stdout if omitted)")
    p_export.set_defaults(func=_cmd_export)

    p_backup = sub.add_parser("backup", help="write a snapshot of all workspaces to a file")
    p_backup.add_argument("file")
    p_backup.set_defaults(func=_cmd_backup)

    p_restore = sub.add_parser("restore", help="merge a snapshot file into this install")
    p_restore.add_argument("file")
    p_restore.set_defaults(func=_cmd_restore)

    p_sync = sub.add_parser("sync", help="two-way sync via a transport (pull, merge, push)")
    p_sync.add_argument("--via", help="transport name (default: filesystem, or your last choice)")
    p_sync.add_argument("--path", help="snapshot file for the filesystem transport")
    p_sync.set_defaults(func=_cmd_sync)

    sub.add_parser("shell", help="start the interactive shell").set_defaults(func=_cmd_shell)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = Store()
    if not getattr(args, "func", None):
        # No subcommand: drop into the interactive shell at a terminal,
        # otherwise print help (so pipes/CI stay non-interactive).
        if sys.stdin.isatty():
            from .shell import ParaisoShell

            return ParaisoShell(store).run()
        parser.print_help()
        return 0
    try:
        return args.func(args, store)
    except ParaisoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
