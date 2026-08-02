"""Tests for the interactive shell.

``cmd.Cmd.onecmd`` runs a single command line, so we can exercise the shell's
commands and completion without spinning up the interactive loop.
"""

import pytest

from paraiso import Store
from paraiso.shell import ParaisoShell


@pytest.fixture
def shell(tmp_path):
    return ParaisoShell(Store(base_dir=tmp_path))


def test_shell_runs_the_core_flow(shell):
    shell.onecmd("new personal")
    assert shell.store.active() == "personal"
    # Plain prompt (color is off when stdout isn't a terminal, as in tests).
    assert shell.prompt == "paraiso (personal) › "

    shell.onecmd("capture buy mulch")
    current = shell.store.current()
    assert current is not None
    assert current.inbox[0].text == "buy mulch"

    cap_id = current.inbox[0].id
    shell.onecmd(f"file {cap_id} --bucket project --title Mulch")
    assert shell.store.current().summary()["buckets"]["Projects"] == 1


def test_welcome_banner_shows_wordmark_and_status(shell):
    banner = shell._welcome_banner()
    assert "P   A   R   A   I   S   O" in banner  # the PARAISO wordmark, spaced
    assert "one calm home for everything on your mind." in banner
    assert "no workspace yet" in banner  # fresh store has none active
    shell.store.create("home")
    assert "workspace" in shell._welcome_banner()


def test_help_clears_screen_on_a_tty(shell, monkeypatch):
    import io

    buf = io.StringIO()
    shell.stdout = buf
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    shell.onecmd("help")
    out = buf.getvalue()
    assert "\033[2J" in out          # screen cleared
    assert "Workspaces" in out       # then the categorized help


def test_help_does_not_clear_when_not_a_tty(shell):
    import io

    buf = io.StringIO()
    shell.stdout = buf
    shell.onecmd("help")
    out = buf.getvalue()
    assert "\033[2J" not in out      # piped/CI: no escape codes
    assert "Workspaces" in out


def test_quit_returns_true(shell):
    assert shell.onecmd("quit") is True
    assert shell.onecmd("EOF") is True


def test_bad_input_does_not_kill_the_shell(shell, capsys):
    # A usage error would make argparse call sys.exit; the shell must survive it.
    result = shell.onecmd("file")  # missing required --bucket
    assert result is None  # shell keeps going


def test_workspace_name_completion(shell):
    shell.store.create("work")
    shell.store.create("personal")
    assert set(shell.complete_use("", "use ", 4, 4)) == {"work", "personal"}
    assert shell.complete_use("wo", "use wo", 4, 6) == ["work"]


def test_browse_commands_list_items(shell, capsys):
    shell.onecmd("new demo")
    shell.onecmd("capture redo the website")
    cap_id = shell.store.current().inbox[0].id
    shell.onecmd(f"file {cap_id} --bucket project --title Website")
    capsys.readouterr()  # clear

    shell.onecmd("projects")
    out = capsys.readouterr().out
    assert "Projects (1)" in out
    assert "Website" in out

    shell.onecmd("tree")
    tree = capsys.readouterr().out
    assert "Projects (1)" in tree and "Website" in tree


def test_shell_move_and_delete(shell):
    shell.onecmd("new t")
    shell.onecmd("area add Work")
    aid = shell.store.current().areas[0].id
    shell.onecmd("capture the website")
    cid = shell.store.current().inbox[0].id
    shell.onecmd(f"file {cid} --bucket seed --title Website --area {aid}")
    iid = shell.store.current().items[0].id

    shell.onecmd(f"move {iid} project")
    assert shell.store.current().items_in("project")[0].id == iid

    # Deleting the Area keeps the item but detaches it.
    shell.onecmd(f"delete {aid} --yes")
    current = shell.store.current()
    assert current.areas == []
    assert current.items[0].area_id is None

    # Deleting the item is permanent.
    shell.onecmd(f"delete {iid} --yes")
    assert shell.store.current().items == []


