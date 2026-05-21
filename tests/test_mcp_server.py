"""Tests for the MCP server tools."""
import pytest
from unittest.mock import patch, MagicMock
import nantex.mcp_server as mcp_module
from nantex.compiler import CompileError


def _reset_state():
    """Reset the module-level _last_result to idle state."""
    mcp_module._last_result = {"state": "idle"}


class TestCompileLatex:
    def setup_method(self):
        _reset_state()

    def test_happy_path_returns_success(self):
        """compile_latex returns success=True and a pdf_path when compile succeeds."""
        fake_pdf = b"%PDF-1.4 fake content"
        with patch("nantex.mcp_server.latex_compile", return_value=fake_pdf):
            result = mcp_module.compile_latex("\\documentclass{article}\\begin{document}Hello\\end{document}")

        assert result["success"] is True
        assert result["pdf_path"] is not None
        assert result["errors"] == []
        assert result["message"] == "Compiled successfully"

    def test_happy_path_pdf_file_written(self, tmp_path):
        """The pdf_path from a successful compile actually exists on disk."""
        fake_pdf = b"%PDF-1.4 fake content"
        with patch("nantex.mcp_server.latex_compile", return_value=fake_pdf):
            result = mcp_module.compile_latex("\\documentclass{article}\\begin{document}Hello\\end{document}")

        import os
        assert os.path.exists(result["pdf_path"])

    def test_compile_error_returns_failure(self):
        """compile_latex returns success=False with errors list when CompileError is raised."""
        error_msg = "! Undefined control sequence."
        with patch("nantex.mcp_server.latex_compile", side_effect=CompileError(error_msg)):
            result = mcp_module.compile_latex("\\bad latex content")

        assert result["success"] is False
        assert result["pdf_path"] is None
        assert error_msg in result["errors"]
        assert error_msg in result["message"]

    def test_compile_error_errors_list_populated(self):
        """The errors list contains exactly the error message string."""
        error_msg = "! Missing $ inserted."
        with patch("nantex.mcp_server.latex_compile", side_effect=CompileError(error_msg)):
            result = mcp_module.compile_latex("bad content")

        assert len(result["errors"]) == 1
        assert result["errors"][0] == error_msg

    def test_compile_uses_default_compiler(self):
        """compile_latex passes default compiler=pdflatex when not specified."""
        fake_pdf = b"%PDF"
        with patch("nantex.mcp_server.latex_compile", return_value=fake_pdf) as mock_compile:
            mcp_module.compile_latex("content")

        mock_compile.assert_called_once()
        _, compiler_arg, _ = mock_compile.call_args[0]
        assert compiler_arg == "pdflatex"

    def test_compile_passes_custom_compiler(self):
        """compile_latex passes through a custom compiler argument."""
        fake_pdf = b"%PDF"
        with patch("nantex.mcp_server.latex_compile", return_value=fake_pdf) as mock_compile:
            mcp_module.compile_latex("content", compiler="xelatex")

        _, compiler_arg, _ = mock_compile.call_args[0]
        assert compiler_arg == "xelatex"

    def test_compile_passes_custom_api_url(self):
        """compile_latex passes through a custom api_url argument."""
        fake_pdf = b"%PDF"
        custom_url = "https://custom.api/builds/sync"
        with patch("nantex.mcp_server.latex_compile", return_value=fake_pdf) as mock_compile:
            mcp_module.compile_latex("content", api_url=custom_url)

        _, _, api_arg = mock_compile.call_args[0]
        assert api_arg == custom_url


class TestGetCompileStatus:
    def setup_method(self):
        _reset_state()

    def test_idle_state_before_any_compile(self):
        """get_compile_status returns idle state when no compile has been run."""
        result = mcp_module.get_compile_status()
        assert result == {"state": "idle"}

    def test_status_after_successful_compile(self):
        """get_compile_status returns last successful compile result."""
        fake_pdf = b"%PDF"
        with patch("nantex.mcp_server.latex_compile", return_value=fake_pdf):
            compile_result = mcp_module.compile_latex("content")

        status = mcp_module.get_compile_status()
        assert status == compile_result
        assert status["success"] is True

    def test_status_after_failed_compile(self):
        """get_compile_status returns last failed compile result."""
        error_msg = "! Error in LaTeX"
        with patch("nantex.mcp_server.latex_compile", side_effect=CompileError(error_msg)):
            compile_result = mcp_module.compile_latex("bad content")

        status = mcp_module.get_compile_status()
        assert status == compile_result
        assert status["success"] is False

    def test_status_reflects_latest_compile(self):
        """get_compile_status always reflects the most recent compile operation."""
        fake_pdf = b"%PDF"
        error_msg = "! Some error"

        # First compile: success
        with patch("nantex.mcp_server.latex_compile", return_value=fake_pdf):
            mcp_module.compile_latex("good content")

        # Second compile: failure
        with patch("nantex.mcp_server.latex_compile", side_effect=CompileError(error_msg)):
            mcp_module.compile_latex("bad content")

        status = mcp_module.get_compile_status()
        assert status["success"] is False
        assert error_msg in status["errors"]
