"""On-disk storage for one or many PARAISO workspaces.

A :class:`Store` is a directory of JSON files, one per workspace, plus a small
``config.json`` remembering which workspace is *active*. This is what lets a
person keep several paraisos (say ``work`` and ``personal``) and switch between
them.

    store = Store()                 # defaults to ~/.paraiso
    store.create("personal")        # becomes active
    p = store.current()             # load the active one
    p.capture("buy mulch")
    store.save(p)

Storage is plain JSON via the standard library — no database, no dependencies.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from .classifier import Classifier
from .core import Paraiso
from .errors import SpaceExistsError, SpaceNotFoundError

_CONFIG_NAME = "config.json"


def _slug(name: str) -> str:
    """A filesystem-safe stem for a workspace name."""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "workspace"


class Store:
    """A directory of PARAISO workspaces."""

    def __init__(self, base_dir: Optional[os.PathLike | str] = None) -> None:
        base = base_dir or os.environ.get("PARAISO_HOME") or (Path.home() / ".paraiso")
        self.base_dir = Path(base)

    # -- Listing / existence ----------------------------------------------

    def spaces(self) -> list[str]:
        """Names of every workspace in the store, sorted."""
        if not self.base_dir.exists():
            return []
        names = []
        for path in self.base_dir.glob("*.json"):
            if path.name == _CONFIG_NAME:
                continue
            try:
                names.append(json.loads(path.read_text(encoding="utf-8"))["name"])
            except (json.JSONDecodeError, KeyError, OSError):
                continue
        return sorted(names)

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    # -- Create / load / save / delete ------------------------------------

    def create(self, name: str, description: str = "", *, make_active: bool = True) -> Paraiso:
        """Create a new, empty workspace. Errors if the name is taken."""
        if self.exists(name):
            raise SpaceExistsError(f"A workspace named {name!r} already exists.")
        paraiso = Paraiso(name, description)
        self.save(paraiso)
        if make_active or self.active() is None:
            self.set_active(name)
        return paraiso

    def load(self, name: str, *, classifier: Optional[Classifier] = None) -> Paraiso:
        """Load a workspace by name."""
        path = self._path(name)
        if not path.exists():
            raise SpaceNotFoundError(f"No workspace named {name!r}.")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Paraiso.from_dict(data, classifier=classifier)

    def save(self, paraiso: Paraiso) -> Path:
        """Write a workspace to disk, creating the store directory if needed."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(paraiso.name)
        path.write_text(
            json.dumps(paraiso.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def delete(self, name: str) -> None:
        path = self._path(name)
        if not path.exists():
            raise SpaceNotFoundError(f"No workspace named {name!r}.")
        path.unlink()
        if self.active() == name:
            self._write_config({})

    def rename(self, old_name: str, new_name: str) -> Paraiso:
        """Rename a workspace: update its display name, move its file, and keep
        it active if it was."""
        if not self.exists(old_name):
            raise SpaceNotFoundError(f"No workspace named {old_name!r}.")
        renaming_same_file = _slug(new_name) == _slug(old_name)
        if self.exists(new_name) and not renaming_same_file:
            raise SpaceExistsError(f"A workspace named {new_name!r} already exists.")
        was_active = self.active() == old_name
        old_path = self._path(old_name)

        paraiso = self.load(old_name)
        paraiso.name = new_name
        self.save(paraiso)  # writes under the new slug's filename
        if not renaming_same_file and old_path.exists():
            old_path.unlink()
        if was_active:
            self.set_active(new_name)
        return paraiso

    # -- Active workspace --------------------------------------------------

    def active(self) -> Optional[str]:
        """Name of the currently selected workspace, if any."""
        return self._read_config().get("active")

    def set_active(self, name: str) -> None:
        if not self.exists(name):
            raise SpaceNotFoundError(f"No workspace named {name!r}.")
        config = self._read_config()
        config["active"] = name
        self._write_config(config)

    def use(self, name: str, *, classifier: Optional[Classifier] = None) -> Paraiso:
        """Make a workspace active and return it loaded."""
        self.set_active(name)
        return self.load(name, classifier=classifier)

    # -- Sync settings -----------------------------------------------------

    def sync_settings(self) -> dict:
        """Remembered sync transport + path, if any."""
        return self._read_config().get("sync", {})

    def set_sync_settings(self, settings: dict) -> None:
        config = self._read_config()
        config["sync"] = settings
        self._write_config(config)

    def current(self, *, classifier: Optional[Classifier] = None) -> Optional[Paraiso]:
        """Load the active workspace, or ``None`` if none is selected."""
        name = self.active()
        if name is None or not self.exists(name):
            return None
        return self.load(name, classifier=classifier)

    # -- Internals ---------------------------------------------------------

    def _path(self, name: str) -> Path:
        return self.base_dir / f"{_slug(name)}.json"

    def _config_path(self) -> Path:
        return self.base_dir / _CONFIG_NAME

    def _read_config(self) -> dict:
        path = self._config_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_config(self, config: dict) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._config_path().write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
