"""Tables, games, and the background driver that plays the computer seats.

Table lifecycle:
  open     nobody seated
  waiting  the first person to sit is the host; others may take empty seats
           (first come, first served); the host may put an AI in any empty seat
           or clear it again, and starts the match once all four seats are filled
  playing  a match is in progress; nobody new can sit down

Each seated human holds a random seat token that their browser tab sends with
every action. A human who leaves, stops polling for IDLE_SECONDS, or sits on
their turn for TURN_SECONDS is replaced by an AI so the others can keep
playing; when the last human goes, the table resets to open. Before the match
starts, a departing host hands the role to the next seated human.

Anyone may watch a table from any seat's point of view and sees only that
seat's cards. Computer moves are made by a single driver thread at a
human-watchable pace, so players and watchers all see the same game.
"""
from __future__ import annotations

import os
import secrets
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..agents import AGENTS as BASE_AGENTS, Agent, HeuristicAgent
from ..cards import RANKS, card_str, is_wild
from ..game import Match, return_options
from ..review import record_move, review_deal
from . import zh
from .store import Store

RUNS = Path(__file__).resolve().parents[2] / "runs"
MODELS = {"dmc": RUNS / "dmc" / "model.pt", "ppo": RUNS / "ppo" / "model.pt"}
SEARCH_WORLDS = int(os.environ.get("GUANDAN_SEARCH_WORLDS", "32"))
SEARCH_TOPK = int(os.environ.get("GUANDAN_SEARCH_TOPK", "4"))
SEARCH_MARGIN = float(os.environ.get("GUANDAN_SEARCH_MARGIN", "0.0"))
SEARCH_BELIEF = float(os.environ.get("GUANDAN_SEARCH_BELIEF", "1.0"))   # 0 = uniform hidden hands, 1 = weighted by the belief head
IDLE_SECONDS = 90
TURN_SECONDS = 5 * 60
NEXT_DEAL_SECONDS = 45   # a finished deal moves on by itself after this long
_NETS: dict = {}
_NETS_LOCK = threading.Lock()


def search_available() -> bool:
    """`ppo+` (the PPO policy with look-ahead search) needs the Rust core; GUANDAN_SEARCH=0 turns it off."""
    from ..rl import fast
    return fast.AVAILABLE and os.environ.get("GUANDAN_SEARCH", "1") != "0"


def default_ai() -> str:
    """The one AI the server offers: ppo+ (search), else the best thing available."""
    kinds = [k for k, p in MODELS.items() if p.exists()]
    if "ppo" in kinds and search_available():
        return "ppo+"
    return next((k for k in ("ppo", "dmc") if k in kinds), "heuristic")


def agent_kinds() -> list[str]:
    return [default_ai()]


def _net(kind: str):
    with _NETS_LOCK:
        if kind not in _NETS:
            if kind == "dmc":
                from ..rl.dmc import load_net
                _NETS[kind] = load_net(MODELS["dmc"])
            else:
                from ..rl.policy import load_policy
                _NETS[kind] = load_policy(MODELS["ppo"])
        return _NETS[kind]


def make_agent(kind: str, seed: int | None = None) -> Agent:
    if kind == "dmc":
        from ..rl.dmc import DMCAgent
        return DMCAgent(_net("dmc"), seed=seed)
    if kind == "ppo":
        from ..rl.policy import PolicyAgent
        return PolicyAgent(_net("ppo"), seed=seed)
    if kind == "ppo+":
        from ..rl.search import SearchAgent
        return SearchAgent(_net("ppo"), seed=seed, worlds=SEARCH_WORLDS, topk=SEARCH_TOPK, margin=SEARCH_MARGIN,
                           belief=SEARCH_BELIEF)
    if kind not in BASE_AGENTS:
        raise ValueError(f"unknown agent {kind!r}")
    return BASE_AGENTS[kind](seed=seed)


def card_json(c: int, level: int) -> dict:
    return {"id": c, "label": card_str(c), "wild": is_wild(c, level)}


