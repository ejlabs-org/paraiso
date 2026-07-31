import json

from paraiso import Store, portability
from paraiso.cli import main
from paraiso.core import Paraiso


def _app_export():
    return {
        "export_version": 1,
        "account": {"name": "Mansi"},
        "areas": [{"id": "area_1", "name": "Work", "color": "#3f6db0", "tags": ["x"]}],
        "objectives": [{"id": "obj_1", "title": "Ship", "area_id": "area_1", "status": "active"}],
        "items": [
            {"id": "itm_1", "module": "seeds", "title": "Idea",
             "area_id": "area_1", "objective_id": "obj_1", "tags": ["t"]},
            {"id": "itm_2", "module": "project", "title": "Task", "area_id": "area_1"},
        ],
        "inbox": [
            {"raw_content": "open thought", "status": "unprocessed", "source": "manual"},
            {"raw_content": "closed history", "status": "accepted"},
        ],
    }


def test_app_export_import_preserves_links():
    p = portability.from_export(_app_export(), name="mine")
    assert p.name == "mine"
    area = p.areas[0]
    assert area.name == "Work" and area.color == "#3f6db0"

    seed = p.items_in("seed")[0]        # "seeds" module → seed bucket
    assert seed.title == "Idea"
    assert seed.area_id == area.id       # link survived, by id
    assert seed.objective_id == p.objectives[0].id
    assert len(p.items_in("project")) == 1
    # Only open captures come across as Inbox; closed history is dropped.
    assert [c.text for c in p.inbox] == ["open thought"]


def test_import_without_ids_degrades_gracefully():
    data = {
        "export_version": 1,
        "areas": [{"name": "Work"}],  # no id
        "items": [{"module": "project", "title": "T", "area_id": "area_gone"}],
    }
    p = portability.from_export(data)
    assert len(p.areas) == 1
    assert p.items_in("project")[0].area_id is None  # unresolved link dropped, item kept


def test_paraiso_export_roundtrips():
    p = Paraiso("Trip")
    area = p.create_area("Travel")
    c = p.capture("book flights")
    p.file(c, "project", title="Book flights", area=area, tags=["urgent"])

    restored = portability.from_export(p.to_dict())
    item = restored.items_in("project")[0]
    assert item.tags == ["urgent"]
    assert item.area_id == area.id


def test_import_via_cli_creates_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("PARAISO_HOME", str(tmp_path))
    path = tmp_path / "export.json"
    path.write_text(json.dumps(_app_export()), encoding="utf-8")

    assert main(["import", str(path), "--name", "imported"]) == 0

    p = Store(base_dir=tmp_path).current()
    assert p is not None
    assert p.name == "imported"
    assert p.items_in("seed")[0].area_id == "area_1"


def test_export_via_cli_writes_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PARAISO_HOME", str(tmp_path))
    main(["new", "demo"])
    main(["capture", "hello"])
    out = tmp_path / "out.json"
    assert main(["export", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["name"] == "demo"
    assert data["captures"][0]["text"] == "hello"
