"""Web app: log in and play Guandan with a computer partner against two computer opponents.

Loopback-only by design. To play from another machine, forward the port over
SSH (ssh -L 8770:127.0.0.1:8770 host) rather than widening the bind. Requests
whose Host header is not this loopback address are rejected (DNS-rebinding
protection), and state-changing requests must be JSON, which together with the
SameSite=Strict session cookie blocks cross-site form posts.

  python -m guandan.server [--port 8770] [--db data/users.db]
"""
from __future__ import annotations

import argparse
import json
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from ..agents import AGENTS as BASE_AGENTS, Agent, HeuristicAgent
from ..cards import RANKS, card_str, is_wild
from ..game import Match, combo_label, partner, return_options, team
from .auth import SESSION_TTL, Sessions, Users

HOST = "127.0.0.1"
STATIC = Path(__file__).parent / "static"
HUMAN = 0
MODEL = Path(__file__).resolve().parents[2] / "runs" / "dmc" / "model.pt"
_DMC_NET = None


def make_agent(kind: str, seed: int | None) -> Agent:
    global _DMC_NET
    if kind == "dmc":
        from ..rl.dmc import DMCAgent, load_net
        if _DMC_NET is None:
            _DMC_NET = load_net(MODEL)
        return DMCAgent(_DMC_NET, seed=seed)
    if kind not in BASE_AGENTS:
        raise ValueError(f"unknown agent {kind!r}")
    return BASE_AGENTS[kind](seed=seed)


def agent_kinds() -> list[str]:
    return sorted(BASE_AGENTS) + (["dmc"] if MODEL.exists() else [])


def card_json(c: int, level: int) -> dict:
    return {"id": c, "label": card_str(c), "wild": is_wild(c, level)}


class Game:
    """One user's match. The human always sits at seat 0; seat 2 is their partner."""

    def __init__(self, user: str, partner_kind: str, opponent_kind: str, seed: int | None = None):
        self.user = user
        self.kinds = [None, opponent_kind, partner_kind, opponent_kind]
        self.agents = [None] + [make_agent(k, None if seed is None else seed + s)
                                for s, k in enumerate(self.kinds[1:], 1)]
        self.hint_agent = HeuristicAgent(seed)
        self.match = Match(seed=seed)
        self.trick: dict[int, dict] = {}
        self.lock = threading.Lock()
        self.recorded = False
        self._start_deal()

    def _start_deal(self) -> None:
        m = self.match
        d = m.new_deal()
        for t in m.pending_returns:
            if t.receiver != HUMAN:
                m.give_return(t.receiver, self.agents[t.receiver].choose_return(d.hands[t.receiver], d.level))
        self.trick = {}
        self.recorded = False

    @property
    def deal(self):
        return self.match.deal

    def phase(self) -> str:
        if self.match.pending_returns:
            return "return"
        if self.deal.done:
            return "match_over" if self.match.over else "deal_over"
        return "your_turn" if self.deal.to_act == HUMAN else "ai_turn"

    def _apply(self, move) -> None:
        d = self.deal
        seat = d.to_act
        if d.leading:
            self.trick = {}
        d.play(move)
        self.trick[seat] = {"kind": "pass" if move.is_pass else str(move.combo),
                            "cards": [card_str(c) for c in move.cards]}
        self.match.log.append(f"{self.name(seat)}: {combo_label(move)}")
        if d.done:
            self.match.finish_deal()

    def step(self) -> None:
        """One computer action (no-op when waiting for the human)."""
        if self.phase() != "ai_turn":
            return
        d = self.deal
        obs = d.observation(d.to_act)
        agent = self.agents[d.to_act]
        self._apply(obs["legal"][agent.act(obs)])

    def play(self, cards: list[int]) -> None:
        if self.phase() != "your_turn":
            raise ValueError("not your turn")
        self._apply(self.deal.move_from_cards([int(c) for c in cards]))

    def give_return(self, card: int) -> None:
        if self.phase() != "return":
            raise ValueError("no return owed")
        self.match.give_return(HUMAN, int(card))

    def next_deal(self) -> None:
        if self.phase() != "deal_over":
            raise ValueError("deal still in progress")
        self._start_deal()

    def hint(self) -> list[int]:
        if self.phase() == "return":
            return [self.hint_agent.choose_return(self.deal.hands[HUMAN], self.deal.level)]
        if self.phase() != "your_turn":
            return []
        obs = self.deal.observation(HUMAN)
        return list(obs["legal"][self.hint_agent.act(obs)].cards)

    def name(self, seat: int) -> str:
        return "You" if seat == HUMAN else ("Partner" if seat == partner(HUMAN) else f"Opponent {seat}")

    def record_result(self, users: Users) -> None:
        """Count a finished deal (and match) once in the user's stats."""
        if self.recorded or not self.deal.done:
            return
        self.recorded = True
        won = self.deal.result()[0] == team(HUMAN)
        users.record(self.user, "deals_won" if won else "deals_lost")
        if self.match.over:
            users.record(self.user, "matches_won" if self.match.winner == team(HUMAN) else "matches_lost")

    def view(self) -> dict:
        m, d = self.match, self.deal
        phase = self.phase()
        seats = []
        for s in range(4):
            seats.append({
                "seat": s, "name": self.name(s), "kind": self.kinds[s] or "human", "cards_left": len(d.hands[s]),
                "to_act": s == d.to_act, "place": d.finished.index(s) + 1 if s in d.finished else None,
                "last": self.trick.get(s),
            })
        out = {
            "phase": phase, "level": RANKS[d.level], "team_levels": [RANKS[x] for x in m.team_levels],
            "level_team": m.level_team, "deal_no": m.deals_played + (0 if d.done else 1),
            "hand": [card_json(c, d.level) for c in d.hands[HUMAN]], "seats": seats,
            "table": combo_label(d.table) if d.table else None, "table_seat": d.table_seat,
            "leading": d.leading, "log": m.log[-60:],
            "tributes": [{"payer": t.payer, "receiver": t.receiver, "card": card_str(t.card),
                          "returned": card_str(t.returned) if t.returned is not None else None}
                         for t in m.tributes],
            "resisted": m.resisted,
        }
        if phase == "return":
            out["return_options"] = return_options(d.hands[HUMAN])
        if d.done:
            win, up = d.result()
            out["result"] = {"order": [self.name(s) for s in d.finished], "you_won": win == team(HUMAN), "up": up}
        if m.over:
            out["match_winner"] = "You" if m.winner == team(HUMAN) else "Opponents"
        # Opponents' and partner's cards stay hidden until the deal is over.
        if d.done:
            out["revealed"] = {s: [card_str(c) for c in d.hands[s]] for s in range(4) if d.hands[s]}
        return out