def suggest(obs: dict, k: int = 3) -> list[dict]:
    """Top-k moves from the PPO policy (or the heuristic's single choice if no model is trained)."""
    legal = obs["legal"]
    if MODELS["ppo"].exists():
        from ..rl.features import encode_actions, encode_state
        from ..rl.policy import policy_step
        net = _net("ppo")
        _, _, p = policy_step(net, encode_state(obs, net.version), encode_actions(obs, net.version),
                              np.random.default_rng(0), True)
        top = np.argsort(-p)[:k]
        return [{"move": zh.move_zh(legal[i]), "cards": list(legal[i].cards), "p": round(float(p[i]), 2)} for i in top]
    i = HeuristicAgent(0).act(obs)
    return [{"move": zh.move_zh(legal[i]), "cards": list(legal[i].cards), "p": None}]


def clean_name(name: str | None, seat: int) -> str:
    name = "".join(ch for ch in (name or "").strip() if ch.isprintable())[:16]
    return name or f"{zh.SEATS[seat]}家"


@dataclass
class Seat:
    kind: str = "empty"          # "empty", "human", or an AI kind
    name: str = ""
    token: str | None = None
    suggestions: bool = False
    last_seen: float = 0.0

    def public(self) -> dict:
        return {"kind": self.kind, "name": self.name, "suggestions": self.suggestions}


