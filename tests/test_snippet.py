import pytest

from nantex.snippet import extract_snippet, build_standalone


# ---------------------------------------------------------------------------
# extract_snippet — line range mode
# ---------------------------------------------------------------------------

SAMPLE_CONTENT = "\n".join(f"line {i}" for i in range(1, 31))  # lines 1-30


def test_line_range_basic():
    result = extract_snippet(SAMPLE_CONTENT, "5-10")
    assert result == "\n".join(f"line {i}" for i in range(5, 11))


def test_line_range_single_line():
    result = extract_snippet(SAMPLE_CONTENT, "7-7")
    assert result == "line 7"


def test_line_range_first_line():
    result = extract_snippet(SAMPLE_CONTENT, "1-1")
    assert result == "line 1"


def test_line_range_last_line():
    result = extract_snippet(SAMPLE_CONTENT, "30-30")
    assert result == "line 30"


def test_line_range_full_content():
    result = extract_snippet(SAMPLE_CONTENT, "1-30")
    assert result == SAMPLE_CONTENT


def test_line_range_out_of_bounds_end():
    result = extract_snippet(SAMPLE_CONTENT, "5-999")
    assert result is None


def test_line_range_start_zero():
    result = extract_snippet(SAMPLE_CONTENT, "0-5")
    assert result is None


def test_line_range_inverted():
    result = extract_snippet(SAMPLE_CONTENT, "10-5")
    assert result is None


# ---------------------------------------------------------------------------
# extract_snippet — label mode
# ---------------------------------------------------------------------------

FIGURE_CONTENT = r"""
\documentclass{article}
\begin{document}
Some text before.
\begin{figure}
  \includegraphics{image.png}
  \caption{A nice figure}
  \label{fig:nice}
\end{figure}
Some text after.
\end{document}
"""

EQUATION_CONTENT = r"""
\documentclass{article}
\begin{document}
\begin{equation}
  E = mc^2
  \label{eq:einstein}
\end{equation}
\end{document}
"""

NESTED_CONTENT = r"""
\begin{tikzpicture}
  \begin{scope}
    \draw (0,0) -- (1,1);
    \label{fig:tikz}
  \end{scope}
\end{tikzpicture}
"""


def test_label_figure():
    result = extract_snippet(FIGURE_CONTENT, "fig:nice")
    assert result is not None
    assert r"\begin{figure}" in result
    assert r"\end{figure}" in result
    assert r"\label{fig:nice}" in result
    assert "Some text before" not in result
    assert "Some text after" not in result


def test_label_equation():
    result = extract_snippet(EQUATION_CONTENT, "eq:einstein")
    assert result is not None
    assert r"\begin{equation}" in result
    assert r"\end{equation}" in result
    assert r"E = mc^2" in result


def test_label_nested_env():
    result = extract_snippet(NESTED_CONTENT, "fig:tikz")
    assert result is not None
    # The label is inside \begin{scope}, so the nearest enclosing env is returned
    assert r"\begin{scope}" in result
    assert r"\end{scope}" in result
    assert r"\label{fig:tikz}" in result


def test_label_not_found():
    result = extract_snippet(FIGURE_CONTENT, "nonexistent:label")
    assert result is None


def test_label_special_chars_in_name():
    content = r"""
\begin{table}
  \label{tab:my-table_2}
\end{table}
"""
    result = extract_snippet(content, "tab:my-table_2")
    assert result is not None
    assert r"\begin{table}" in result
    assert r"\end{table}" in result


def test_label_no_enclosing_env():
    # Label appears in plain text with no surrounding environment
    content = "some text \\label{bare} more text"
    result = extract_snippet(content, "bare")
    assert result is None


# ---------------------------------------------------------------------------
# build_standalone
# ---------------------------------------------------------------------------

SNIPPET = r"\begin{equation} x^2 \end{equation}"


def test_build_standalone_basic():
    doc = build_standalone(SNIPPET)
    assert r"\documentclass[preview]{standalone}" in doc
    assert r"\begin{document}" in doc
    assert r"\end{document}" in doc
    assert SNIPPET in doc


def test_build_standalone_common_packages():
    doc = build_standalone(SNIPPET)
    for pkg in ("amsmath", "amssymb", "graphicx", "tikz", "xcolor"):
        assert f"\\usepackage{{{pkg}}}" in doc


def test_build_standalone_original_packages_included():
    original = r"""
\documentclass{article}
\usepackage{booktabs}
\usepackage[T1]{fontenc}
\begin{document}
content
\end{document}
"""
    doc = build_standalone(SNIPPET, original)
    assert r"\usepackage{booktabs}" in doc
    assert r"\usepackage[T1]{fontenc}" in doc


def test_build_standalone_no_duplicate_packages():
    original = r"""
\usepackage{amsmath}
\usepackage{tikz}
"""
    doc = build_standalone(SNIPPET, original)
    # Each of the common packages that are already in original should not be duplicated
    assert doc.count("\\usepackage{amsmath}") == 1
    assert doc.count("\\usepackage{tikz}") == 1


def test_build_standalone_empty_original():
    doc = build_standalone(SNIPPET, "")
    # Should still include common packages
    assert r"\usepackage{amsmath}" in doc


def test_build_standalone_document_structure():
    doc = build_standalone(SNIPPET)
    lines = doc.splitlines()
    # documentclass must be first non-empty line
    assert lines[0] == r"\documentclass[preview]{standalone}"
    # \begin{document} must come before the snippet
    begin_doc_idx = next(i for i, l in enumerate(lines) if l.strip() == r"\begin{document}")
    snippet_idx = next(i for i, l in enumerate(lines) if SNIPPET in l)
    end_doc_idx = next(i for i, l in enumerate(lines) if l.strip() == r"\end{document}")
    assert begin_doc_idx < snippet_idx < end_doc_idx
