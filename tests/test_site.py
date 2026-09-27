import inspect
import re
from pathlib import Path

import typer

from nantex import cli, mcp_server

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "site" / "index.html").read_text(encoding="utf-8")


def _marked(attr: str) -> set[str]:
    return set(re.findall(rf"<[^>]*\b{attr}\b[^>]*>([^<]+)<", PAGE))


def test_every_cli_flag_is_documented():
    command = typer.main.get_command(cli.app)
    typer_builtins = {"--install-completion", "--show-completion"}
    flags = {opt for p in command.params for opt in p.opts if opt.startswith("--")} - typer_builtins
    assert flags == _marked("data-flag")


def test_every_example_is_listed():
    assert {p.name for p in (ROOT / "examples").glob("*.tex")} == _marked("data-example")


def test_every_mcp_tool_is_listed():
    tools = re.findall(r"@mcp\.tool\(\)\s*\ndef (\w+)", inspect.getsource(mcp_server))
    assert set(tools) == _marked("data-tool")