class Game:
    """One match. `humans` maps seat -> whether that player wants AI suggestions."""

    def __init__(self, table_id: int, kinds: list[str], names: list[str], humans: dict[int, bool],
                 store: Store, seed: int | None = None):
        self.table_id = table_id
        self.match_id = uuid.uuid4().hex[:12]
        self.kinds = list(kinds)
        self.names = list(names)
        self.humans = dict(humans)
        self.agents = [None if s in self.humans else make_agent(k, None if seed is None else seed + s)
                       for s, k in enumerate(self.kinds)]
        self.ever_assisted = {s for s, on in humans.items() if on}
        self.store = store
        self.match = Match(seed=seed)
        self.deal_ids: list[int] = []
        self.log: list[str] = []
        self._start_deal()

    @property
    def deal(self):
        return self.match.deal

    def _start_deal(self) -> None:
        m = self.match
        d = m.new_deal()
        lv = m.team_levels
        self.log.append(f"—— 第 {m.deals_played + 1} 局：打 {zh.rank_zh(d.level)}"
                        f"（南北 {zh.rank_zh(lv[0])} / 东西 {zh.rank_zh(lv[1])}）——")
        if m.resisted:
            self.log.append("抗贡：两张大王都在进贡方手里，本局不进贡")
        for t in m.tributes:
            self.log.append(f"{self.names[t.payer]} 进贡 {zh.card_zh(t.card)} 给 {self.names[t.receiver]}")
        for t in m.pending_returns:
            if t.receiver not in self.humans:
                self._return(t.receiver, self.agents[t.receiver].choose_return(d.hands[t.receiver], d.level))
        self.trick: dict[int, dict] = {}
        self.record: dict | None = None
        self.last_action = time.time()

    def _return(self, seat: int, card: int) -> None:
        payer = next(t.payer for t in self.match.pending_returns if t.receiver == seat)
        self.match.give_return(seat, card)
        self.log.append(f"{self.names[seat]} 还贡 {zh.card_zh(card)} 给 {self.names[payer]}")

    def phase(self) -> str:
        if self.match.pending_returns:
            return "return"
        if self.deal.done:
            return "match_over" if self.match.over else "deal_over"
        return "human_turn" if self.deal.to_act in self.humans else "ai_turn"

    def waiting_on(self) -> list[int]:
        """Human seats the game is waiting for."""
        ph = self.phase()
        if ph == "return":
            return [t.receiver for t in self.match.pending_returns]
        return [self.deal.to_act] if ph == "human_turn" else []

    def replace_with_ai(self, seat: int, kind: str) -> None:
        """A human left: an AI takes over the seat (and any return card they owed)."""
        self.humans.pop(seat, None)
        self.kinds[seat] = kind
        self.names[seat] = f"{zh.SEATS[seat]}·AI（代打）"
        self.log.append(f"{zh.SEATS[seat]}家离开，由 AI 代打")
        self.agents[seat] = make_agent(kind)
        m, d = self.match, self.deal
        for t in m.pending_returns:
            if t.receiver == seat:
                self._return(seat, self.agents[seat].choose_return(d.hands[seat], d.level))
        self.last_action = time.time()

    def _apply(self, move) -> None:
        d, m = self.deal, self.match
        seat = d.to_act
        if self.record is None:  # first move: hands are final (tribute and returns done)
            self.record = {
                "table": self.table_id, "match": self.match_id, "deal_no": m.deals_played + 1,
                "level": d.level, "team_levels": list(d.team_levels), "level_team": d.level_team,
                "leader": seat, "hands": [list(h) for h in d.hands], "kinds": list(self.kinds),
                "names": list(self.names), "humans": sorted(self.humans),
                "assisted": sorted(s for s in self.humans if self.humans[s]), "moves": [],
                "tributes": [{"payer": t.payer, "receiver": t.receiver, "card": zh.card_zh(t.card),
                              "returned": zh.card_zh(t.returned) if t.returned is not None else None}
                             for t in m.tributes],
                "resisted": m.resisted,
            }
        if d.leading:
            self.trick = {}
        d.play(move)
        self.record["moves"].append(record_move(seat, move))
        self.trick[seat] = {"kind": zh.kind_zh(move),
                            "cards": [card_str(c) for c in move.cards]}
        self.log.append(f"{self.names[seat]}：{zh.move_zh(move)}")
        self.last_action = time.time()
        if d.done:
            win, up = m.finish_deal()
            self.record.update(finished=list(d.finished), result={"win_team": win, "up": up})
            order = "，".join(f"{zh.PLACES[i]} {self.names[p]}" for i, p in enumerate(d.finished))
            self.log.append(f"本局结束：{order}。{zh.TEAMS[win]}升 {up} 级"
                            + (f"，{zh.TEAMS[win]}赢得整场比赛！" if m.over else ""))
            self.deal_ids.append(self.store.save_deal(self.record))

    def step(self) -> None:
        if self.phase() != "ai_turn":
            return
        d = self.deal
        obs = d.observation(d.to_act)
        self._apply(obs["legal"][self.agents[d.to_act].act(obs)])

    def play(self, seat: int, cards: list[int]) -> None:
        if self.phase() != "human_turn" or self.deal.to_act != seat:
            raise ValueError("not your turn")
        self._apply(self.deal.move_from_cards([int(c) for c in cards]))

    def give_return(self, seat: int, card: int) -> None:
        if seat not in self.waiting_on() or self.phase() != "return":
            raise ValueError("no return owed")
        self._return(seat, int(card))
        self.last_action = time.time()

    def next_deal(self) -> None:
        if self.phase() != "deal_over":
            raise ValueError("deal still in progress")
        self._start_deal()

    def view(self, seat: int, as_player: bool) -> dict:
        """Everything visible from `seat`: its own hand plus public information."""
        m, d = self.match, self.deal
        phase = self.phase()
        seats = [{"seat": s, "name": self.names[s], "kind": self.kinds[s], "human": s in self.humans,
                  "cards_left": len(d.hands[s]), "to_act": s == d.to_act and not d.done,
                  "place": d.finished.index(s) + 1 if s in d.finished else None,
                  "last": self.trick.get(s)} for s in range(4)]
        out = {
            "phase": phase, "view_seat": seat, "as_player": as_player, "match": self.match_id,
            "waiting_on": self.waiting_on(), "level": RANKS[d.level],
            "team_levels": [RANKS[x] for x in m.team_levels], "level_team": m.level_team,
            "deal_no": m.deals_played + (0 if d.done else 1), "hand": [card_json(c, d.level) for c in d.hands[seat]],
            "seats": seats, "table_play": zh.move_zh(d.table) if d.table else None, "table_seat": d.table_seat,
            "leading": d.leading, "log": self.log[-25:], "resisted": m.resisted, "moves_in_deal": len(d.history),
            "suggestions_on": as_player and self.humans.get(seat, False),
            "tributes": [{"payer": t.payer, "receiver": t.receiver, "card": zh.card_zh(t.card),
                          "returned": zh.card_zh(t.returned) if t.returned is not None else None}
                         for t in m.tributes],
            "deal_ids": list(self.deal_ids),
        }
        if as_player and phase == "return" and seat in self.waiting_on():
            out["return_options"] = return_options(d.hands[seat])
        if as_player and self.humans.get(seat) and phase == "human_turn" and d.to_act == seat:
            out["suggestions"] = suggest(d.observation(seat))
        if d.done:
            win, up = d.result()
            out["result"] = {"order": [self.names[s] for s in d.finished], "win_team": win, "up": up}
            out["revealed"] = {s: [card_str(c) for c in d.hands[s]] for s in range(4) if d.hands[s]}
            out["next_in"] = max(0, round(NEXT_DEAL_SECONDS - (time.time() - self.last_action)))
        if m.over:
            out["match_winner"] = m.winner
        return out


