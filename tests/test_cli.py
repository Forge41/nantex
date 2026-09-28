from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from nantex import cli
from nantex.compiler import CompileError

DOC = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"


@pytest.fixture
def tex(tmp_path):
    path = tmp_path / "main.tex"
    path.write_text(DOC)
    return path


@pytest.fixture
def preview():
    with (
        patch.object(cli, "PreviewServer") as server,
        patch.object(cli.webbrowser, "open") as browser,
        patch.object(cli.watcher_mod, "watch") as watch,
    ):
        yield server, browser, watch


def run(*args):
    return CliRunner().invoke(cli.app, [str(a) for a in args])


def test_once_writes_the_pdf_without_a_preview(tex, preview):
    server, browser, watch = preview
    with patch.object(cli, "latex_compile", return_value=b"%PDF-1.4"):
        result = run(tex, "--once")

    assert result.exit_code == 0, result.output
    assert tex.with_suffix(".pdf").read_bytes() == b"%PDF-1.4"
    server.assert_not_called()
    browser.assert_not_called()
    watch.assert_not_called()


def test_once_exits_nonzero_when_the_compile_fails(tex, preview):
    with patch.object(cli, "latex_compile", side_effect=CompileError("! Undefined control sequence.")):
        result = run(tex, "--once")

    assert result.exit_code == 1
    assert not tex.with_suffix(".pdf").exists()


def test_once_ignores_share(tex, preview):
    with patch.object(cli, "latex_compile", return_value=b"%PDF-1.4"):
        result = run(tex, "--once", "--share")

    assert result.exit_code == 0
    assert "--share is ignored" in result.output


def test_watch_mode_serves_the_preview(tex, preview):
    server, browser, watch = preview
    with patch.object(cli, "latex_compile", return_value=b"%PDF-1.4"):
        result = run(tex)

    assert result.exit_code == 0, result.output
    server.return_value.start.assert_called_once()
    assert server.return_value.notify.call_args.args[0] == "ok"
    browser.assert_called_once_with("http://localhost:7474")
    watch.assert_called_once()
