"""Web app: shared tables where people play Guandan with and against each other and AI players.

The first person to sit at an open table hosts it: they fill empty seats with
AI or wait for others to sit, then start the match. There are no accounts. Access control is the network: the server binds to
loopback by default, and otherwise only to a private address (a Tailscale or
WireGuard interface). Public and wildcard binds are refused. Reach it over an
SSH tunnel (ssh -L 8770:127.0.0.1:8770 host) or the private network; see
docs/DEPLOY.md. Requests whose Host header is not an expected address are
rejected (DNS-rebinding protection), and actions require the seat token issued
when the seat was claimed.

  python -m guandan.server [--host 127.0.0.1] [--port 8770] [--db data/games.db]
"""
from __future__ import annotations

import argparse
import ipaddress
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ..review import lead_flags
from .store import Store
from .tables import Lobby, agent_kinds
from .zh import error_zh

STATIC = Path(__file__).parent / "static"
TAILSCALE = ipaddress.ip_network("100.64.0.0/10")
TABLES = 10  # see docs/DEPLOY.md: capacity estimate


def check_bind(host: str) -> None:
    """Allow loopback and private-network addresses only (never 0.0.0.0, :: or a public IP)."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        raise SystemExit(f"--host must be an IP address, got {host!r}") from None
    if ip.is_unspecified or not (ip.is_loopback or ip.is_private or ip in TAILSCALE):
        raise SystemExit(f"refusing to bind {host}: this server has no login, so it must only listen on "
                         "loopback or a private (Tailscale/WireGuard) address. See docs/DEPLOY.md.")


class Handler(BaseHTTPRequestHandler):
    lobby: Lobby
    allowed_hosts: set[str]

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                                    "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj).encode())

    def _route(self, method: str) -> None:
        if (self.headers.get("Host") or "") not in self.allowed_hosts:
            return self._json(403, {"error": error_zh("bad host")})
        url = urlsplit(self.path)
        parts = url.path.strip("/").split("/")
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        body: dict = {}
        try:
            if method == "POST":
                if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
                    return self._json(415, {"error": error_zh("JSON required")})
                length = int(self.headers.get("Content-Length") or 0)
                if length > 64 * 1024:
                    return self._json(413, {"error": error_zh("request too large")})
                body = json.loads(self.rfile.read(length) or b"{}")
            return self._dispatch(method, parts, query, body)
        except PermissionError as e:
            self._json(409, {"error": error_zh(str(e))})
        except KeyError as e:
            self._json(404, {"error": error_zh(str(e).strip("'\""))})
        except (ValueError, TypeError) as e:
            self._json(400, {"error": error_zh(str(e))})

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def _dispatch(self, method: str, parts: list[str], query: dict, body: dict) -> None:
        lobby = self.lobby
        if method == "GET" and parts in ([""], ["index.html"]):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if parts == ["api", "lobby"] and method == "GET":
            return self._json(200, {"tables": [t.summary() for t in lobby.tables], "agents": agent_kinds(),
                                    "recent": lobby.store.deals(limit=20)})
        if parts == ["api", "deals"] and method == "GET":
            return self._json(200, lobby.store.deals(match_id=query.get("match"), limit=100))
        if len(parts) >= 3 and parts[:2] == ["api", "deal"]:
            deal_id = int(parts[2])
            if len(parts) == 3 and method == "GET":
                record = lobby.store.deal(deal_id)
                if record is None:
                    raise KeyError("no such deal")
                return self._json(200, {"id": deal_id, **record, "leads": lead_flags(record)})
            if parts[3:] == ["review"]:
                seat = int(query.get("seat", body.get("seat", 0)))
                if method == "POST":
                    return self._json(200, lobby.request_review(deal_id, seat))
                return self._json(200, lobby.review_status(deal_id, seat))
        if len(parts) == 4 and parts[:2] == ["api", "table"]:
            table = lobby.table(int(parts[2]))
            token = self.headers.get("X-Seat-Token")
            cmd = parts[3]
            if cmd == "state" and method == "GET":
                seat = int(query.get("seat", 0))
                if not 0 <= seat < 4:
                    raise ValueError("seat must be 0-3")
                return self._json(200, table.view(token, seat))  # a seated player always sees their own seat
            if method != "POST":
                raise KeyError("not found")
            if cmd == "sit":
                token = table.sit(int(body.get("seat", -1)), body.get("name"), body.get("suggestions", False))
                return self._json(200, {"token": token, **table.view(token, 0)})
            with table.lock:
                me = table.seat_of(token)
                if me is None:
                    raise PermissionError("you are not seated at this table")
                g = table.game
                if cmd == "leave":
                    table.leave(me)
                elif cmd == "seat":
                    table.set_seat(me, int(body["seat"]), body.get("kind", "empty"))
                elif cmd == "start":
                    table.start(me)
                elif g is None:
                    raise ValueError("the match has not started")
                elif cmd == "play":
                    g.play(me, body.get("cards", []))
                elif cmd == "return":
                    g.give_return(me, body["card"])
                elif cmd == "next":
                    g.next_deal()
                else:
                    raise KeyError("unknown command")
                return self._json(200, table.view(None if cmd == "leave" else token, me))
        raise KeyError("not found")


class Server(ThreadingHTTPServer):
    request_queue_size = 256  # the default of 5 drops connections when many clients poll at once
    daemon_threads = True


def make_server(host: str, port: int, db: str | Path, tables: int = TABLES, ai_delay: float = 0.9,
                extra_hosts: tuple[str, ...] = ()) -> ThreadingHTTPServer:
    check_bind(host)
    lobby = Lobby(Store(db), tables, ai_delay=ai_delay)
    handler = type("BoundHandler", (Handler,), {"lobby": lobby, "allowed_hosts": set()})
    srv = Server((host, port), handler)
    port = srv.server_address[1]  # resolved when port=0
    names = [host] + (["localhost"] if ipaddress.ip_address(host).is_loopback else []) + list(extra_hosts)
    handler.allowed_hosts = {f"{n}:{port}" for n in names}
    srv.lobby = lobby
    return srv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="loopback (default) or a private Tailscale/WireGuard IP")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--db", default="data/games.db")
    ap.add_argument("--tables", type=int, default=TABLES)
    ap.add_argument("--ai-delay", type=float, default=0.9, help="seconds between computer moves")
    ap.add_argument("--allow-host", action="append", default=[],
                    help="extra Host name clients use, e.g. a Tailscale MagicDNS name")
    a = ap.parse_args()
    srv = make_server(a.host, a.port, a.db, a.tables, a.ai_delay, tuple(a.allow_host))
    print(f"guandan on http://{a.host}:{srv.server_address[1]}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.lobby.stop()


if __name__ == "__main__":
    main()
