from unittest.mock import MagicMock, patch

import pytest
import requests as req_lib

from nantex.compiler import CompileError, compile


API = "https://latex.ytotech.com/builds/sync"
PDF_BYTES = b"%PDF-1.7 fake"

LOG_WITH_ERROR = (
    "This is pdfTeX\n"
    "! Missing } inserted.\n"
    "l.47 \\textbf{hello\n"
    "more noise\n"
)


def _mock_response(status: int, content: bytes = b"", json_body: dict | None = None):
    m = MagicMock()
    m.status_code = status
    m.content = content
    m.text = content.decode("utf-8", errors="replace") if content else ""
    if json_body is not None:
        m.json.return_value = json_body
    return m


def test_happy_path():
    with patch("nantex.compiler.requests.post", return_value=_mock_response(201, PDF_BYTES)):
        result = compile("\\documentclass{article}", "pdflatex", API)
    assert result == PDF_BYTES


def test_compile_error_400():
    body = {"log_files": {"__main_document__.log": LOG_WITH_ERROR}}
    with patch("nantex.compiler.requests.post", return_value=_mock_response(400, json_body=body)):
        with pytest.raises(CompileError) as exc:
            compile("bad tex", "pdflatex", API)
    msg = str(exc.value)
    assert "Missing } inserted" in msg
    assert "l.47" in msg


def test_network_error():
    with patch("nantex.compiler.requests.post", side_effect=req_lib.exceptions.ConnectionError):
        with pytest.raises(CompileError) as exc:
            compile("...", "pdflatex", API)
    assert "unreachable" in str(exc.value).lower()


def test_timeout():
    with patch("nantex.compiler.requests.post", side_effect=req_lib.exceptions.Timeout):
        with pytest.raises(CompileError) as exc:
            compile("...", "pdflatex", API)
    assert "timed out" in str(exc.value).lower()


def test_non_201_400_status():
    with patch("nantex.compiler.requests.post", return_value=_mock_response(500, b"internal error")):
        with pytest.raises(CompileError) as exc:
            compile("...", "pdflatex", API)
    assert "500" in str(exc.value)