def test_triage_flow_files_and_discards(tmp_path, monkeypatch):
    from paraiso import interactive

    store = Store(base_dir=tmp_path)
    store.create("t")
    current = store.current()
    current.capture("redo the website")
    current.capture("random noise")
    store.save(current)

    # Capture 1: file it (Enter action → keep title → area none → bucket p).
    # Capture 2: discard (d at the action bar).
    keys = iter(["", "", "p", "d"])
    monkeypatch.setattr(interactive, "read_key", lambda prompt="": next(keys))
    # No areas exist, so choose_area asks for a name; blank = none.
    monkeypatch.setattr("builtins.input", lambda prompt="": "")

    interactive.triage(store, color=False)

    result = store.current()
    assert result.inbox == []  # both resolved
    projects = result.items_in("project")
    assert len(projects) == 1
    assert projects[0].title == "redo the website"


def test_triage_esc_at_action_bar_quits(tmp_path, monkeypatch):
    from paraiso import interactive

    store = Store(base_dir=tmp_path)
    store.create("t")
    current = store.current()
    current.capture("one")
    current.capture("two")
    store.save(current)

    monkeypatch.setattr(interactive, "read_key", lambda prompt="": "esc")
    interactive.triage(store, color=False)

    assert len(store.current().inbox) == 2  # Esc quit before filing anything


def test_triage_esc_mid_filing_skips_capture(tmp_path, monkeypatch):
    from paraiso import interactive

    store = Store(base_dir=tmp_path)
    store.create("t")
    current = store.current()
    current.capture("only one")
    store.save(current)

    # Enter to start filing, then Esc at the title step → skip this capture.
    keys = iter(["", "esc"])
    monkeypatch.setattr(interactive, "read_key", lambda prompt="": next(keys))
    interactive.triage(store, color=False)

    assert len(store.current().inbox) == 1  # still unsorted
    assert store.current().items == []


def test_move_flow_changes_bucket_but_keeps_area(tmp_path, monkeypatch):
    from paraiso import interactive

    store = Store(base_dir=tmp_path)
    store.create("t")
    current = store.current()
    area = current.create_area("Work")
    c = current.capture("the website")
    current.file(c, "seed", title="Website", area=area)
    store.save(current)

    # pick item 1 (typed); bucket 'p' (project); area 'k' (keep current, keypress)
    keys = iter(["p", "k"])
    monkeypatch.setattr(interactive, "read_key", lambda prompt="": next(keys))
    monkeypatch.setattr("builtins.input", lambda prompt="": "1")

    interactive.move_flow(store, color=False)

    result = store.current()
    moved = result.items_in("project")[0]
    assert moved.title == "Website"
    assert moved.area_id == area.id  # area kept


def test_read_key_normalizes_enter_and_ctrl():
    import pytest

    from paraiso.interactive import _normalize_key

    # Enter arrives as CR in raw mode — must become "" so loops can finish.
    assert _normalize_key("\r") == ""
    assert _normalize_key("\n") == ""
    assert _normalize_key("") == ""
    assert _normalize_key("P") == "p"
    for ctrl in ("\x03", "\x04"):
        with pytest.raises(KeyboardInterrupt):
            _normalize_key(ctrl)


def test_edit_area_recolors_from_palette(tmp_path, monkeypatch):
    from paraiso import interactive, palette

    store = Store(base_dir=tmp_path)
    store.create("t")
    current = store.current()
    area = current.create_area("Work")
    store.save(current)

    # press 'c' (color), choose palette #5, then Enter to finish
    keys = iter(["c", ""])
    monkeypatch.setattr(interactive, "read_key", lambda prompt="": next(keys))
    monkeypatch.setattr("builtins.input", lambda prompt="": "5")

    interactive.edit_area_flow(store, area_id=area.id, color=False)

    assert store.current().areas[0].color == palette.AREA_COLORS[4]


def test_file_completion_offers_bucket_values_and_capture_ids(shell):
    shell.onecmd("new p")
    current = shell.store.current()
    current.capture("something")
    shell.store.save(current)
    cap_id = shell.store.current().inbox[0].id

    # After --bucket, complete bucket names.
    line = "file cap_x --bucket "
    buckets = shell.complete_file("", line, len(line), len(line))
    assert set(buckets) == {"project", "resource", "seed", "archive"}

    # At the first positional, offer the unsorted capture id.
    assert cap_id in shell.complete_file("cap", "file cap", 5, 8)
