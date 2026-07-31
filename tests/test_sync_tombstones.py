from paraiso import Paraiso


def test_delete_item_leaves_a_tombstone():
    p = Paraiso("x")
    c = p.capture("thing")
    item = p.file(c, "project")
    p.delete_item(item)
    assert item.id in p.tombstones


def test_discard_leaves_a_tombstone():
    p = Paraiso("x")
    c = p.capture("thing")
    p.discard(c)
    assert c.id in p.tombstones


def test_delete_area_tombstones_area_and_bumps_detached_records():
    p = Paraiso("x")
    area = p.create_area("Work")
    c = p.capture("thing")
    item = p.file(c, "project", area=area)
    obj = p.create_objective("Ship", area=area)
    before_item = item.updated_at
    before_obj = obj.updated_at

    p.delete_area(area)

    assert area.id in p.tombstones
    assert item.updated_at > before_item      # detach propagates as an edit
    assert obj.updated_at > before_obj


def test_file_bumps_capture_updated_at():
    p = Paraiso("x")
    c = p.capture("thing")
    before = c.updated_at
    p.file(c, "project")
    assert c.updated_at > before


def test_update_area_bumps_updated_at():
    p = Paraiso("x")
    area = p.create_area("Work")
    before = area.updated_at
    p.update_area(area, name="Health")
    assert area.updated_at > before


def test_tombstones_survive_roundtrip():
    p = Paraiso("x")
    c = p.capture("thing")
    item = p.file(c, "project")
    p.delete_item(item)
    back = Paraiso.from_dict(p.to_dict())
    assert item.id in back.tombstones
