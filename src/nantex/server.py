import html
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>nantex preview</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { display: flex; flex-direction: column; height: 100vh; font-family: sans-serif; }
  #status {
    padding: 6px 12px; font-size: 13px; background: #1e1e1e; color: #ccc;
    border-bottom: 1px solid #333; min-height: 30px; display: flex; align-items: center;
  }
  #status.ok  { color: #4ec94e; }
  #status.err { color: #f87171; }
  #placeholder {
    flex: 1; display: flex; align-items: center; justify-content: center;
    color: #888; font-size: 16px; background: #fafafa;
  }
  #pdf-frame { flex: 1; border: none; display: none; }
</style>
</head>
<body>
<div id="status">Waiting for first compile…</div>
<div id="placeholder">Waiting for first compile…</div>
<iframe id="pdf-frame" src=""></iframe>
<script>
const status = document.getElementById('status');
const placeholder = document.getElementById('placeholder');
const frame = document.getElementById('pdf-frame');

function applyState(data) {
  const state = JSON.parse(data);
  if (state.state === 'ok') {
    frame.src = '/output.pdf?t=' + Date.now();
    frame.style.display = 'block';
    placeholder.style.display = 'none';
    status.className = 'ok';
    status.textContent = state.message || 'Compiled';
  } else if (state.state === 'error') {
    status.className = 'err';
    const msg = document.createElement('span');
    msg.textContent = state.message || 'Compile error';
    status.replaceChildren(msg);
  }
}

const es = new EventSource('/events');
es.onmessage = function(e) { applyState(e.data); };
es.onerror   = function()  {
  status.className = '';
  status.textContent = 'Disconnected — reconnecting…';
};

fetch('/status').then(r => r.text()).then(t => { if (t) applyState(t); });
</script>
</body>
</html>
"""


class PreviewServer:
    def __init__(self, pdf_path: str, port: int):
        self._pdf_path = Path(pdf_path)
        self._port = port
        self._clients: list[queue.Queue] = []
        self._clients_lock = threading.Lock()
        self._last_state: dict = {}
        self._ready = threading.Event()
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> None:
        server = self  # reference for handler closure

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # suppress default request logging

            def do_GET(self):
                if self.path == "/":
                    self._send_html()
                elif self.path.startswith("/output.pdf"):
                    self._send_pdf()
                elif self.path == "/events":
                    self._send_sse()
                elif self.path == "/status":
                    self._send_status()
                else:
                    self.send_response(404)
                    self.end_headers()

            def _send_html(self):
                data = _HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_pdf(self):
                if not server._pdf_path.exists():
                    self.send_response(404)
                    self.end_headers()
                    return
                data = server._pdf_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _send_sse(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                per_client_queue: queue.Queue = queue.Queue()
                with server._clients_lock:
                    server._clients.append(per_client_queue)

                # Emit current state immediately so reconnecting browsers catch up
                if server._last_state:
                    self._sse_write(json.dumps(server._last_state))

                while True:
                    try:
                        item = per_client_queue.get(timeout=30)
                        self._sse_write(json.dumps(item))
                    except queue.Empty:
                        try:
                            self.wfile.write(b": keep-alive\n\n")
                            self.wfile.flush()
                        except Exception:
                            with server._clients_lock:
                                try:
                                    server._clients.remove(per_client_queue)
                                except ValueError:
                                    pass
                            break
                    except BrokenPipeError:
                        with server._clients_lock:
                            try:
                                server._clients.remove(per_client_queue)
                            except ValueError:
                                pass
                        break
                    except Exception:
                        with server._clients_lock:
                            try:
                                server._clients.remove(per_client_queue)
                            except ValueError:
                                pass
                        break

            def _send_status(self):
                data = json.dumps(server._last_state).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _sse_write(self, payload: str):
                try:
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()
                except Exception:
                    pass

        class _ReuseAddrServer(ThreadingHTTPServer):
            allow_reuse_address = True

            def handle_error(self, request, client_address):
                # Suppress noisy browser disconnect errors — harmless in practice
                import sys
                exc = sys.exc_info()[1]
                if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
                    return
                super().handle_error(request, client_address)

        def _run():
            httpd = _ReuseAddrServer(("127.0.0.1", self._port), Handler)
            self._server = httpd
            self._ready.set()
            httpd.serve_forever()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self._ready.wait()

    def notify(self, state: str, message: str = "") -> None:
        # HTML-escape message to prevent XSS if ever rendered as HTML
        safe_message = html.escape(message)
        payload = {"state": state, "message": safe_message}
        self._last_state = payload
        with self._clients_lock:
            for client_queue in list(self._clients):
                client_queue.put(payload)