class App:
    def __init__(self, db: str | Path):
        self.users = Users(db)
        self.sessions = Sessions()
        self.games: dict[str, Game] = {}
        self.allowed_hosts: set[str] = set()


class Handler(BaseHTTPRequestHandler):
    app: App

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send(self, code: int, body: bytes, ctype_: str = "application/json", headers: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype_)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                                    "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj, headers: dict | None = None) -> None:
        self._send(code, json.dumps(obj).encode(), headers=headers)

    def _token(self) -> str | None:
        c = SimpleCookie(self.headers.get("Cookie") or "")
        return c["session"].value if "session" in c else None

    def _host_ok(self) -> bool:
        return (self.headers.get("Host") or "") in self.app.allowed_hosts

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "bad host"})
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        user = self.app.sessions.get(self._token())
        if path == "/api/me":
            if user is None:
                return self._json(401, {"error": "not logged in"})
            return self._json(200, {"user": user, "stats": self.app.users.stats(user), "agents": agent_kinds(),
                                    "has_game": user in self.app.games})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "bad host"})
        if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
            return self._json(415, {"error": "JSON required"})
        app = self.app
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 64 * 1024:
                return self._json(413, {"error": "request too large"})
            body = json.loads(self.rfile.read(length) or b"{}")
            path = urlsplit(self.path).path
            if path == "/api/register":
                app.users.register(body.get("username", ""), body.get("password", ""))
                return self._login(body)
            if path == "/api/login":
                return self._login(body)
            user = app.sessions.get(self._token())
            if user is None:
                return self._json(401, {"error": "not logged in"})
            if path == "/api/logout":
                app.sessions.delete(self._token())
                return self._json(200, {}, {"Set-Cookie": "session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"})
            if path == "/api/new":
                kinds = agent_kinds()
                p, o = body.get("partner", "heuristic"), body.get("opponents", "heuristic")
                if p not in kinds or o not in kinds:
                    raise ValueError("unknown agent")
                app.games[user] = Game(user, p, o)
                with app.games[user].lock:
                    return self._json(200, app.games[user].view())
            g = app.games.get(user)
            if g is None:
                return self._json(404, {"error": "no game; start one"})
            with g.lock:
                if path == "/api/state":
                    pass
                elif path == "/api/step":
                    g.step()
                elif path == "/api/play":
                    g.play(body.get("cards", []))
                elif path == "/api/return":
                    g.give_return(body["card"])
                elif path == "/api/next":
                    g.next_deal()
                elif path == "/api/hint":
                    return self._json(200, {"cards": g.hint()})
                else:
                    return self._json(404, {"error": "not found"})
                g.record_result(app.users)
                return self._json(200, g.view())
        except (KeyError, ValueError, TypeError) as e:
            self._json(400, {"error": str(e)})
        except FileNotFoundError as e:  # "dmc" chosen but no trained model on disk
            self._json(400, {"error": f"missing model file: {e.filename}"})

    def _login(self, body: dict) -> None:
        user = self.app.users.verify(body.get("username", ""), body.get("password", ""))
        if user is None:
            return self._json(401, {"error": "wrong username or password"})
        token = self.app.sessions.create(user)
        cookie = f"session={token}; Path=/; Max-Age={SESSION_TTL}; HttpOnly; SameSite=Strict"
        self._json(200, {"user": user}, {"Set-Cookie": cookie})


def make_server(port: int, db: str | Path) -> ThreadingHTTPServer:
    app = App(db)
    srv = ThreadingHTTPServer((HOST, port), type("BoundHandler", (Handler,), {"app": app}))
    port = srv.server_address[1]  # resolved when port=0
    app.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    return srv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--db", default="data/users.db")
    a = ap.parse_args()
    srv = make_server(a.port, a.db)
    print(f"guandan on http://{HOST}:{a.port}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
