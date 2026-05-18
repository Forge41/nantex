import json
import time
from pathlib import Path

import pytest

from nantex.server import PreviewServer


def _free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server_with_pdf(tmp_path):
    pdf = tmp_path / "out.pdf"
    pdf.write_bytes(b"%PDF-1.7 fake")
    port = _free_port()
    srv = PreviewServer(str(pdf), port)
    srv.start()
    return srv, port, pdf


@pytest.fixture
def server_no_pdf(tmp_path):
    pdf = tmp_path / "out.pdf"   # does NOT exist yet
    port = _free_port()
    srv = PreviewServer(str(pdf), port)
    srv.start()
    return srv, port, pdf


def _get(port, path):
    import urllib.request
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def test_pdf_exists_returns_200(server_with_pdf):
    srv, port, _ = server_with_pdf
    status, body, ct = _get(port, "/output.pdf")
    assert status == 200
    assert b"%PDF" in body
    assert "application/pdf" in ct


def test_pdf_missing_returns_404(server_no_pdf):
    srv, port, _ = server_no_pdf
    import urllib.error
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(port, "/output.pdf")
    assert exc.value.code == 404


def test_status_after_ok_notify(server_no_pdf):
    srv, port, _ = server_no_pdf
    srv.notify("ok", "Compiled in 1.2s")
    time.sleep(0.05)
    status, body, _ = _get(port, "/status")
    data = json.loads(body)
    assert data["state"] == "ok"
    assert "Compiled" in data["message"]


def test_status_after_error_notify(server_no_pdf):
    srv, port, _ = server_no_pdf
    srv.notify("error", "Missing }")
    time.sleep(0.05)
    status, body, _ = _get(port, "/status")
    data = json.loads(body)
    assert data["state"] == "error"
    assert "Missing" in data["message"]


def test_notify_puts_to_queue(server_no_pdf):
    srv, port, _ = server_no_pdf
    srv.notify("ok", "test")
    item = srv._queue.get(timeout=1)
    assert item["state"] == "ok"
