"""An interactive PARAISO shell, built on the stdlib :mod:`cmd` + ``readline``.

This is the "sit down and work" front door: a REPL with tab-completion, command
history, and arrow-key line editing (all from the standard library — no
dependencies). It reuses the exact same commands as the one-shot CLI, so
``paraiso capture "x"`` and typing ``capture x`` at the prompt do the same
thing.

Launch it with ``paraiso shell`` (or just ``paraiso`` at a terminal).
"""

from __future__ import annotations

import cmd
import shlex
import sys
from typing import Optional

from . import framework, palette, term
from ._version import __version__
from .cli import build_parser
from .errors import ParaisoError
from .framework import Bucket
from .store import Store

# Flags that expect a value the shell can complete for.
_FILE_FLAGS = ["--bucket", "--title", "--summary", "--area", "--objective", "--tags"]

# Commands grouped for a scannable `help`.
_HELP_CATEGORIES = (
    ("Workspaces", ("spaces", "new", "use", "rename")),
    ("Capture", ("capture", "inbox")),
    ("Sort", ("sort", "file", "move", "delete")),
    ("Browse", ("tree", "show", "projects", "resources", "seeds", "archive")),
    ("Organize", ("area", "objective")),
    ("Data", ("import", "export", "backup", "restore", "sync")),
    ("Info", ("framework", "help", "quit")),
)


def _is_libedit() -> bool:
    try:
        import readline

        return "libedit" in (readline.__doc__ or "")
    except ImportError:  # pragma: no cover
        return False


