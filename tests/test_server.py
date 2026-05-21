import json
import queue
import threading
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


def test_notify_puts_to_client_queues(server_no_pdf):
    """notify() fans out to all registered client queues."""
    srv, port, _ = server_no_pdf
    q1: queue.Queue = queue.Queue()
    q2: queue.Queue = queue.Queue()
    with srv._clients_lock:
        srv._clients.append(q1)
        srv._clients.append(q2)
    srv.notify("ok", "test")
    item1 = q1.get(timeout=1)
    item2 = q2.get(timeout=1)
    assert item1["state"] == "ok"
    assert item2["state"] == "ok"


def test_two_clients_both_receive_notify(server_no_pdf):
    """Two independently registered client queues both receive a notify payload."""
    srv, port, _ = server_no_pdf
    q1: queue.Queue = queue.Queue()
    q2: queue.Queue = queue.Queue()
    with srv._clients_lock:
        srv._clients.append(q1)
        srv._clients.append(q2)
    srv.notify("ok", "broadcast")
    item1 = q1.get(timeout=1)
    item2 = q2.get(timeout=1)
    assert item1["state"] == "ok"
    assert item2["state"] == "ok"
    assert item1["message"] == item2["message"]


def test_disconnected_client_removed_from_registry(server_no_pdf):
    """A client queue that is removed from the registry no longer receives payloads."""
    srv, port, _ = server_no_pdf
    q1: queue.Queue = queue.Queue()
    q2: queue.Queue = queue.Queue()
    with srv._clients_lock:
        srv._clients.append(q1)
        srv._clients.append(q2)

    # Simulate disconnection: remove q1 from the registry
    with srv._clients_lock:
        srv._clients.remove(q1)

    srv.notify("ok", "after disconnect")

    # q2 should receive the message
    item2 = q2.get(timeout=1)
    assert item2["state"] == "ok"

    # q1 should NOT receive anything
    with pytest.raises(queue.Empty):
        q1.get(timeout=0.1)

    # Registry should only contain q2
    with srv._clients_lock:
        assert q1 not in srv._clients
        assert q2 in srv._clients
