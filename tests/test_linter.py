"""Tests for the pre-compile static linter (nantex/linter.py)."""
import textwrap
from pathlib import Path

import pytest

from nantex.linter import LintError, lint

# A fake path whose parent is a directory that doesn't contain any .tex files
# (used for \input tests)
FAKE_TEX = Path("/tmp/fake_project/main.tex")


def _lint(content: str, tex_path: Path = FAKE_TEX) -> list[LintError]:
    return lint(textwrap.dedent(content), tex_path)


def _errors(content: str, tex_path: Path = FAKE_TEX) -> list[LintError]:
    return [e for e in _lint(content, tex_path) if e.severity == "error"]


def _warnings(content: str, tex_path: Path = FAKE_TEX) -> list[LintError]:
    return [e for e in _lint(content, tex_path) if e.severity == "warning"]


# ------------------------------------------------------------------ #
# Rule 1: Unclosed environments                                        #
# ------------------------------------------------------------------ #

class TestUnclosedEnvironments:
    def test_no_error_when_balanced(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            Hello
            \end{document}
        """
        errs = _errors(src)
        # No unclosed-env errors (may still have a Missing \end{document} edge — but
        # the dedented text does end with \end{document}, so there should be none)
        env_errors = [e for e in errs if "Unclosed environment" in e.message or "no matching" in e.message]
        assert env_errors == []

    def test_unclosed_itemize(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            \begin{itemize}
            \item Hello
            \end{document}
        """
        errs = _errors(src)
        msgs = [e.message for e in errs]
        assert any("itemize" in m for m in msgs)

    def test_nested_balanced(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            \begin{figure}
            \begin{center}
            content
            \end{center}
            \end{figure}
            \end{document}
        """
        env_errors = [
            e for e in _errors(src)
            if "Unclosed" in e.message or "no matching" in e.message
        ]
        assert env_errors == []

    def test_mismatched_environments(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            \begin{itemize}
            \item x
            \end{enumerate}
            \end{document}
        """
        errs = _errors(src)
        msgs = " ".join(e.message for e in errs)
        # Should flag itemize or enumerate mismatch
        assert "itemize" in msgs or "enumerate" in msgs

    def test_end_without_begin(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            \end{figure}
            \end{document}
        """
        errs = _errors(src)
        msgs = [e.message for e in errs]
        assert any("figure" in m and "no matching" in m for m in msgs)


# ------------------------------------------------------------------ #
# Rule 2: Missing \end{document}                                       #
# ------------------------------------------------------------------ #

class TestMissingEndDocument:
    def test_present(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            Hello world.
            \end{document}
        """
        errs = _errors(src)
        missing = [e for e in errs if "Missing \\end{document}" in e.message]
        assert missing == []

    def test_missing(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            Hello world.
        """
        errs = _errors(src)
        missing = [e for e in errs if "Missing \\end{document}" in e.message]
        assert len(missing) == 1

    def test_missing_no_begin_either(self):
        src = r"""
            \documentclass{article}
            Hello world.
        """
        errs = _errors(src)
        missing = [e for e in errs if "Missing \\end{document}" in e.message]
        assert len(missing) == 1


# ------------------------------------------------------------------ #
# Rule 3: \input{file} where file.tex doesn't exist                   #
# ------------------------------------------------------------------ #

class TestInputFileCheck:
    def test_existing_file(self, tmp_path):
        chapter = tmp_path / "chapter1.tex"
        chapter.write_text("hello")
        main = tmp_path / "main.tex"
        src = r"""
            \documentclass{article}
            \begin{document}
            \input{chapter1}
            \end{document}
        """
        errs = _errors(textwrap.dedent(src), main)
        input_errs = [e for e in errs if "input" in e.message.lower() and "not found" in e.message]
        assert input_errs == []

    def test_missing_file(self, tmp_path):
        main = tmp_path / "main.tex"
        src = r"""
            \documentclass{article}
            \begin{document}
            \input{missing_chapter}
            \end{document}
        """
        errs = _errors(textwrap.dedent(src), main)
        input_errs = [e for e in errs if "missing_chapter" in e.message]
        assert len(input_errs) == 1
        assert input_errs[0].severity == "error"

    def test_existing_file_with_tex_extension(self, tmp_path):
        chapter = tmp_path / "chap.tex"
        chapter.write_text("hello")
        main = tmp_path / "main.tex"
        src = r"""
            \documentclass{article}
            \begin{document}
            \input{chap.tex}
            \end{document}
        """
        errs = _errors(textwrap.dedent(src), main)
        input_errs = [e for e in errs if "chap" in e.message and "not found" in e.message]
        assert input_errs == []

    def test_missing_file_with_tex_extension(self, tmp_path):
        main = tmp_path / "main.tex"
        src = r"""
            \documentclass{article}
            \begin{document}
            \input{nope.tex}
            \end{document}
        """
        errs = _errors(textwrap.dedent(src), main)
        input_errs = [e for e in errs if "nope" in e.message]
        assert len(input_errs) == 1


# ------------------------------------------------------------------ #
# Rule 4: Unmatched braces                                             #
# ------------------------------------------------------------------ #

class TestUnmatchedBraces:
    def test_balanced_braces(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            \textbf{hello}
            \end{document}
        """
        errs = _errors(src)
        brace_errs = [e for e in errs if "brace" in e.message.lower()]
        assert brace_errs == []

    def test_extra_closing_brace(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            hello}
            \end{document}
        """
        errs = _errors(src)
        brace_errs = [e for e in errs if "brace" in e.message.lower()]
        assert len(brace_errs) >= 1
        assert any(e.severity == "error" for e in brace_errs)

    def test_unclosed_brace(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            \textbf{hello
            \end{document}
        """
        errs = _errors(src)
        brace_errs = [e for e in errs if "brace" in e.message.lower()]
        assert len(brace_errs) >= 1

    def test_commented_brace_not_counted(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            hello % this has an { unmatched brace in comment
            \end{document}
        """
        errs = _errors(src)
        brace_errs = [e for e in errs if "brace" in e.message.lower()]
        assert brace_errs == []

    def test_escaped_percent_then_brace(self):
        # \% is a literal percent sign (not a comment), then { is real
        src = r"""
            \documentclass{article}
            \begin{document}
            50\% discount \textbf{here}
            \end{document}
        """
        errs = _errors(src)
        brace_errs = [e for e in errs if "brace" in e.message.lower()]
        assert brace_errs == []


# ------------------------------------------------------------------ #
# Rule 5: Double \\ outside tabular/array/matrix environments          #
# ------------------------------------------------------------------ #

class TestDoubleBackslash:
    def test_double_backslash_in_tabular_no_warning(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            \begin{tabular}{ll}
            A & B \\
            C & D \\
            \end{tabular}
            \end{document}
        """
        warns = _warnings(src)
        dbl_warns = [w for w in warns if "Double" in w.message]
        assert dbl_warns == []

    def test_double_backslash_outside_tabular_warning(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            Hello \\
            World
            \end{document}
        """
        warns = _warnings(src)
        dbl_warns = [w for w in warns if "Double" in w.message]
        assert len(dbl_warns) >= 1
        assert dbl_warns[0].severity == "warning"

    def test_double_backslash_in_align_no_warning(self):
        src = r"""
            \documentclass{article}
            \usepackage{amsmath}
            \begin{document}
            \begin{align}
            x &= 1 \\
            y &= 2
            \end{align}
            \end{document}
        """
        warns = _warnings(src)
        dbl_warns = [w for w in warns if "Double" in w.message]
        assert dbl_warns == []

    def test_double_backslash_in_array_no_warning(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            $\begin{array}{cc} a & b \\ c & d \end{array}$
            \end{document}
        """
        warns = _warnings(src)
        dbl_warns = [w for w in warns if "Double" in w.message]
        assert dbl_warns == []

    def test_double_backslash_outside_is_warning_not_error(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            Line one \\
            Line two
            \end{document}
        """
        all_lint = _lint(src)
        dbl = [e for e in all_lint if "Double" in e.message]
        assert all(e.severity == "warning" for e in dbl)

    def test_double_backslash_line_number(self):
        # The \\ is on line 4 of the dedented content
        src = "\\documentclass{article}\n\\begin{document}\nHello \\\\\nWorld\n\\end{document}\n"
        all_lint = _lint(src)
        dbl = [e for e in all_lint if "Double" in e.message]
        assert len(dbl) >= 1
        assert dbl[0].line == 3  # 1-indexed


# ------------------------------------------------------------------ #
# Integration: clean document produces no errors                       #
# ------------------------------------------------------------------ #

class TestCleanDocument:
    def test_minimal_valid_document(self):
        src = r"""
            \documentclass{article}
            \begin{document}
            Hello, world!
            \end{document}
        """
        all_lint = _lint(src)
        assert all_lint == []

    def test_document_with_nested_envs_and_math(self):
        src = r"""
            \documentclass{article}
            \usepackage{amsmath}
            \begin{document}
            \begin{enumerate}
            \item First
            \item Second
            \begin{align*}
            f(x) &= x^2
            \end{align*}
            \end{enumerate}
            \end{document}
        """
        all_lint = _lint(src)
        assert all_lint == []
