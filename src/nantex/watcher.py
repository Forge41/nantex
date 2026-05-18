import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

_DEBOUNCE_S = 0.3


class _Handler(FileSystemEventHandler):
    def __init__(self, target: str, on_change: Callable[[], None]):
        self._target = target
        self._on_change = on_change
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _matches(self, path: str) -> bool:
        return path == self._target

    def _schedule(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(_DEBOUNCE_S, self._on_change)
            self._timer.start()

    def on_modified(self, event):
        if not event.is_directory and self._matches(event.src_path):
            self._schedule()

    def on_moved(self, event):
        if isinstance(event, FileMovedEvent) and self._matches(event.dest_path):
            self._schedule()

    def cancel(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()


def watch(tex_path: str, on_change: Callable[[], None]) -> None:
    resolved = str(Path(tex_path).resolve())
    parent = str(Path(resolved).parent)

    handler = _Handler(resolved, on_change)
    observer = Observer()
    observer.schedule(handler, path=parent, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler.cancel()
        observer.stop()
        observer.join()
