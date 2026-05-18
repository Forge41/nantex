from pathlib import Path
from unittest.mock import MagicMock, patch

from watchdog.events import FileModifiedEvent, FileMovedEvent

from nantex.watcher import _Handler


def _handler(target: str, callback=None):
    cb = callback or MagicMock()
    h = _Handler(target, cb)
    return h, cb


def test_on_modified_matching_calls_change(tmp_path):
    target = str(tmp_path / "main.tex")
    h, cb = _handler(target)

    with patch.object(h, "_schedule") as mock_schedule:
        h.on_modified(FileModifiedEvent(target))
        mock_schedule.assert_called_once()


def test_on_modified_non_matching_no_call(tmp_path):
    target = str(tmp_path / "main.tex")
    other = str(tmp_path / "other.tex")
    h, cb = _handler(target)

    with patch.object(h, "_schedule") as mock_schedule:
        h.on_modified(FileModifiedEvent(other))
        mock_schedule.assert_not_called()


def test_on_moved_matching_dest_calls_change(tmp_path):
    target = str(tmp_path / "main.tex")
    src = str(tmp_path / "main.tex~")
    h, cb = _handler(target)

    with patch.object(h, "_schedule") as mock_schedule:
        h.on_moved(FileMovedEvent(src, target))
        mock_schedule.assert_called_once()


def test_on_moved_non_matching_no_call(tmp_path):
    target = str(tmp_path / "main.tex")
    h, cb = _handler(target)

    with patch.object(h, "_schedule") as mock_schedule:
        h.on_moved(FileMovedEvent(str(tmp_path / "a.tex"), str(tmp_path / "b.tex")))
        mock_schedule.assert_not_called()
