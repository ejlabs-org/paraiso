import pytest

import paraiso
from paraiso import Paraiso
from paraiso.util import short_id


def test_short_id_is_fixed_width_regardless_of_source_length():
    assert short_id("itm_652f29e127764a4e") == "itm_652f29e1"   # 16-hex (imported)
    assert short_id("itm_e24af0cdb4e2") == "itm_e24af0cd"       # 12-hex (native)
    assert short_id("area_abc") == "area_abc"                   # shorter than width: unchanged
    assert short_id("weird") == "weird"                         # no prefix: unchanged


def test_resolve_item_by_unique_prefix():
    p = Paraiso("x")
    item = p.add_item("thing", "project")
    # Full id works, and so does any unique prefix (including the short id).
    assert p.get_item(item.id).id == item.id
    assert p.get_item(short_id(item.id)).id == item.id
    assert p.get_item(item.id[:6]).id == item.id


def test_ambiguous_prefix_raises():
    p = Paraiso("x")
    a = p.add_item("a", "project")
    b = p.add_item("b", "project")
    # The shared prefix "itm_" matches both.
    with pytest.raises(paraiso.AmbiguousIdError):
        p.get_item("itm_")
    assert {a.id, b.id}  # both exist


def test_unknown_prefix_raises_not_found():
    p = Paraiso("x")
    with pytest.raises(paraiso.ItemNotFoundError):
        p.get_item("itm_deadbeef")


def test_prefix_resolution_works_for_areas_and_captures():
    p = Paraiso("x")
    area = p.create_area("Health")
    c = p.capture("thing")
    assert p.get_area(short_id(area.id)).id == area.id
    assert p.get_capture(short_id(c.id)).id == c.id


def test_listings_render_short_ids(tmp_path, capsys):
    from paraiso import Store
    from paraiso.cli import build_parser

    store = Store(base_dir=tmp_path)
    store.create("w")
    p = store.current(); p.capture("hello"); store.save(p)
    cid = store.current().inbox[0].id

    args = build_parser().parse_args(["inbox"])
    args.func(args, store)
    out = capsys.readouterr().out

    assert short_id(cid) in out       # short form shown
    assert cid not in out             # full id not shown (native id is longer)
