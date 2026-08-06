# Contributing to paraiso

Thanks for your interest! paraiso is a small, calm, **dependency-free** Python
foundation for the PARAISO organization framework. Contributions that keep it
small and calm are very welcome.

## Development setup

```bash
git clone https://github.com/ejlabs-org/paraiso
cd paraiso
python -m pip install -e ".[dev]"     # installs paraiso + pytest, ruff, build, twine
```

No editable install? The package needs no dependencies, so you can also just run
against the source tree:

```bash
PYTHONPATH=src python -m pytest
```

## Tests and linting

```bash
pytest                    # the whole suite (fast — pure, in-memory, tmp_path)
ruff check src/paraiso    # lint (config lives in pyproject.toml)
```

Both must be green before a PR merges — CI runs them on every push and pull
request across Python 3.9–3.13.

**Never let tests write to the real `~/.paraiso`.** Use `tmp_path` and
`Store(base_dir=tmp_path)` (and set `PARAISO_HOME` to a temp dir for any smoke
run).

## The invariants (please keep these)

These are what make paraiso reusable — a PR that breaks one won't be merged:

- **Zero runtime dependencies — standard library only. No network, no
  databases.** If a feature seems to need a dependency, reconsider the design.
- **Python 3.9+.** Every module starts with `from __future__ import
  annotations`. Use `typing.Optional` / `typing.Union` for *runtime* type
  aliases — not `X | Y`, which 3.9 evaluates at runtime. (This is also why the
  ruff config omits the `UP` rules.)
- **The user decides.** Capture is separate from filing; nothing reaches a
  bucket except through an explicit call. A classifier only ever *suggests*.
- **Presentation stays out of the core.** Color/terminal code lives only in
  `cli.py` / `shell.py` (via `term`), always gated on `term.color_enabled()` so
  pipes and CI get plain text. The core library is presentation-agnostic.
- **Persistence is plain JSON** under `$PARAISO_HOME` (default `~/.paraiso`).

## Making a change

1. Branch off `main` (e.g. `feat/<thing>` or `fix/<thing>`).
2. Write a test first where you can — the suite is fast and drives the
   interactive flows via piped stdin.
3. Keep the command surface small and categorized. If you add a command, define
   it once in `cli.py` and add a thin `do_<cmd>` wrapper in `shell.py`, and keep
   the `--help` epilog and the shell's `help` categories in sync.
4. Update **CHANGELOG.md** under `[Unreleased]` / the pending version.
5. Open a PR against `main`; make sure CI is green.

## Cutting a release (maintainers)

Bump the version in lockstep — the version test enforces it:

- `src/paraiso/_version.py`
- `pyproject.toml` (`[project].version`)
- `tests/test_package.py::test_version`
- the README "Status" line, and move the CHANGELOG section from Unreleased to
  the new version + date.

Then build and publish:

```bash
rm -rf dist build src/*.egg-info
python -m build
twine check dist/*
twine upload dist/*        # PyPI is immutable — always bump before re-publishing
```

## Code of conduct

Be kind and assume good faith. We're here to build a calm little tool together.
