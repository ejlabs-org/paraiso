# Changelog

All notable changes to **paraiso** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(with the usual `0.x` latitude — anything may still change before `1.0`).

## [0.9.0] — Unreleased

### Added
- **Per-area bucket views**: `projects` / `resources` / `seeds` / `archive`
  accept `-a` — bare `-a` opens an Area picker (with an "all areas" option),
  `-a <id-or-prefix>` filters directly.
- **Consistent short ids**: ids display at a fixed width (`prefix_` + 8 chars)
  so listings align, and any command that takes an id accepts a **unique
  prefix** (git-style). Ambiguous prefixes raise `AmbiguousIdError`.
- `help` / `?` clears the screen on a real terminal, like `tree`.

### Changed
- **Sort flow reordered** to confirm title → pick Area → choose bucket, and is
  now keypress-first: a per-capture action bar (`[Enter] file / [s] skip /
  [d] discard / [Esc] quit`), a `n/total` progress counter, and a
  `→ Bucket · Area` confirmation.
- **Esc cancels the current flow** everywhere — mid-filing it skips that
  capture; at the action bar it ends the sort; `move` / `edit` honor it too.
  Arrow/nav escape sequences are drained so they don't read as a bare Esc.
- **Browse views share one order**: `projects` / `resources` / `seeds` /
  `archive` and `tree` all group items by Area (then title), consistently.

## [0.8.0] — 2026-07-31

### Added
- **Two-way sync across machines.** A record-level last-writer-wins merge with
  tombstones so adds, edits, *and* deletes all propagate; a whole-install
  snapshot format; a `Transport` protocol seam (with a stdlib
  `FilesystemTransport`); and `backup` / `restore` / `sync` commands. External
  services ship as opt-in add-on packages via the `paraiso.transports` entry
  point — the core stays dependency-free and never touches the network.
- `updated_at` on every model; the pure `merge_workspaces()` primitive is
  exported for building custom flows.

## [0.7.0]

Earlier history predates this changelog — see the git log for details.

[0.9.0]: https://github.com/ejlabs-org/paraiso
[0.8.0]: https://github.com/ejlabs-org/paraiso
[0.7.0]: https://github.com/ejlabs-org/paraiso