class Table:
    def __init__(self, tid: int, store: Store):
        self.id = tid
        self.store = store
        self.lock = threading.RLock()
        self._reset()

    def _reset(self) -> None:
        self.seats = [Seat() for _ in range(4)]
        self.host: int | None = None
        self.game: Game | None = None

    @property
    def status(self) -> str:
        if self.game is not None:
            return "playing"
        return "waiting" if self.host is not None else "open"

    def humans(self) -> list[int]:
        return [s for s, x in enumerate(self.seats) if x.kind == "human"]

    def seat_of(self, token: str | None) -> int | None:
        """The seat holding this token (refreshes its idle timer), or None."""
        if not token:
            return None
        for s, x in enumerate(self.seats):
            if x.token and secrets.compare_digest(token, x.token):
                x.last_seen = time.time()
                return s
        return None

    # -- before the match ---------------------------------------------------

    def sit(self, seat: int, name: str | None, suggestions: bool) -> str:
        with self.lock:
            if self.game is not None:
                raise PermissionError("the match has already started")
            if not 0 <= seat < 4 or self.seats[seat].kind != "empty":
                raise PermissionError("that seat is taken")
            token = secrets.token_urlsafe(24)
            self.seats[seat] = Seat("human", clean_name(name, seat), token, bool(suggestions), time.time())
            if self.host is None:
                self.host = seat
            return token

    def set_seat(self, by: int, seat: int, kind: str) -> None:
        """Host only: put an AI in an empty seat, or clear an AI seat ("empty")."""
        with self.lock:
            if by != self.host or self.game is not None:
                raise PermissionError("only the host can change seats before the start")
            if not 0 <= seat < 4 or self.seats[seat].kind == "human":
                raise PermissionError("that seat has a person in it")
            if kind == "empty":
                self.seats[seat] = Seat()
            else:
                if kind not in agent_kinds():
                    raise ValueError("unknown agent")
                self.seats[seat] = Seat(kind, zh.ai_name(seat, kind))

    def start(self, by: int) -> None:
        with self.lock:
            if by != self.host or self.game is not None:
                raise PermissionError("only the host can start the match")
            if any(x.kind == "empty" for x in self.seats):
                raise ValueError("fill every seat (with people or AI) first")
            humans = {s: x.suggestions for s, x in enumerate(self.seats) if x.kind == "human"}
            self.game = Game(self.id, [x.kind for x in self.seats], [x.name for x in self.seats], humans, self.store)

    def leave(self, seat: int) -> None:
        with self.lock:
            if self.seats[seat].kind != "human":
                return
            if self.game is not None:
                self.game.replace_with_ai(seat, default_ai())
                self.seats[seat] = Seat(self.game.kinds[seat], self.game.names[seat])
            else:
                self.seats[seat] = Seat()
            if not self.humans():
                self._reset()
            elif self.host == seat:
                self.host = self.humans()[0]

    # -- views and driving --------------------------------------------------

    def summary(self) -> dict:
        with self.lock:
            out = {"id": self.id, "status": self.status, "host": self.host,
                   "seats": [x.public() for x in self.seats]}
            if self.game is not None:
                m = self.game.match
                out.update(deal_no=m.deals_played + 1, team_levels=[RANKS[x] for x in m.team_levels])
            return out

    def view(self, token: str | None, watch_seat: int) -> dict:
        with self.lock:
            me = self.seat_of(token)
            base = {"table": self.id, "status": self.status, "host": self.host, "my_seat": me,
                    "seats_info": [x.public() for x in self.seats]}
            if self.game is None:
                return base
            seat = me if me is not None else watch_seat
            return {**base, **self.game.view(seat, me is not None)}

    def tick(self, now: float, ai_delay: float) -> None:
        with self.lock:
            for s in self.humans():
                if now - self.seats[s].last_seen > IDLE_SECONDS:
                    self.leave(s)
            g = self.game
            if g is None:
                return
            ph = g.phase()
            if g.waiting_on() and now - g.last_action > TURN_SECONDS:
                for s in g.waiting_on():
                    self.leave(s)  # an AI finishes the match in their place
            elif ph == "ai_turn" and now - g.last_action >= ai_delay:
                g.step()
                while ai_delay <= 0 and g.phase() == "ai_turn":  # tests / benchmarks: no pacing
                    g.step()
            elif ph == "deal_over" and now - g.last_action > NEXT_DEAL_SECONDS:
                g.next_deal()


