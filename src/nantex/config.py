"""Load project configuration from .nantex.toml.

Walks up the directory tree from a given starting directory looking for a
``.nantex.toml`` file and returns its contents as a plain dict.  Uses the
stdlib ``tomllib`` module (Python 3.11+) so no extra dependency is needed.

Supported top-level keys (all optional):
  compiler  – LaTeX compiler to use (e.g. "xelatex")
  api       – compile API endpoint URL
  port      – preview server port (integer)
  output    – output PDF path (string)
"""

import sys
import tomllib
from pathlib import Path

_SUPPORTED_KEYS = {"compiler", "api", "port", "output"}
_CONFIG_FILENAME = ".nantex.toml"


def load_config(start_dir: Path) -> dict:
    """Walk up from *start_dir* and return the first ``.nantex.toml`` found.

    Returns an empty dict when no config file exists anywhere in the tree.
    Raises ``SystemExit`` with a human-readable message when the file exists
    but contains invalid TOML.
    """
    current = start_dir.resolve()
    while True:
        candidate = current / _CONFIG_FILENAME
        if candidate.is_file():
            try:
                with candidate.open("rb") as fh:
                    data = tomllib.load(fh)
            except tomllib.TOMLDecodeError as exc:
                sys.exit(f"[nantex] Error: malformed {candidate}: {exc}")
            # Return only the keys we recognise so callers get a clean dict.
            return {k: v for k, v in data.items() if k in _SUPPORTED_KEYS}
        parent = current.parent
        if parent == current:
            # Reached filesystem root without finding a config.
            return {}
        current = parent
