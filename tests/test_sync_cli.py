import pytest

from paraiso import Store
from paraiso.cli import build_parser
from paraiso.errors import ParaisoError
from paraiso.sync import FilesystemTransport, resolve_transport


def _run(argv, store):
    args = build_parser().parse_args(argv)
    return args.func(args, store)


def test_backup_then_restore_roundtrip(tmp_path, capsys):
    src = Store(base_dir=tmp_path / "a")
    src.create("w"); p = src.current(); p.capture("carry me"); src.save(p)
    snap_file = tmp_path / "backup.json"
    _run(["backup", str(snap_file)], src)
    assert snap_file.exists()

    dst = Store(base_dir=tmp_path / "b")
    _run(["restore", str(snap_file)], dst)
    assert dst.load("w").inbox[0].text == "carry me"


def test_resolve_filesystem_requires_path():
    assert isinstance(resolve_transport("filesystem", path="/tmp/x.json"), FilesystemTransport)
    with pytest.raises(ParaisoError):
        resolve_transport("filesystem", path=None)


def test_resolve_unknown_transport_raises():
    with pytest.raises(ParaisoError):
        resolve_transport("does-not-exist")


def test_sync_command_uses_and_remembers_settings(tmp_path):
    store = Store(base_dir=tmp_path / "s")
    store.create("w")
    snap = tmp_path / "snap.json"
    _run(["sync", "--path", str(snap)], store)
    assert snap.exists()
    # Settings persisted so a later bare `sync` reuses them.
    assert store.sync_settings()["path"] == str(snap)
    assert store.sync_settings()["transport"] == "filesystem"


def test_resolve_loads_entry_point(monkeypatch):
    class FakeTransport:
        def pull(self): return None
        def push(self, snap): pass

    class FakeEP:
        name = "fake"
        def load(self): return FakeTransport

    monkeypatch.setattr("paraiso.sync._transport_entry_points", lambda: [FakeEP()])
    assert isinstance(resolve_transport("fake"), FakeTransport)
