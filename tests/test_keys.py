import io

import pytest

from paraiso import interactive
from paraiso.interactive import _normalize_key


def test_normalize_key_maps_escape_to_esc():
    assert _normalize_key("\x1b") == "esc"


def test_normalize_key_still_handles_enter_and_ctrl():
    assert _normalize_key("\r") == ""
    assert _normalize_key("\n") == ""
    assert _normalize_key("") == ""
    assert _normalize_key("P") == "p"
    for ctrl in ("\x03", "\x04"):
        with pytest.raises(KeyboardInterrupt):
            _normalize_key(ctrl)


def test_read_key_fallback_returns_esc(monkeypatch):
    # No TTY (StringIO.isatty() is False) → the line-based fallback path.
    monkeypatch.setattr("sys.stdin", io.StringIO("\x1b\n"))
    assert interactive.read_key() == "esc"


def test_cancel_sentinel_exists():
    assert interactive.CANCEL is not None
    assert interactive.CANCEL is not interactive.KEEP
