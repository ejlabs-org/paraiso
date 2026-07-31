from paraiso import Store
from paraiso.sync import (
    FilesystemTransport,
    apply_snapshot,
    build_snapshot,
    sync,
)


def test_build_snapshot_shape(tmp_path):
    store = Store(base_dir=tmp_path)
    store.create("work")
    snap = build_snapshot(store)
    assert snap["paraiso_snapshot"] == 1
    assert snap["active"] == "work"
    assert [w["name"] for w in snap["workspaces"]] == ["work"]


def test_apply_snapshot_creates_missing_workspace(tmp_path):
    src = Store(base_dir=tmp_path / "a")
    src.create("shared"); p = src.current(); p.capture("hello"); src.save(p)
    snap = build_snapshot(src)

    dst = Store(base_dir=tmp_path / "b")
    report = apply_snapshot(dst, snap)
    assert "shared" in dst.spaces()
    assert dst.load("shared").inbox[0].text == "hello"
    assert "shared" in report.created


def test_filesystem_transport_roundtrip(tmp_path):
    store = Store(base_dir=tmp_path / "s")
    store.create("w")
    t = FilesystemTransport(tmp_path / "snap.json")
    assert t.pull() is None                      # nothing there yet
    t.push(build_snapshot(store))
    assert t.pull()["workspaces"][0]["name"] == "w"


def test_sync_converges_two_installs(tmp_path):
    shared = tmp_path / "snap.json"
    a = Store(base_dir=tmp_path / "a"); a.create("main")
    b = Store(base_dir=tmp_path / "b"); b.create("main")

    pa = a.current(); pa.capture("from A"); a.save(pa)
    sync(a, FilesystemTransport(shared))         # A pushes

    pb = b.current(); pb.capture("from B"); b.save(pb)
    sync(b, FilesystemTransport(shared))         # B pulls A, merges, pushes
    sync(a, FilesystemTransport(shared))         # A pulls the merged result

    texts_a = {c.text for c in a.load("main").captures}
    texts_b = {c.text for c in b.load("main").captures}
    assert texts_a == texts_b == {"from A", "from B"}


def test_sync_deletion_propagates(tmp_path):
    shared = tmp_path / "snap.json"
    a = Store(base_dir=tmp_path / "a"); a.create("main")
    pa = a.current(); item = pa.add_item("doomed", "project"); a.save(pa)
    sync(a, FilesystemTransport(shared))

    b = Store(base_dir=tmp_path / "b")
    sync(b, FilesystemTransport(shared))         # B now has the item
    pb = b.load("main"); pb.delete_item(item.id); b.save(pb)
    sync(b, FilesystemTransport(shared))         # B pushes the deletion

    sync(a, FilesystemTransport(shared))         # A pulls it
    assert a.load("main").items == []
