from paraiso import Paraiso, Store
from paraiso.util import short_id


def test_update_item_changes_only_given_fields():
    p = Paraiso("x")
    it = p.add_item("orig", "project", summary="s", content="c", tags=["a"])
    before = it.updated_at
    p.update_item(it, title="new title")
    assert it.title == "new title"
    assert it.summary == "s"       # untouched
    assert it.content == "c"
    assert it.tags == ["a"]
    assert it.updated_at > before  # bumped


def test_update_item_all_fields():
    p = Paraiso("x")
    it = p.add_item("t", "seed")
    p.update_item(it, title="T", summary="S", content="C", tags=["x", "y"])
    assert (it.title, it.summary, it.content, it.tags) == ("T", "S", "C", ["x", "y"])


def test_update_item_by_prefix():
    p = Paraiso("x")
    it = p.add_item("t", "seed")
    p.update_item(short_id(it.id), title="Z")
    assert p.get_item(it.id).title == "Z"


# -- $EDITOR helper --------------------------------------------------------


def test_edit_in_editor_fallback_uses_input(monkeypatch):
    from paraiso import interactive

    monkeypatch.setattr("builtins.input", lambda prompt="": "typed line")
    assert interactive.edit_in_editor("original") == "typed line"


def test_edit_in_editor_blank_keeps_original(monkeypatch):
    from paraiso import interactive

    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    assert interactive.edit_in_editor("keep me") == "keep me"


def test_edit_in_editor_opens_editor(monkeypatch):
    from paraiso import interactive

    monkeypatch.setenv("EDITOR", "fake-editor")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)

    def fake_call(cmd):
        with open(cmd[-1], "w", encoding="utf-8") as f:
            f.write("edited via editor\n")
        return 0

    monkeypatch.setattr(interactive.subprocess, "call", fake_call)
    assert interactive.edit_in_editor("orig") == "edited via editor"


# -- guided edit flow ------------------------------------------------------


def test_edit_item_flow_edits_title_and_tags(tmp_path, monkeypatch):
    from paraiso import interactive

    store = Store(base_dir=tmp_path)
    store.create("t")
    current = store.current()
    it = current.add_item("orig", "project")
    store.save(current)

    keys = iter(["t", "g", ""])  # title, tags, done
    monkeypatch.setattr(interactive, "read_key", lambda prompt="": next(keys))
    inputs = iter(["New Title", "x, y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    interactive.edit_item_flow(store, item_id=it.id, color=False)

    result = store.current().get_item(it.id)
    assert result.title == "New Title"
    assert result.tags == ["x", "y"]


def test_edit_item_flow_content_via_editor(tmp_path, monkeypatch):
    from paraiso import interactive

    store = Store(base_dir=tmp_path)
    store.create("t")
    current = store.current()
    it = current.add_item("orig", "seed", content="old")
    store.save(current)

    keys = iter(["c", ""])
    monkeypatch.setattr(interactive, "read_key", lambda prompt="": next(keys))
    monkeypatch.setattr(interactive, "edit_in_editor", lambda text: "brand new content")

    interactive.edit_item_flow(store, item_id=it.id, color=False)
    assert store.current().get_item(it.id).content == "brand new content"


# -- CLI item command ------------------------------------------------------


def _run(argv, store):
    from paraiso.cli import build_parser

    args = build_parser().parse_args(argv)
    return args.func(args, store)


def test_item_show_renders_detail(tmp_path, capsys):
    store = Store(base_dir=tmp_path)
    store.create("w")
    p = store.current()
    area = p.create_area("Travel")
    it = p.add_item("Book flights", "project", content="compare prices",
                    area=area, tags=["urgent"])
    store.save(p)

    _run(["item", "show", it.id], store)
    out = capsys.readouterr().out
    assert "Book flights" in out
    assert "compare prices" in out    # full content shown
    assert "Travel" in out
    assert "urgent" in out


def test_item_list_grouped_by_area(tmp_path, capsys):
    store = Store(base_dir=tmp_path)
    store.create("w")
    p = store.current()
    beta = p.create_area("Beta")
    alpha = p.create_area("Alpha")
    p.add_item("apple", "project", area=beta)
    p.add_item("zebra", "seed", area=alpha)
    p.add_item("mango", "resource")   # no Area
    store.save(p)

    _run(["item"], store)
    out = capsys.readouterr().out
    z, a, m = out.index("zebra"), out.index("apple"), out.index("mango")
    assert z < a < m   # Alpha, Beta, then orphan


def test_item_edit_dispatches_to_flow(tmp_path, monkeypatch):
    from paraiso import interactive

    store = Store(base_dir=tmp_path)
    store.create("w")
    p = store.current()
    it = p.add_item("x", "seed")
    store.save(p)

    called = {}
    monkeypatch.setattr(
        interactive, "edit_item_flow",
        lambda store_, *, item_id=None, **kw: called.setdefault("id", item_id) or 0,
    )
    _run(["item", "edit", it.id], store)
    assert called["id"] == it.id
