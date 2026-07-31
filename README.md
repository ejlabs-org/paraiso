# paraiso

[![PyPI](https://img.shields.io/pypi/v/paraiso.svg)](https://pypi.org/project/paraiso/)
[![Python versions](https://img.shields.io/pypi/pyversions/paraiso.svg)](https://pypi.org/project/paraiso/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](pyproject.toml)

An open, dependency-free Python foundation for the **PARAISO** organization
framework: one calm home for everything on your mind.

PARAISO extends Tiago Forte's [PARA method](https://fortelabs.com/blog/para/)
(Projects, Areas, Resources, Archive) with three additions — an **Inbox** for
raw capture, **Seeds** for not-yet ideas, and **Objectives** for direction:

```
P  Projects    Things with a finish line.
A  Areas       Ongoing parts of life you maintain.
R  Resources   Reference you might want later.
A  Archive     Done or dormant, and still findable.
I  Inbox       Where every raw capture lands first.
S  Seeds       Ideas you let grow, with no pressure.
O  Objectives  The direction you're moving toward.
```

This package is **not tied to any app**. It's a shared, framework-first base
other tools can build on. Two principles are baked in:

1. **The user decides.** Capture is separate from sorting; nothing is filed
   until a person says so.
2. **AI is bring-your-own.** Classification is an optional seam you implement
   yourself — the core needs no model, no network, and no dependencies.

## Install

```bash
pip install paraiso
```

Requires Python 3.9+.

## Quickstart

`paraiso` is both an importable **library** and a **command-line tool** — the
same core, two front doors.

As a library:

```python
import paraiso

p = paraiso.Paraiso("Personal")
c = p.capture("call the dentist tomorrow")               # lands in the Inbox
p.file(c, "project", title="Book dentist appointment")   # you decide where it goes
```

As a CLI (state persists under `~/.paraiso`):

```bash
paraiso new personal
paraiso capture "call the dentist tomorrow"
paraiso inbox
paraiso file <cap_id> --bucket project --title "Book dentist appointment"
paraiso show
```

The **library** is in-memory — you choose when to persist, with `Store`. The
**CLI** saves automatically and remembers the active workspace, so you can keep
several paraisos and switch between them. The rest of this README goes deeper
on each.

## Library

```python
import paraiso

p = paraiso.Paraiso("Personal")

# Capture first — no decision required. Everything lands in the Inbox.
c = p.capture("someday: write an essay about calm systems")

# Sort later, when you're calm. You decide the bucket, Area, etc.
writing = p.create_area("Writing", tags=["essay"])
item = p.file(c, "seed", title="Essay: calm systems", area=writing)

p.summary()
# {'name': 'Personal', 'inbox': 0, 'items': 1,
#  'buckets': {'Projects': 0, 'Resources': 0, 'Seeds': 1, 'Archive': 0}, ...}
```

The four fileable buckets are `project`, `resource`, `seed`, `archive`. Areas
and Objectives are cross-cutting: an item may *belong to* an Area and *advance*
an Objective, but you never file into either.

## Multiple workspaces

Keep several paraisos (say `work` and `personal`) and switch between them. They
persist as plain JSON under `~/.paraiso` (override with `$PARAISO_HOME`).

```python
from paraiso import Store

store = Store()
store.create("work")            # becomes active
p = store.current()             # load the active workspace
p.capture("ship the release")
store.save(p)

store.spaces()                  # ['work']
store.use("personal")           # switch active workspace
```

## Bring your own AI

`Classifier` is the extension point. The default `ManualClassifier` suggests
nothing (the user decides). Implement the protocol around any model to get
suggestions, then let a person accept them:

```python
from paraiso import Bucket, Suggestion

class MyLLM:
    def classify(self, capture, *, areas, objectives):
        # ...call your own model, referencing (never inventing) areas/objectives
        return Suggestion(bucket=Bucket.PROJECT, area_id=areas[0].id,
                          rationale="looked like a deliverable")

p = paraiso.Paraiso("Personal", classifier=MyLLM())
suggestion = p.suggest(capture)     # advisory only
if suggestion:
    item = p.accept(capture, suggestion)   # the user confirms
```

A tiny offline `KeywordClassifier` is included as a worked example.

## Command line

```bash
paraiso framework                 # what PARAISO stands for
paraiso new personal              # create + switch to a workspace
paraiso spaces                    # list workspaces (active one starred)
paraiso rename work               # rename the active workspace (or `rename <old> <new>`)
paraiso capture "buy mulch"       # drop a thought in the Inbox
paraiso inbox                     # see what's waiting to be sorted
paraiso area add Health --tags fitness,sleep
paraiso file cap_ab12 --bucket project --title "Book dentist"

# Browse your PARAISO (color-coded in a real terminal)
paraiso projects                  # also: resources, seeds, archive
paraiso tree                      # a colorful overview of everything (clears the screen)
paraiso show                      # quick counts

# Areas & objectives (bare noun lists; add/show/edit)
paraiso area                      # list Areas (numbered, with counts)
paraiso area add Health --tags fitness,sleep
paraiso area show                 # explore one Area (its items by bucket + objectives)
paraiso area edit                 # rename / recolor (from the palette) / retag
paraiso objective                 # list Objectives (`objective add` creates)

# Sort, reclassify, delete
paraiso sort                      # guided: press one key per capture to file it
paraiso move <item_id> project    # reclassify a filed item (add --area to re-home it)
paraiso delete <item_id>          # delete an item (deleting an Area id keeps its items)

# Data portability
paraiso export backup.json        # export the active workspace as JSON
paraiso import export.json --name mine   # import a JSON export (paraiso or a PARA-style app)
```

**Guided sorting.** `paraiso sort` (or `sort` in the shell) walks the Inbox one
capture at a time: press **p / r / s / a** to choose a bucket (a single keypress
in a real terminal), pick an Area from a numbered list (or create one on the
spot), and press Enter to accept the title. `move` and `delete` with no id drop
you into a numbered picker, so you never have to type an id — guided `move` lets
you change an item's bucket **and/or** its Area, choosing "keep" for whichever
you want to leave alone. Deleting is the only destructive action and asks first
(pass `--yes` to skip); deleting an **Area** keeps its items and just detaches
them. `tree` prints the workspace name in an `=====` banner above the buckets.

**Color.** Areas are assigned distinct colors from a calm 7-hue palette (cycling
as you add them); recolor any Area with `area edit`, which offers **only those
predefined colors**, never a free-form hex. Buckets are color-coded too. Output
uses 24-bit ANSI and turns itself off automatically for pipes, `NO_COLOR`, or a
`dumb` terminal — so scripts stay clean.

**Explore & port.** `area show` opens a single Area's page (its items grouped by
bucket, plus objectives); `tree` and the Area page clear the screen for a clean
view. `import` reads either paraiso's own export or a PARA-style app export
(mapping `module` → bucket, e.g. `seeds` → seed) — Area and Objective links
survive when the export includes their ids.

## Interactive shell

Run `paraiso` with no arguments (or `paraiso shell`) to drop into a REPL with
**Tab-completion, command history, and arrow-key editing** — all from the
standard library, no dependencies:

It opens on a calm welcome screen (the PARAISO wordmark in its colors, your
active workspace, and a hint), then you're at the prompt:

```text
paraiso › new personal
paraiso (personal) › capture buy mulch
paraiso (personal) › file <Tab>                    # completes capture ids
paraiso (personal) › file cap_03dc --bucket <Tab>  # → project resource seed archive
paraiso (personal) › sort                          # guided: one keypress per capture
```

The prompt is colored per workspace (each name gets a stable palette color), and
`help` lists commands grouped by category (Workspaces, Capture, Sort, Browse,
Organize, Info); `help <command>` explains one. It runs the exact same commands
as the one-shot CLI — anything you can script, you can also do interactively.

## Status

`0.7.0` — early but usable. The public API (models, `Paraiso`, `Store`,
`Classifier`) is settling; expect additions before `1.0`.

## Related

`paraiso` is framework-first and app-agnostic. If you'd like PARAISO as a calm,
full app — with AI that suggests where each capture belongs — see
[Chiefly](https://chiefly.io), a calm AI "Chief of Mind" built on the same
framework, by the same team ([EJ Labs](https://ejlabs.io)).
