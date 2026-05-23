# nantex

[![PyPI version](https://img.shields.io/pypi/v/nantex.svg)](https://pypi.org/project/nantex/)
[![Python](https://img.shields.io/pypi/pyversions/nantex.svg)](https://pypi.org/project/nantex/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

LaTeX-to-PDF live preview in your browser — no local LaTeX install needed.

Write `.tex`, save, see the result. That's it.

## How it works

`nantex` watches your `.tex` file, compiles it via the [latex-on-http](https://github.com/YtoTech/latex-on-http) public API, and serves the result through a local HTTP server with automatic browser refresh via Server-Sent Events. No Overleaf tab switching. No Skim install. Just your editor and a browser.

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
nantex main.tex                      # watch mode, opens http://localhost:7474
nantex main.tex --once               # compile once and exit
nantex main.tex --port 8080          # custom port
nantex main.tex --compiler xelatex  # use xelatex instead of pdflatex
nantex main.tex --output ~/out.pdf  # custom output path
nantex main.tex --api https://...   # self-hosted latex-on-http instance
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--compiler` | `pdflatex` | LaTeX compiler (`pdflatex`, `xelatex`, `lualatex`) |
| `--api` | `https://latex.ytotech.com/builds/sync` | Compile API endpoint |
| `--output` | `<file>.pdf` | Output PDF path |
| `--port` | `7474` | Preview server port |
| `--once` | off | Compile once and exit (no watch loop) |

## Privacy

Your `.tex` file content is sent to the configured API endpoint on every compile. For sensitive documents, run a self-hosted [latex-on-http](https://github.com/YtoTech/latex-on-http) instance and point `--api` at it.

## Limitations

- Requires internet access to the compile API (or a self-hosted instance).

## Publishing

```bash
uv build
uv publish  # set UV_PUBLISH_TOKEN or use OIDC Trusted Publisher
```

## License

MIT