from datetime import timedelta

from paraiso import Paraiso
from paraiso.merge import merge_workspaces
from paraiso.util import now


def _newer(record):
    # Force a strictly-later updated_at without sleeping.
    record.updated_at = now() + timedelta(seconds=5)
    return record


def test_add_only_both_sides_unions():
    a = Paraiso("w"); a.capture("from A")
    b = Paraiso("w"); b.capture("from B")
    merged = merge_workspaces(a, b)
    texts = {c.text for c in merged.captures}
    assert texts == {"from A", "from B"}


def test_edit_collision_newer_wins():
    a = Paraiso("w"); item = a.add_item("orig", "project")
    b = Paraiso.from_dict(a.to_dict())            # same id on both sides
    b_item = b.get_item(item.id)
    b_item.title = "edited on B"; _newer(b_item)
    merged = merge_workspaces(a, b)
    assert merged.get_item(item.id).title == "edited on B"


def test_delete_propagates_via_tombstone():
    a = Paraiso("w"); item = a.add_item("doomed", "project")
    b = Paraiso.from_dict(a.to_dict())
    b.delete_item(item.id)                         # tombstoned on B
    merged = merge_workspaces(a, b)
    assert merged.items == []
    assert item.id in merged.tombstones


def test_edit_beats_stale_delete():
    a = Paraiso("w"); item = a.add_item("keep?", "project")
    b = Paraiso.from_dict(a.to_dict())
    b.delete_item(item.id)                         # delete on B
    edited = a.get_item(item.id)
    edited.title = "still wanted"; _newer(edited)  # later edit on A
    merged = merge_workspaces(a, b)
    assert merged.get_item(item.id).title == "still wanted"


def test_idempotent():
    a = Paraiso("w"); a.add_item("x", "project")
    b = Paraiso.from_dict(a.to_dict())
    once = merge_workspaces(a, b)
    twice = merge_workspaces(once, b)
    assert {i.id for i in once.items} == {i.id for i in twice.items}


def test_convergent_regardless_of_order():
    a = Paraiso("w"); ia = a.add_item("a", "project")
    b = Paraiso("w"); ib = b.add_item("b", "seed")
    ab = merge_workspaces(a, b)
    ba = merge_workspaces(b, a)
    assert {i.id for i in ab.items} == {i.id for i in ba.items} == {ia.id, ib.id}
