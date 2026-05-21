"""Tests for nantex.config.load_config."""

import pytest
from pathlib import Path

from nantex.config import load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_toml(directory: Path, content: str) -> Path:
    """Write a .nantex.toml file in *directory* and return its path."""
    cfg_file = directory / ".nantex.toml"
    cfg_file.write_text(content, encoding="utf-8")
    return cfg_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_happy_path_compiler(tmp_path):
    """A .nantex.toml with compiler = 'xelatex' is parsed correctly."""
    _write_toml(tmp_path, 'compiler = "xelatex"\n')
    result = load_config(tmp_path)
    assert result == {"compiler": "xelatex"}


def test_no_config_returns_empty_dict(tmp_path):
    """When no .nantex.toml exists anywhere, an empty dict is returned."""
    # tmp_path is an isolated temp directory — no config file present.
    result = load_config(tmp_path)
    assert result == {}


def test_walk_up_finds_parent_config(tmp_path):
    """Config in a parent directory is found when starting from a subdirectory."""
    _write_toml(tmp_path, 'compiler = "lualatex"\n')
    subdir = tmp_path / "project" / "src"
    subdir.mkdir(parents=True)
    result = load_config(subdir)
    assert result == {"compiler": "lualatex"}


def test_malformed_toml_raises_system_exit(tmp_path):
    """A malformed .nantex.toml causes SystemExit with a clear message."""
    _write_toml(tmp_path, "compiler = [unterminated\n")
    with pytest.raises(SystemExit) as exc_info:
        load_config(tmp_path)
    assert "malformed" in str(exc_info.value).lower() or ".nantex.toml" in str(exc_info.value)


def test_all_supported_keys(tmp_path):
    """All four supported keys are parsed and returned correctly."""
    content = (
        'compiler = "xelatex"\n'
        'api = "https://example.com/build"\n'
        'port = 8080\n'
        'output = "out/document.pdf"\n'
    )
    _write_toml(tmp_path, content)
    result = load_config(tmp_path)
    assert result == {
        "compiler": "xelatex",
        "api": "https://example.com/build",
        "port": 8080,
        "output": "out/document.pdf",
    }


def test_unknown_keys_are_ignored(tmp_path):
    """Keys not in the supported set are silently dropped."""
    _write_toml(tmp_path, 'compiler = "pdflatex"\nunknown_key = "value"\n')
    result = load_config(tmp_path)
    assert result == {"compiler": "pdflatex"}
    assert "unknown_key" not in result


def test_nearest_config_wins(tmp_path):
    """When both a parent and a child directory have a config, the child wins."""
    _write_toml(tmp_path, 'compiler = "pdflatex"\n')
    subdir = tmp_path / "sub"
    subdir.mkdir()
    _write_toml(subdir, 'compiler = "xelatex"\n')
    result = load_config(subdir)
    assert result == {"compiler": "xelatex"}
