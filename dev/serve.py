#!/usr/bin/env python3
"""Run everything locally on one address, the way the server does behind nginx.

  .venv/bin/python dev/serve.py            # http://127.0.0.1:8780/

Starts the Guandan server (Python) and the board-game server (Node), and a small
reverse proxy that serves the portal at / and the games under /guandan/ and
/boardgames/. Needs the Guandan Python environment (see README) and Node.js 18+.
Loopback only; there is no login here (nginx provides it in deployment).
"""
import argparse
import atexit
import http.client
import os
import shutil
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "proxy-authorization", "proxy-authenticate"}


def make_handler(routes: dict[str, int], portal: Path):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _static(self):
            path = self.path.split("?", 1)[0]
            if path not in ("/", "/index.html"):
                return self._send(404, b"not found")
            self._send(200, (portal / "index.html").read_bytes(), "text/html; charset=utf-8")

        def _send(self, code, body, ctype="text/plain", extra=()):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in extra:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _proxy(self):
            for prefix, port in routes.items():
                if self.path == prefix:
                    return self._send(301, b"", extra=[("Location", prefix + "/")])
                if self.path.startswith(prefix + "/"):
                    rest = self.path[len(prefix):]
                    break
            else:
                return self._static()
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else None
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP and k.lower() != "host"}
            headers["Host"] = f"127.0.0.1:{port}"
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3600)
            try:
                conn.request(self.command, rest, body=body, headers=headers)
                r = conn.getresponse()
            except OSError:
                return self._send(502, "the game server is not reachable".encode())
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() not in HOP and k.lower() != "content-length":
                    self.send_header(k, v)
            length = r.getheader("Content-Length")
            if length is not None:
                self.send_header("Content-Length", length)
                self.end_headers()
                self.wfile.write(r.read())
            else:   # streaming (server-sent events): pass chunks through as they arrive, then close
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                try:
                    while chunk := r.read1(4096):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except (OSError, ValueError):
                    pass
            conn.close()

        do_GET = do_POST = do_PUT = do_DELETE = _proxy

    return Handler


def wait_port(port: int, name: str, proc: subprocess.Popen):
    import socket
    for _ in range(100):
        if proc.poll() is not None:
            sys.exit(f"{name} exited early (code {proc.returncode})")
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    sys.exit(f"{name} did not start on port {port}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8780)
    ap.add_argument("--guandan-port", type=int, default=8770)
    ap.add_argument("--boardgames-port", type=int, default=8765)
    ap.add_argument("--tables", type=int, default=10, help="Guandan tables")
    ap.add_argument("--db", default=str(ROOT / "data" / "games.db"), help="Guandan replay database")
    a = ap.parse_args()
    node = shutil.which("node")
    if not node:
        sys.exit("Node.js 18+ is needed for the board game (https://nodejs.org)")
    (ROOT / "data").mkdir(exist_ok=True)
    procs = []

    def start(name, cmd, cwd, env=None, port=None):
        p = subprocess.Popen(cmd, cwd=cwd, env={**os.environ, **(env or {})})
        procs.append(p)
        atexit.register(p.terminate)
        wait_port(port, name, p)

    start("guandan", [sys.executable, "-m", "guandan.server", "--port", str(a.guandan_port), "--tables", str(a.tables), "--db", a.db],
          ROOT / "games" / "guandan", port=a.guandan_port)
    start("boardgames", [node, "server/server.js"], ROOT / "games" / "boardgames",
          {"SANGUO_PORT": str(a.boardgames_port)}, port=a.boardgames_port)
    routes = {"/guandan": a.guandan_port, "/boardgames": a.boardgames_port}
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(routes, ROOT / "portal"))
    srv.daemon_threads = True
    print(f"Xanadu: http://127.0.0.1:{a.port}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
