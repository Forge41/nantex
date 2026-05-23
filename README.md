# nantex

[![PyPI version](https://img.shields.io/pypi/v/nantex.svg)](https://pypi.org/project/nantex/)
[![Python](https://img.shields.io/pypi/pyversions/nantex.svg)](https://pypi.org/project/nantex/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

LaTeX-to-PDF live preview in your browser — no local LaTeX install needed.

Write `.tex`, save, see the result. That's it.

## How it works

`nantex` watches your `.tex` file, compiles it via the [latex-on-http](https://github.com/YtoTech/latex-on-http) public API, and serves the PDF through a local HTTP server with automatic browser refresh via Server-Sent Events. No Overleaf switching. No Skim install. Just your editor and a browser.

## Install

```bash
# via uv (recommended)
uv tool install nantex

# zero-install run
uvx nantex main.tex

# via pip
pip install nantex
```

## Usage

```bash
nantex main.tex                       # watch mode, opens http://localhost:7474
nantex main.tex --once                # compile once and exit
nantex main.tex --port 8080           # custom port
nantex main.tex --compiler xelatex   # use xelatex instead of pdflatex
nantex main.tex --output ~/out.pdf   # custom output path
nantex main.tex --api https://...    # self-hosted latex-on-http instance
nantex main.tex --share              # print LAN URL for collaborators
nantex main.tex --snippet fig:label  # preview a single figure or line range
nantex --mcp                         # run as MCP server for AI agents
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--compiler` | `pdflatex` | LaTeX compiler: `pdflatex`, `xelatex`, `lualatex` |
| `--api` | `https://latex.ytotech.com/builds/sync` | Compile API endpoint |
| `--output` | `<file>.pdf` | Output PDF path |
| `--port` | `7474` | Preview server port |
| `--once` | off | Compile once and exit |
| `--share` | off | Print local network URL for live collaboration |
| `--snippet` | off | Compile a label (`fig:x`) or line range (`10-25`) in isolation |
| `--mcp` | off | Run as an MCP server for AI agent integration |

## Project config

Add a `.nantex.toml` in your project directory to persist settings:

```toml
compiler = "xelatex"
port     = 7475
```

CLI flags always override the config file.

## Multi-file projects

`nantex` automatically detects `\input{}` and `\include{}` directives, watches all discovered files, and bundles them in the API call. No extra configuration needed.

## Collaboration

```bash
nantex main.tex --share
# Preview: http://localhost:7474
# Share:   http://192.168.0.113:7474  ← anyone on your network can open this
```

## MCP server

Run nantex as an MCP server so AI agents (Claude, etc.) can compile LaTeX autonomously:

```bash
nantex --mcp
```

Exposes two tools: `compile_latex` and `get_compile_status`.

To wire it into Claude Code, add to `.mcp.json`:

```json
{
  "mcpServers": {
    "nantex": {
      "command": "uvx",
      "args": ["nantex", "--mcp"]
    }
  }
}
```

## Examples

Ready-to-run examples are in the [`examples/`](examples/) folder:

```bash
nantex examples/01-hello-world.tex   # minimal quickstart
nantex examples/02-math.tex          # equations, Maxwell's laws, matrices
nantex examples/03-resume.tex        # CV / resume template
nantex examples/04-report.tex        # report with table of contents + tables
```

## Privacy

Your `.tex` file content is sent to the configured API on every compile. For sensitive documents, run a self-hosted [latex-on-http](https://github.com/YtoTech/latex-on-http) instance and point `--api` at it.

## License

MIT
