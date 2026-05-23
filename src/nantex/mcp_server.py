import sys
from fastmcp import FastMCP
from nantex.compiler import compile as latex_compile, CompileError
from nantex import __version__

_BANNER = f"""
\033[1;36m
  ███╗   ██╗ █████╗ ███╗   ██╗████████╗███████╗██╗  ██╗
  ████╗  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔════╝╚██╗██╔╝
  ██╔██╗ ██║███████║██╔██╗ ██║   ██║   █████╗   ╚███╔╝
  ██║╚██╗██║██╔══██║██║╚██╗██║   ██║   ██╔══╝   ██╔██╗
  ██║ ╚████║██║  ██║██║ ╚████║   ██║   ███████╗██╔╝ ██╗
  ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
\033[0m
  \033[1mLaTeX-to-PDF CLI with browser live preview\033[0m
  \033[2mhttps://github.com/Forge41/nantex\033[0m

  \033[36m⬡  Server:\033[0m   nantex v{__version__} (MCP mode)
  \033[36m⬡  Tools:\033[0m    compile_latex · get_compile_status
  \033[36m⬡  Docs:\033[0m     https://pypi.org/project/nantex/
"""

mcp = FastMCP("nantex")
_last_result: dict = {"state": "idle"}

@mcp.tool()
def compile_latex(content: str, compiler: str = "pdflatex", api_url: str = "https://latex.ytotech.com/builds/sync") -> dict:
    """Compile LaTeX content and return structured result. Never raises."""
    global _last_result
    try:
        pdf_bytes = latex_compile(content, compiler, api_url)
        # Save to temp file so caller can access it
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(pdf_bytes)
        tmp.close()
        result = {"success": True, "pdf_path": tmp.name, "errors": [], "message": "Compiled successfully"}
    except CompileError as e:
        result = {"success": False, "pdf_path": None, "errors": [str(e)], "message": str(e)}
    _last_result = result
    return result

@mcp.tool()
def get_compile_status() -> dict:
    """Return the status of the last compile operation."""
    return _last_result

def run():
    print(_BANNER, file=sys.stderr)
    mcp.run(show_banner=False)
