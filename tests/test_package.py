import pytest

import paraiso
from paraiso import Bucket, KeywordClassifier, ManualClassifier, Paraiso, Store


def test_version() -> None:
    assert paraiso.__version__ == "0.9.0"


def test_framework_has_seven_pieces() -> None:
    assert len(paraiso.PIECES) == 7
    assert "".join(p.letter for p in paraiso.PIECES) == "PARAISO"
    assert [b.value for b in Bucket] == ["project", "resource", "seed", "archive"]


def test_bucket_coerces_aliases() -> None:
    assert Bucket.coerce("seeds") is Bucket.SEED
    assert Bucket.coerce("Projects") is Bucket.PROJECT
    with pytest.raises(paraiso.InvalidBucketError):
        Bucket.coerce("nonsense")


def test_area_backwards_compatible_construction() -> None:
    # The original stub allowed Area(id=..., name=..., tags=[...]).
    area = paraiso.Area(id="product", name="Product", tags=["launch"])
    assert area.id == "product"
    assert area.tags == ["launch"]


def test_capture_lands_in_inbox_then_files() -> None:
    p = Paraiso("Personal")
    writing = p.create_area("Writing", tags=["essay"])

    capture = p.capture("someday: essay about calm systems")
    assert capture in p.inbox
    assert p.summary()["inbox"] == 1

    item = p.file(capture, "seed", title="Essay: calm systems", area=writing)
    assert item.bucket is Bucket.SEED
    assert item.area_id == writing.id
    assert item.source_capture_id == capture.id
    # Filing closes the capture: it leaves the Inbox but is retained as lineage.
    assert capture.processed is True
    assert capture.item_id == item.id
    assert p.inbox == []
    assert p.items_in("seed") == [item]
    assert p.items_for_area(writing) == [item]


def test_cannot_file_twice() -> None:
    p = Paraiso("x")
    c = p.capture("thing")
    p.file(c, "project")
    with pytest.raises(paraiso.AlreadyProcessedError):
        p.file(c, "archive")


def test_cross_area_reference_is_validated() -> None:
    p = Paraiso("x")
    c = p.capture("thing")
    with pytest.raises(paraiso.AreaNotFoundError):
        p.file(c, "project", area="area_does_not_exist")


def test_manual_classifier_abstains_but_keyword_suggests() -> None:
    p = Paraiso("x", classifier=ManualClassifier())
    p.create_area("Health", tags=["dentist", "sleep"])
    c = p.capture("call the dentist tomorrow")

    assert p.suggest(c) is None  # user decides by default

    suggestion = p.suggest(c, classifier=KeywordClassifier())
    assert suggestion is not None
    assert suggestion.bucket is Bucket.SEED
    item = p.accept(c, suggestion)
    assert item.area_id == suggestion.area_id


def test_areas_get_cycling_palette_colors() -> None:
    from paraiso import palette

    p = Paraiso("x")
    a1 = p.create_area("One")
    a2 = p.create_area("Two")
    custom = p.create_area("Three", color="#123456")

    assert a1.color == palette.AREA_COLORS[0]
    assert a2.color == palette.AREA_COLORS[1]
    assert custom.color == "#123456"
    # Bucket colors align with the framework graphic (Projects = rust).
    assert palette.BUCKET_COLORS["project"] == "#b0562f"


def test_delete_area_keeps_and_detaches_content() -> None:
    p = Paraiso("x")
    area = p.create_area("Work")
    c = p.capture("thing")
    item = p.file(c, "project", area=area)
    obj = p.create_objective("Ship", area=area)

    p.delete_area(area)

    assert p.areas == []
    assert p.items == [item]          # item kept
    assert item.area_id is None       # detached
    assert obj.area_id is None        # objective detached too


def test_delete_item_is_permanent() -> None:
    p = Paraiso("x")
    c = p.capture("thing")
    item = p.file(c, "project")
    p.delete_item(item)
    assert p.items == []
    assert p.get_capture(c.id).item_id is None  # dangling lineage cleared


def test_update_area_edits_fields() -> None:
    p = Paraiso("x")
    area = p.create_area("Work")
    p.update_area(area, name="Health", color="#2f807a", tags=["sleep"])
    assert area.name == "Health"
    assert area.color == "#2f807a"
    assert area.tags == ["sleep"]


def test_set_item_area_attaches_and_detaches() -> None:
    p = Paraiso("x")
    area = p.create_area("Work")
    c = p.capture("thing")
    item = p.file(c, "seed")
    p.set_item_area(item, area)
    assert item.area_id == area.id
    p.set_item_area(item, None)
    assert item.area_id is None


def test_roundtrip_serialization() -> None:
    p = Paraiso("Trip", "planning")
    area = p.create_area("Travel")
    obj = p.create_objective("Visit Japan", area=area)
    c = p.capture("book flights")
    p.file(c, "project", title="Book flights", area=area, objective=obj, tags=["urgent"])

    restored = Paraiso.from_dict(p.to_dict())
    assert restored.name == "Trip"
    assert len(restored.items) == 1
    assert restored.items[0].tags == ["urgent"]
    assert restored.items_for_objective(obj)[0].title == "Book flights"
    # Area color survives the round-trip.
    assert restored.areas[0].color == area.color


def test_store_multiple_spaces_and_switch(tmp_path) -> None:
    store = Store(base_dir=tmp_path)
    assert store.spaces() == []

    store.create("work")
    store.create("personal")
    assert store.spaces() == ["personal", "work"]
    # Last created stays active; switching changes current().
    assert store.active() == "personal"

    work = store.use("work")
    work.capture("ship the release")
    store.save(work)

    reloaded = store.current()
    assert reloaded is not None
    assert reloaded.name == "work"
    assert reloaded.inbox[0].text == "ship the release"


def test_store_rejects_duplicate_space(tmp_path) -> None:
    store = Store(base_dir=tmp_path)
    store.create("dup")
    with pytest.raises(paraiso.SpaceExistsError):
        store.create("dup")


def test_store_rename_moves_file_and_keeps_active(tmp_path) -> None:
    store = Store(base_dir=tmp_path)
    current = store.create("work")
    current.capture("ship it")
    store.save(current)

    store.rename("work", "Client Acme")

    assert "work" not in store.spaces()
    assert "Client Acme" in store.spaces()
    assert store.active() == "Client Acme"  # active pointer followed the rename
    reloaded = store.current()
    assert reloaded.name == "Client Acme"
    assert reloaded.inbox[0].text == "ship it"  # content preserved


def test_store_rename_rejects_existing_name(tmp_path) -> None:
    store = Store(base_dir=tmp_path)
    store.create("a")
    store.create("b")
    with pytest.raises(paraiso.SpaceExistsError):
        store.rename("a", "b")


def test_store_rename_missing_space(tmp_path) -> None:
    store = Store(base_dir=tmp_path)
    with pytest.raises(paraiso.SpaceNotFoundError):
        store.rename("ghost", "new")
