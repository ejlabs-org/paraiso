from paraiso.models import Area, Capture, Objective
from paraiso.util import from_iso


def test_new_records_have_updated_at():
    for rec in (Capture("t"), Area("A"), Objective("O")):
        assert rec.updated_at is not None
        assert rec.updated_at >= rec.created_at


def test_updated_at_survives_roundtrip():
    for cls, rec in ((Capture, Capture("t")), (Area, Area("A")), (Objective, Objective("O"))):
        back = cls.from_dict(rec.to_dict())
        assert back.updated_at == rec.updated_at


def test_missing_updated_at_falls_back_to_created_at():
    # An old export that predates updated_at.
    for cls, data in (
        (Capture, {"id": "cap_1", "text": "t", "created_at": "2020-01-01T00:00:00+00:00"}),
        (Area, {"id": "area_1", "name": "A", "created_at": "2020-01-01T00:00:00+00:00"}),
        (Objective, {"id": "obj_1", "title": "O", "created_at": "2020-01-01T00:00:00+00:00"}),
    ):
        rec = cls.from_dict(data)
        assert rec.updated_at == from_iso("2020-01-01T00:00:00+00:00")