class Lobby:
    def __init__(self, store: Store, n_tables: int, ai_delay: float = 0.9):
        self.store = store
        self.tables = [Table(i + 1, store) for i in range(n_tables)]
        self.ai_delay = ai_delay
        self.reviews: dict[tuple[int, int], str] = {}   # (deal, seat) -> "running" / "error: ..."
        # Reviews run rollouts for up to a minute of CPU; a separate process keeps them
        # from competing with live tables for the interpreter lock.
        self.review_pool = ProcessPoolExecutor(1)
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._drive, daemon=True)
        self.thread.start()

    def table(self, tid: int) -> Table:
        if not 1 <= tid <= len(self.tables):
            raise KeyError("no such table")
        return self.tables[tid - 1]

    def _drive(self) -> None:
        while not self._stop.wait(0.1):
            now = time.time()
            for t in self.tables:
                try:
                    t.tick(now, self.ai_delay)
                except Exception as e:  # keep the other tables running
                    print(f"table {t.id}: {e!r}")
                    with t.lock:
                        t._reset()

    def stop(self) -> None:
        self._stop.set()
        self.review_pool.shutdown(wait=False, cancel_futures=True)

    def review_status(self, deal_id: int, seat: int) -> dict:
        done = self.store.review(deal_id, seat)
        if done is not None:
            return {"status": "done", "review": done}
        return {"status": self.reviews.get((deal_id, seat), "none")}

    def request_review(self, deal_id: int, seat: int) -> dict:
        status = self.review_status(deal_id, seat)
        if status["status"] == "done":
            return status
        record = self.store.deal(deal_id)
        if record is None:
            raise KeyError("no such deal")
        if not MODELS["ppo"].exists():
            raise ValueError("reviews need a trained policy (runs/ppo/model.pt)")
        key = (deal_id, seat)
        state = self.reviews.get(key)
        if state is None or state.startswith("error"):
            self.reviews[key] = "running"
            fut = self.review_pool.submit(run_review, record, seat)
            fut.add_done_callback(lambda f, key=key: self._reviewed(key, f))
        return {"status": "running"}

    def _reviewed(self, key: tuple[int, int], fut) -> None:
        try:
            self.store.save_review(key[0], key[1], fut.result())
            self.reviews.pop(key, None)
        except Exception as e:
            self.reviews[key] = f"error: {e}"


def run_review(record: dict, seat: int) -> dict:
    """Review worker (runs in its own process)."""
    import torch
    torch.set_num_threads(1)
    return review_deal(record, _net("ppo"), seat=seat, label_fn=zh.move_zh)
