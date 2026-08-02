from paraiso import Store
from paraiso.cli import build_parser


def _seed(tmp_path):
    store = Store(base_dir=tmp_path)
    store.create("w")
    p = store.current()
    health = p.create_area("Health")
    work = p.create_area("Work")
    p.add_item("run a 5k", "project", area=health)
    p.add_item("ship v2", "project", area=work)
    store.save(p)
    return store, health, work


def _run(argv, store):
    args = build_parser().parse_args(argv)
    return args.func(args, store)


def test_projects_filtered_by_area_id(tmp_path, capsys):
    store, health, _ = _seed(tmp_path)
    _run(["projects", "-a", health.id], store)
    out = capsys.readouterr().out
    assert "run a 5k" in out
    assert "ship v2" not in out


def test_projects_filtered_by_area_prefix(tmp_path, capsys):
    store, _, work = _seed(tmp_path)
    _run(["projects", "-a", work.id[:8]], store)  # unique prefix resolves
    out = capsys.readouterr().out
    assert "ship v2" in out
    assert "run a 5k" not in out


def test_projects_no_area_shows_all(tmp_path, capsys):
    store, _, _ = _seed(tmp_path)
    _run(["projects"], store)
    out = capsys.readouterr().out
    assert "run a 5k" in out and "ship v2" in out


def test_projects_area_prompt(tmp_path, capsys, monkeypatch):
    from paraiso import interactive

    store, health, _ = _seed(tmp_path)
    # Bare -a → picker; choose option 1 (first area = Health).
    monkeypatch.setattr(interactive, "read_key", lambda prompt="": "1")
    _run(["projects", "-a"], store)
    out = capsys.readouterr().out
    assert "run a 5k" in out
    assert "ship v2" not in out