class ParaisoShell(cmd.Cmd):
    """A calm, tab-completing shell over a :class:`~paraiso.store.Store`."""

    def __init__(self, store: Optional[Store] = None) -> None:
        super().__init__()
        self.store = store or Store()
        self.parser = build_parser()
        # Prompt color only when it's safe: a real terminal AND GNU readline
        # (libedit ignores the zero-width markers and would print them raw).
        self._prompt_color = term.color_enabled() and not _is_libedit()
        self.prompt = self._prompt()

    # -- lifecycle ---------------------------------------------------------

    def run(self) -> int:
        """Run the loop, treating Ctrl-C as "cancel this line", not "quit"."""
        self._show_welcome()
        while True:
            try:
                self.cmdloop(None)  # welcome already shown; no cmd intro
                break
            except KeyboardInterrupt:
                self.stdout.write("^C\n")
        return 0

    def _show_welcome(self) -> None:
        """A calm, colorful welcome. On a real terminal it clears the screen
        first; piped/CI runs get the plain one-liner instead."""
        if sys.stdout.isatty():
            self.stdout.write("\033[2J\033[H")  # clear + home cursor
            self.stdout.write(self._welcome_banner())
        else:
            self.stdout.write(self._intro())

    def _welcome_banner(self) -> str:
        color = term.color_enabled()
        wordmark = "   ".join(
            term.paint(piece.letter, hexc, bold=True, enabled=color)
            for piece, hexc in zip(framework.PIECES, palette.PIECE_COLORS)
        )
        name = self.store.active()
        if name:
            status = term.dim("workspace  ", enabled=color) + term.paint(
                name, palette.color_for(name), bold=True, enabled=color
            )
        else:
            status = (
                term.dim("no workspace yet — ", enabled=color)
                + term.paint("new <name>", palette.DEFAULT_ACCENT, enabled=color)
                + term.dim(" to begin", enabled=color)
            )
        hint = "  ·  ".join(
            term.paint(word, palette.DEFAULT_ACCENT, enabled=color)
            for word in ("help", "framework", "quit")
        )
        pad = "      "
        return "\n".join(
            [
                "",
                "",
                pad + wordmark,
                "",
                pad + term.dim("one calm home for everything on your mind.", enabled=color),
                "",
                "",
                pad + status,
                pad + hint,
                "",
                pad + term.dim(f"paraiso {__version__}", enabled=color),
                "",
                "",
            ]
        )

    def cmdloop(self, intro: Optional[str] = None) -> None:  # noqa: D102
        # macOS ships libedit rather than GNU readline; bind Tab explicitly so
        # completion works there too. On GNU readline this is a harmless no-op.
        try:
            import readline

            if "libedit" in (readline.__doc__ or ""):
                readline.parse_and_bind("bind ^I rl_complete")
        except ImportError:
            pass
        super().cmdloop(intro=intro)

    def emptyline(self) -> bool:
        return False  # a blank line does nothing (don't repeat the last command)

    def default(self, line: str) -> None:
        word = line.split()[0] if line.split() else line
        self.stdout.write(f"Unknown command: {word!r}. Type `help` for the list.\n")

    # -- commands (thin wrappers over the shared CLI handlers) -------------

    def do_framework(self, arg: str) -> None:
        "Explain what PARAISO stands for."
        self._dispatch("framework", arg)

    def do_spaces(self, arg: str) -> None:
        "List workspaces (the active one is starred)."
        self._dispatch("spaces", arg)

    def do_new(self, arg: str) -> None:
        "new NAME [--description TEXT] — create and switch to a workspace."
        self._dispatch("new", arg)

    def do_use(self, arg: str) -> None:
        "use NAME — switch the active workspace."
        self._dispatch("use", arg)

    def do_rename(self, arg: str) -> None:
        "rename NEW — rename the active workspace (or `rename OLD NEW`)."
        self._dispatch("rename", arg)

    def do_capture(self, arg: str) -> None:
        "capture TEXT — drop a thought into the Inbox."
        self._dispatch("capture", arg)

    def do_inbox(self, arg: str) -> None:
        "List captures still waiting to be sorted."
        self._dispatch("inbox", arg)

    def do_file(self, arg: str) -> None:
        "file CAP_ID --bucket B [--title T --area A --objective O --tags a,b] — file a capture."
        self._dispatch("file", arg)

    def do_area(self, arg: str) -> None:
        "area — list Areas. Also: `area add NAME`, `area show [id]`, `area edit [id]`."
        self._dispatch("area", arg)

    def do_objective(self, arg: str) -> None:
        "objective — list Objectives. `objective add TITLE [--area A]` creates one."
        self._dispatch("objective", arg)

    def do_projects(self, arg: str) -> None:
        "List items in Projects."
        self._dispatch("projects", arg)

    def do_resources(self, arg: str) -> None:
        "List items in Resources."
        self._dispatch("resources", arg)

    def do_seeds(self, arg: str) -> None:
        "List items in Seeds."
        self._dispatch("seeds", arg)

    def do_archive(self, arg: str) -> None:
        "List items in Archive."
        self._dispatch("archive", arg)

    def do_show(self, arg: str) -> None:
        "Quick counts for the active workspace."
        self._dispatch("show", arg)

    def do_tree(self, arg: str) -> None:
        "Colorful overview of everything in the active workspace."
        self._dispatch("tree", arg)

    def do_sort(self, arg: str) -> None:
        "Sort the Inbox interactively — press a key per capture to file it."
        self._dispatch("sort", arg)

    def do_move(self, arg: str) -> None:
        "move [ITEM_ID BUCKET] — reclassify an item (guided if you give no args)."
        self._dispatch("move", arg)

    def do_delete(self, arg: str) -> None:
        "delete [ID] — delete an item or Area (guided picker if you give no id)."
        self._dispatch("delete", arg)

    def do_import(self, arg: str) -> None:
        "import FILE [--name NAME] [--force] — import a workspace from a JSON export."
        self._dispatch("import", arg)

    def do_export(self, arg: str) -> None:
        "export [FILE] — export the active workspace as JSON (stdout if no file)."
        self._dispatch("export", arg)

    def do_backup(self, arg: str) -> None:
        "backup FILE — write a snapshot of all workspaces to a file."
        self._dispatch("backup", arg)

    def do_restore(self, arg: str) -> None:
        "restore FILE — merge a snapshot file into this install."
        self._dispatch("restore", arg)

    def do_sync(self, arg: str) -> None:
        "sync [--via NAME --path FILE] — two-way sync (pull, merge, push)."
        self._dispatch("sync", arg)

    def do_clear(self, arg: str) -> None:
        "Clear the screen."
        self.stdout.write("\033[2J\033[H")

    def do_quit(self, arg: str) -> bool:
        "Leave the shell."
        self.stdout.write("\n")
        return True

    do_exit = do_quit  # the one alias worth keeping

    def do_EOF(self, arg: str) -> bool:  # Ctrl-D
        self.stdout.write("\n")
        return True

    def do_help(self, arg: str) -> None:
        "help [command] — list commands by category, or explain one."
        if sys.stdout.isatty():
            self.stdout.write("\033[2J\033[H")  # clear for a clean help page
        if arg:
            super().do_help(arg)
            return
        color = term.color_enabled()
        self.stdout.write("\n")
        for title, commands in _HELP_CATEGORIES:
            label = term.paint(f"{title:<11}", palette.DEFAULT_ACCENT, bold=True, enabled=color)
            self.stdout.write(f"  {label} {'  '.join(commands)}\n")
        hint = term.paint("help <command>", palette.DEFAULT_ACCENT, enabled=color)
        self.stdout.write(f"\n  Type {hint} for details on any command.\n\n")

    # -- completion --------------------------------------------------------

    def complete_use(self, text, line, begidx, endidx):
        return [s for s in self.store.spaces() if s.startswith(text)]

    def complete_rename(self, text, line, begidx, endidx):
        # First arg may be an existing workspace name (when renaming another).
        return [s for s in self.store.spaces() if s.startswith(text)]

    def complete_area(self, text, line, begidx, endidx):
        preceding = line[:begidx].split()
        if len(preceding) <= 1:
            return [s for s in ("add", "list", "show", "edit") if s.startswith(text)]
        if len(preceding) == 2 and preceding[1] in ("show", "edit"):
            current = self.store.current()
            ids = [a.id for a in current.areas] if current else []
            return [i for i in ids if i.startswith(text)]
        return []

    def complete_objective(self, text, line, begidx, endidx):
        return [s for s in ("add", "list") if s.startswith(text)]

    def complete_move(self, text, line, begidx, endidx):
        current = self.store.current()
        preceding = line[:begidx].split()
        if len(preceding) <= 1:  # first arg: item id
            ids = [i.id for i in current.items] if current else []
            return [i for i in ids if i.startswith(text)]
        if len(preceding) == 2:  # second arg: bucket
            return [b.value for b in Bucket if b.value.startswith(text)]
        return []

    def complete_delete(self, text, line, begidx, endidx):
        current = self.store.current()
        ids = (
            [i.id for i in current.items] + [a.id for a in current.areas]
            if current
            else []
        )
        return [i for i in ids if i.startswith(text)]

    def complete_file(self, text, line, begidx, endidx):
        prev = self._prev_token(line, begidx)
        current = self.store.current()
        if prev in ("--bucket", "-b"):
            return [b.value for b in Bucket if b.value.startswith(text)]
        if prev in ("--area", "-a"):
            ids = [a.id for a in current.areas] if current else []
            return [i for i in ids if i.startswith(text)]
        if prev in ("--objective", "-o"):
            ids = [o.id for o in current.objectives] if current else []
            return [i for i in ids if i.startswith(text)]
        # Default: complete an unsorted capture id, or a flag name.
        cap_ids = [c.id for c in current.inbox] if current else []
        return [c for c in (cap_ids + _FILE_FLAGS) if c.startswith(text)]

    # -- internals ---------------------------------------------------------

    def _dispatch(self, command: str, arg: str) -> None:
        try:
            tokens = shlex.split(arg)
        except ValueError as exc:  # e.g. an unbalanced quote
            self.stdout.write(f"error: {exc}\n")
            return
        try:
            namespace = self.parser.parse_args([command, *tokens])
        except SystemExit:
            # argparse calls sys.exit on a usage error; keep the shell alive.
            return
        func = getattr(namespace, "func", None)
        if func is not None:
            try:
                func(namespace, self.store)
            except ParaisoError as exc:
                self.stdout.write(f"error: {exc}\n")
        # `new`/`use` change the active workspace — refresh the prompt.
        self.prompt = self._prompt()

    def _prompt(self) -> str:
        color = getattr(self, "_prompt_color", False)
        name = self.store.active()
        if not name:
            return term.prompt("paraiso ›", palette.DEFAULT_ACCENT, enabled=color) + " "
        return (
            term.prompt("paraiso", palette.DEFAULT_ACCENT, enabled=color)
            + " "
            + term.prompt(f"({name})", palette.color_for(name), bold=True, enabled=color)
            + " "
            + term.prompt("›", palette.DEFAULT_ACCENT, enabled=color)
            + " "
        )

    def _intro(self) -> str:
        return (
            f"paraiso {__version__} — interactive shell.\n"
            "Type `help` or `?` for commands, `framework` for what PARAISO means, "
            "`quit` to exit.\n"
        )

    @staticmethod
    def _prev_token(line: str, begidx: int) -> str:
        parts = line[:begidx].split()
        return parts[-1] if parts else ""
