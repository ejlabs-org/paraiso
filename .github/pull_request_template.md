<!-- Thanks for contributing to paraiso! -->

## What & why

<!-- What does this change, and what problem does it solve? -->

## Checklist

- [ ] `pytest` passes
- [ ] `ruff check src/paraiso` is clean
- [ ] Stays **dependency-free** (stdlib only, no network) and Python 3.9+
      (`typing.Optional`/`Union`, not `X | Y`)
- [ ] New/changed behavior has tests
- [ ] If a command was added: defined once in `cli.py`, thin `do_*` wrapper in
      `shell.py`, and the `--help` epilog + shell `help` categories are in sync
- [ ] **CHANGELOG.md** updated under `[Unreleased]` / the pending version

## Notes for reviewers

<!-- Anything worth calling out — tradeoffs, follow-ups, screenshots. -->
