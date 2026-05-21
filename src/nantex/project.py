import re
from pathlib import Path


# Magic comment pattern: % !TEX root = <file>
_TEX_ROOT_RE = re.compile(r"^\s*%\s*!TEX\s+root\s*=\s*(.+)$", re.IGNORECASE | re.MULTILINE)

# \input{...} and \include{...} patterns
_INCLUDE_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")


def find_root(start: Path) -> Path:
    """Check % !TEX root = magic comment, else scan for \\documentclass, else return start."""
    start = start.resolve()

    # Check magic comment in the start file
    try:
        text = start.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return start

    m = _TEX_ROOT_RE.search(text)
    if m:
        candidate = (start.parent / m.group(1).strip()).resolve()
        if candidate.exists():
            return candidate

    # If the start file itself has \documentclass, it is the root
    if "\\documentclass" in text:
        return start

    # Walk up looking for a file with \documentclass
    for parent in [start.parent] + list(start.parents):
        for tex_file in sorted(parent.glob("*.tex")):
            try:
                content = tex_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "\\documentclass" in content:
                return tex_file.resolve()

    return start


def collect_resources(root: Path, visited: set | None = None) -> list[dict]:
    """Recursively parse \\input{}/\\include{} and return resources list for API.

    Returns [{"main": True/False, "content": str, "path": str}, ...]
    Root file has main=True. Guard against circular includes with visited set.
    """
    root = root.resolve()
    is_root_call = visited is None
    if visited is None:
        visited = set()

    if root in visited:
        return []
    visited.add(root)

    try:
        content = root.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    resources = [{"main": is_root_call, "content": content, "path": str(root)}]

    for match in _INCLUDE_RE.finditer(content):
        inc_path_str = match.group(1).strip()
        # Add .tex extension if missing
        if not inc_path_str.endswith(".tex"):
            inc_path_str += ".tex"
        inc_path = (root.parent / inc_path_str).resolve()
        if inc_path.exists():
            resources.extend(collect_resources(inc_path, visited))

    return resources


def get_all_paths(root: Path) -> list[Path]:
    """Return root + all discovered dependency paths for the watcher."""
    resources = collect_resources(root)
    return [Path(r["path"]) for r in resources]
