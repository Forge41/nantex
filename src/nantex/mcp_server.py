from fastmcp import FastMCP
from nantex.compiler import compile as latex_compile, CompileError

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
    mcp.run()
