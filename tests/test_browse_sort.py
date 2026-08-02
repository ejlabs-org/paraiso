"""Browse views (projects/resources/seeds/archive and tree) group by Area."""

from paraiso import Store
from paraiso.cli import build_parser


def _seed(tmp_path):
    store = Store(base_dir=tmp_path)
    store.create("w")
    p = store.current()
    beta = p.create_area("Beta")
    alpha = p.create_area("Alpha")
    # Titles chosen so alphabetical-by-title differs from grouped-by-area:
    #   by title:  apple(Beta), mango(orphan), zebra(Alpha)
    #   by area:   zebra(Alpha), apple(Beta), mango(orphan)
    p.add_item("apple", "project", area=beta)
    p.add_item("zebra", "project", area=alpha)
    p.add_item("mango", "project")  # no Area
    store.save(p)
    return store


def _run(argv, store):
    args = build_parser().parse_args(argv)
    return args.func(args, store)


def _order(out, *names):
    return [out.index(n) for n in names]


def test_projects_grouped_by_area_then_orphans(tmp_path, capsys):
    store = _seed(tmp_path)
    _run(["projects"], store)
    out = capsys.readouterr().out
    zebra, apple, mango = _order(out, "zebra", "apple", "mango")
    assert zebra < apple < mango   # Alpha, then Beta, then the area-less item


def test_tree_uses_the_same_order(tmp_path, capsys):
    store = _seed(tmp_path)
    _run(["tree"], store)
    out = capsys.readouterr().out
    zebra, apple, mango = _order(out, "zebra", "apple", "mango")
    assert zebra < apple < mango
