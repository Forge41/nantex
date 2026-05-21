import os
import socket
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from nantex import __version__
from nantex.compiler import CompileError, compile as latex_compile
from nantex.config import load_config
from nantex.linter import lint
from nantex.server import PreviewServer
from nantex import watcher as watcher_mod
from nantex import project as project_mod
from nantex.snippet import extract_snippet, build_standalone

app = typer.Typer(help="nantex — LaTeX live preview in your browser.")
console = Console()
err_console = Console(stderr=True)

DEFAULT_API = "https://latex.ytotech.com/builds/sync"


def _version_callback(value: bool):
    if value:
        typer.echo(f"nantex {__version__}")
        raise typer.Exit()


@app.command()
def main(
    tex_file: Annotated[Optional[Path], typer.Argument(help=".tex file to compile and watch")] = None,
    compiler: Annotated[str, typer.Option("--compiler", help="LaTeX compiler")] = "pdflatex",
    api: Annotated[str, typer.Option("--api", help="Compile API endpoint")] = DEFAULT_API,
    output: Annotated[Optional[Path], typer.Option("--output", help="Output PDF path")] = None,
    port: Annotated[int, typer.Option("--port", help="Preview server port")] = 7474,
    once: Annotated[bool, typer.Option("--once", help="Compile once and exit")] = False,
    share: Annotated[bool, typer.Option("--share", help="Print local network share URL")] = False,
    snippet: Annotated[Optional[str], typer.Option("--snippet", help="Extract and compile a snippet (label or line range '10-25')")] = None,
    version: Annotated[Optional[bool], typer.Option("--version", callback=_version_callback, is_eager=True)] = None,
    mcp: Annotated[bool, typer.Option("--mcp", help="Run as MCP server")] = False,
):
    # --- MCP server mode ---
    if mcp:
        from nantex import mcp_server
        mcp_server.run()
        return

    # --- load project config (.nantex.toml) ---
    cfg = load_config(tex_file.parent if tex_file else Path.cwd())

    # Merge: explicit CLI flag wins; fall back to config value when the flag
    # still holds its default (i.e. the user did not supply it on the CLI).
    if compiler == "pdflatex" and "compiler" in cfg:
        compiler = cfg["compiler"]
    if api == DEFAULT_API and "api" in cfg:
        api = cfg["api"]
    if port == 7474 and "port" in cfg:
        port = int(cfg["port"])
    if output is None and "output" in cfg:
        output = Path(cfg["output"])

    # --- validate input ---
    if tex_file is None:
        err_console.print("[bold red]Error:[/bold red] Provide a .tex file or use --mcp")
        raise typer.Exit(1)

    if not tex_file.exists():
        err_console.print(f"[bold red]Error:[/bold red] File not found: {tex_file}")
        raise typer.Exit(1)

    if compiler not in ("pdflatex", "xelatex", "lualatex"):
        err_console.print(f"[bold red]Error:[/bold red] Unknown compiler '{compiler}'. Choose: pdflatex, xelatex, lualatex")
        raise typer.Exit(1)

    pdf_path = output or tex_file.with_suffix(".pdf")

    if api.startswith("http://"):
        console.print("[yellow][nantex][/yellow] Warning: --api uses HTTP. Document contents will be transmitted unencrypted.")

    # --- resolve root and collect initial resources ---
    root = project_mod.find_root(tex_file.resolve())
    all_paths = project_mod.get_all_paths(root)
    if len(all_paths) > 1:
        console.print(f"[cyan][nantex][/cyan] Multi-file project detected ({len(all_paths)} files), root: {root.name}")

    # --- start preview server ---
    srv = PreviewServer(str(pdf_path), port)
    try:
        srv.start()
    except OSError:
        err_console.print(f"[bold red][nantex][/bold red] Port {port} is already in use. Try: nantex {tex_file.name} --port {port + 1}")
        raise typer.Exit(1)

    # --- compile function ---
    def do_compile() -> bool:
        nonlocal all_paths
        t0 = time.perf_counter()
        raw = tex_file.read_text(encoding="utf-8", errors="replace")

        # --- pre-compile static lint (always on the source file) ---
        lint_errors = lint(raw, tex_file)
        if lint_errors:
            warnings = [e for e in lint_errors if e.severity == "warning"]
            errors = [e for e in lint_errors if e.severity == "error"]
            for w in warnings:
                err_console.print(f"[yellow][nantex lint][/yellow] Line {w.line}: {w.message}")
            if errors:
                formatted = "\n".join(f"  Line {e.line}: {e.message}" for e in errors)
                err_console.print(f"[bold red][nantex lint][/bold red] {len(errors)} error(s):\n{formatted}")
                srv.notify("error", formatted)
                return False

        if snippet is not None:
            # Snippet mode: compile just the extracted fragment as a standalone doc
            console.print(f"[cyan][nantex][/cyan] Snippet mode: {snippet}")
            extracted = extract_snippet(raw, snippet)
            if extracted is None:
                err_console.print(f"[bold red][nantex][/bold red] Snippet not found: {snippet!r}")
                return False
            content = build_standalone(extracted, raw)
            try:
                pdf_bytes = latex_compile(content, compiler, api)
            except CompileError as e:
                elapsed = time.perf_counter() - t0
                err_console.print(f"[bold red][nantex][/bold red] Compile error ({elapsed:.1f}s):\n{e}")
                srv.notify("error", str(e))
                return False
        else:
            # Normal mode: re-collect resources for multi-file support
            resources = project_mod.collect_resources(root)
            all_paths = [Path(r["path"]) for r in resources]
            try:
                pdf_bytes = latex_compile(None, compiler, api, resources=resources)
            except CompileError as e:
                elapsed = time.perf_counter() - t0
                err_console.print(f"[bold red][nantex][/bold red] Compile error ({elapsed:.1f}s):\n{e}")
                srv.notify("error", str(e))
                return False

        # atomic write: temp file in same dir → os.replace
        tmp = pdf_path.with_suffix(".pdf.tmp")
        tmp.write_bytes(pdf_bytes)
        os.replace(tmp, pdf_path)

        elapsed = time.perf_counter() - t0
        srv.notify("ok", f"Compiled in {elapsed:.1f}s")
        console.print(f"[green][nantex][/green] Compiled → {pdf_path} ({elapsed:.1f}s)")
        return True

    do_compile()

    # --- open browser ---
    url = f"http://localhost:{port}"
    console.print(f"[cyan][nantex][/cyan] Preview: {url}")
    if share:
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            local_ip = "127.0.0.1"
        console.print(f"[cyan][nantex][/cyan] Share: http://{local_ip}:{port}")
    webbrowser.open(url)

    if once:
        return

    # --- watch loop ---
    console.print("[dim][nantex][/dim] Watching for changes… (Ctrl+C to stop)")
    watcher_mod.watch([str(p) for p in all_paths], do_compile)
