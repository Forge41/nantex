import re


def extract_snippet(content: str, target: str) -> str | None:
    """Extract a snippet from LaTeX content.

    target can be:
    - A label name like "fig:circuit" → find \\label{fig:circuit} and extract
      surrounding \\begin{X}...\\end{X}
    - A line range like "10-25" → extract those lines (1-indexed, inclusive)

    Returns None if target not found.
    """
    # Check if target is a line range (digits-digits)
    line_range_match = re.fullmatch(r"(\d+)-(\d+)", target)
    if line_range_match:
        start = int(line_range_match.group(1))
        end = int(line_range_match.group(2))
        lines = content.splitlines()
        # 1-indexed, inclusive
        if start < 1 or end < start or end > len(lines):
            return None
        return "\n".join(lines[start - 1 : end])

    # Otherwise treat target as a label name
    label_pattern = re.compile(r"\\label\{" + re.escape(target) + r"\}")
    label_match = label_pattern.search(content)
    if label_match is None:
        return None

    label_pos = label_match.start()

    # Walk backwards to find the enclosing \begin{X}
    begin_pattern = re.compile(r"\\begin\{([^}]+)\}")
    begin_match = None
    env_name = None
    for m in begin_pattern.finditer(content):
        if m.start() <= label_pos:
            begin_match = m
            env_name = m.group(1)
        else:
            break

    if begin_match is None or env_name is None:
        return None

    # Walk forwards from \begin to find matching \end{env_name}
    # Use a nesting counter to handle nested environments of the same name
    end_pattern = re.compile(
        r"\\(begin|end)\{" + re.escape(env_name) + r"\}"
    )
    depth = 0
    end_match = None
    for m in end_pattern.finditer(content, begin_match.start()):
        if m.group(1) == "begin":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                end_match = m
                break

    if end_match is None:
        return None

    return content[begin_match.start() : end_match.end()]


def build_standalone(snippet: str, original_content: str = "") -> str:
    """Wrap snippet in a minimal standalone document.

    Extracts \\usepackage lines from original_content for the preamble.
    Uses \\documentclass[preview]{standalone} as the base.
    Always includes common packages: amsmath, amssymb, graphicx, tikz, xcolor.
    """
    common_packages = ["amsmath", "amssymb", "graphicx", "tikz", "xcolor"]

    # Collect \usepackage lines from the original document
    usepackage_lines: list[str] = []
    already_included: set[str] = set()

    if original_content:
        for line in original_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("\\usepackage"):
                # Extract package name(s) for dedup tracking
                pkg_match = re.search(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", stripped)
                if pkg_match:
                    pkgs = [p.strip() for p in pkg_match.group(1).split(",")]
                    for pkg in pkgs:
                        already_included.add(pkg)
                usepackage_lines.append(stripped)

    # Add common packages that aren't already present
    extra_lines = []
    for pkg in common_packages:
        if pkg not in already_included:
            extra_lines.append(f"\\usepackage{{{pkg}}}")

    preamble_lines = extra_lines + usepackage_lines

    preamble = "\n".join(preamble_lines)
    if preamble:
        preamble = "\n" + preamble

    return (
        "\\documentclass[preview]{standalone}"
        + preamble
        + "\n\\begin{document}\n"
        + snippet
        + "\n\\end{document}\n"
    )
