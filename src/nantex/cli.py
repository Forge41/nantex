import os
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from nantex import __version__
from nantex.compiler import CompileError, compile as latex_compile
from nantex.server import PreviewServer
from nantex import watcher as watcher_mod

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
    tex_file: Annotated[Path, typer.Argument(help=".tex file to compile and watch")],
    compiler: Annotated[str, typer.Option("--compiler", help="LaTeX compiler")] = "pdflatex",
    api: Annotated[str, typer.Option("--api", help="Compile API endpoint")] = DEFAULT_API,
    output: Annotated[Optional[Path], typer.Option("--output", help="Output PDF path")] = None,
    port: Annotated[int, typer.Option("--port", help="Preview server port")] = 7474,
    once: Annotated[bool, typer.Option("--once", help="Compile once and exit")] = False,
    version: Annotated[Optional[bool], typer.Option("--version", callback=_version_callback, is_eager=True)] = None,
):
    # --- validate input ---
    if not tex_file.exists():
        err_console.print(f"[bold red]Error:[/bold red] File not found: {tex_file}")
        raise typer.Exit(1)

    if compiler not in ("pdflatex", "xelatex", "lualatex"):
        err_console.print(f"[bold red]Error:[/bold red] Unknown compiler '{compiler}'. Choose: pdflatex, xelatex, lualatex")
        raise typer.Exit(1)

    pdf_path = output or tex_file.with_suffix(".pdf")

    # --- warnings ---
    source = tex_file.read_text(encoding="utf-8", errors="replace")
    if "\\input{" in source or "\\include{" in source:
        console.print("[yellow][nantex][/yellow] Warning: \\\\input{}/\\\\include{} detected — multi-file projects not supported in v1. Included files will be missing.")

    if api.startswith("http://"):
        console.print("[yellow][nantex][/yellow] Warning: --api uses HTTP. Document contents will be transmitted unencrypted.")

    # --- start preview server ---
    srv = PreviewServer(str(pdf_path), port)
    try:
        srv.start()
    except OSError:
        err_console.print(f"[bold red][nantex][/bold red] Port {port} is already in use. Try: nantex {tex_file.name} --port {port + 1}")
        raise typer.Exit(1)

    # --- first compile ---
    def do_compile() -> bool:
        t0 = time.perf_counter()
        content = tex_file.read_text(encoding="utf-8", errors="replace")
        try:
            pdf_bytes = latex_compile(content, compiler, api)
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
    webbrowser.open(url)

    if once:
        return

    # --- watch loop ---
    console.print("[dim][nantex][/dim] Watching for changes… (Ctrl+C to stop)")
    watcher_mod.watch(str(tex_file), do_compile)
