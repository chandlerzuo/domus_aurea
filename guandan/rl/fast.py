"""Batched self-play actors on the Rust core.

`play_batch` plays many deals side by side. Each round, every deal that needs a real
decision is encoded in Rust and the networks are evaluated once per group (one forward pass
for all learner seats, one per snapshot, one for DMC), instead of one small call per move.
Returns the same arrays as the one-deal-at-a-time `ppo.play_task`, plus per-opponent scores.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import torch

from ..agents import HeuristicAgent
from ..combos import move_from_tuple
from ..game import Match, team
from .policy import padded_log_probs

try:
    import guandan_core as core
except ImportError:  # extension not built
    core = None

AVAILABLE = core is not None


def fast_observation(rs, seat: int) -> dict:
    """The observation dict the Python agents expect, built from an RsDeal (no history)."""
    table = rs.table
    return {
        "seat": seat, "level": rs.level, "hand": rs.hands[seat], "leading": rs.leading,
        "table": None if table is None else move_from_tuple(table), "table_seat": rs.table_seat,
        "counts": rs.counts, "finished": rs.finished, "history": [], "played": rs.played,
        "team_levels": rs.team_levels, "level_team": rs.level_team,
        "legal": [move_from_tuple(m) for m in rs.legal()] if seat == rs.to_act and not rs.done else [],
    }


def rs_from_deal(d) -> "core.RsDeal":
    return core.RsDeal(d.hands, d.level, d.to_act, tuple(d.team_levels), d.level_team)


def sample_rows(logits: torch.Tensor, n: np.ndarray, rng: np.random.Generator, greedy: bool = False):
    """Per-decision move choice from flat logits. Returns (choice (B,), logp (B,), probs (B, W))."""
    B, M = len(n), logits.shape[0]
    nt = torch.from_numpy(n.astype(np.int64))
    seg = torch.repeat_interleave(torch.arange(B), nt)
    pos = torch.arange(M) - torch.repeat_interleave(torch.cumsum(nt, 0) - nt, nt)
    logp_all = padded_log_probs(logits, seg, pos, B, int(n.max()))
    probs = logp_all.exp().double().numpy()
    probs /= probs.sum(1, keepdims=True)
    if greedy:
        idx = probs.argmax(1)
    else:
        idx = (probs.cumsum(1) < rng.random((B, 1))).sum(1)
    idx = np.minimum(idx, n - 1)
    logp = np.log(probs[np.arange(B), idx] + 1e-12)
    return idx, logp, probs


def policy_logits(actor, S: np.ndarray, A: np.ndarray, n: np.ndarray):
    s, a = torch.from_numpy(S).float(), torch.from_numpy(A).float()
    seg = torch.repeat_interleave(torch.arange(len(n)), torch.from_numpy(n.astype(np.int64)))
    hs = actor.state(s)
    return actor.logits(hs, a, seg), s


def q_logits(net, S: np.ndarray, A: np.ndarray, n: np.ndarray):
    s, a = torch.from_numpy(S).float(), torch.from_numpy(A).float()
    seg = torch.repeat_interleave(torch.arange(len(n)), torch.from_numpy(n.astype(np.int64)))
    return net.head(torch.cat([net.state(s)[seg], net.action(a)], -1)).squeeze(-1)


class _Traj:
    __slots__ = ("S", "O", "A", "chosen", "logp", "value")

    def __init__(self):
        self.S, self.O, self.A, self.chosen, self.logp, self.value = [], [], [], [], [], []


def play_batch(rng: np.random.Generator, n_deals: int, mode: str, learner, opponents, p_tribute: float,
               lam: float, reward_scale: float, width: int = 64, version: int = 1) -> dict:
    """`learner` = (actor, critic); `opponents` = callable(rng) -> ("self"|"heuristic"|"dmc"|"snapshot", net or None).

    mode "bc": the heuristic plays all four seats and its choices are recorded (imitation data).
    mode "ppo": the learner's sampled moves are recorded, with GAE advantages from the oracle critic.
    """
    from .dmc import random_match

    actor, critic = learner if learner is not None else (None, None)
    out = {k: [] for k in ("S", "O", "A", "n", "chosen", "logp", "adv", "ret")}
    scores_by: dict[str, list] = defaultdict(list)
    tables: list[dict] = []
    started = 0

    def new_table() -> dict:
        m = random_match(rng, p_tribute)
        d = m.new_deal()
        me = int(rng.integers(2))
        kind, net = ("self", None) if mode == "bc" else opponents(rng)
        ctrl, agents = [], [None] * 4
        for s in range(4):
            seed = int(rng.integers(2**31))
            if mode == "bc":
                ctrl.append("bc")
                agents[s] = HeuristicAgent(seed)
            elif kind == "self" or team(s) == me:
                ctrl.append("learn")
            elif kind == "heuristic":
                ctrl.append("heur")
                agents[s] = HeuristicAgent(seed)
            else:
                ctrl.append(kind)  # "dmc" or "snapshot": batched network controllers
        for t in m.pending_returns:
            m.give_return(t.receiver, HeuristicAgent(0).choose_return(d.hands[t.receiver], d.level))
        return {"rs": rs_from_deal(d), "ctrl": ctrl, "agents": agents, "me": me, "kind": kind,
                "net": net, "trajs": [_Traj() for _ in range(4)]}

    def finish(t: dict) -> None:
        win, up = t["rs"].result()
        scores_by["bc" if mode == "bc" else t["kind"]].append(up if win == t["me"] else -up)
        for s, tr in enumerate(t["trajs"]):
            if not tr.S:
                continue
            r = (up if win == team(s) else -up) / reward_scale
            if mode == "bc":
                adv, ret = [0.0] * len(tr.S), [r] * len(tr.S)
            else:  # GAE over this player's decisions; reward only at the end (gamma = 1)
                vals = tr.value + [r]
                adv, gae = [0.0] * len(tr.S), 0.0
                for k in reversed(range(len(tr.S))):
                    gae = vals[k + 1] - vals[k] + lam * gae
                    adv[k] = gae
                ret = [x + v for x, v in zip(adv, tr.value)]
            out["S"] += tr.S
            out["O"] += tr.O
            out["A"] += tr.A
            out["n"] += [len(a) for a in tr.A]
            out["chosen"] += tr.chosen
            out["logp"] += tr.logp
            out["adv"] += adv
            out["ret"] += ret

    while tables or started < n_deals:
        while len(tables) < width and started < n_deals:
            tables.append(new_table())
            started += 1
        groups: dict = defaultdict(list)
        for t in tables:
            rs = t["rs"]
            while not rs.done and rs.n_legal() == 1:
                rs.play_index(0)
            if rs.done:
                continue
            seat = rs.to_act
            c = t["ctrl"][seat]
            if c == "heur":
                rs.play_index(t["agents"][seat].act(fast_observation(rs, seat)))
            elif c == "bc":
                i = t["agents"][seat].act(fast_observation(rs, seat))
                tr = t["trajs"][seat]
                tr.S.append(rs.encode_state(seat, version)), tr.A.append(rs.encode_actions(version))
                tr.O.append(rs.encode_oracle(seat)), tr.chosen.append(i), tr.logp.append(0.0), tr.value.append(0.0)
                rs.play_index(i)
            else:
                groups["learn" if c == "learn" else (c, id(t["net"]))].append(t)
        with torch.no_grad():
            for key, ts in groups.items():
                deals = [t["rs"] for t in ts]
                net = actor if key == "learn" else ts[0]["net"]
                S, A, n = core.batch_encode(deals, getattr(net, "version", 1))
                if key == "learn":
                    logits, s_t = policy_logits(actor, S, A, n)
                    idx, logp, _ = sample_rows(logits, n, rng)
                    O = core.batch_oracle(deals)
                    v = critic(s_t, torch.from_numpy(O).float()).numpy()
                    off = np.concatenate([[0], np.cumsum(n)[:-1]])
                    for k, t in enumerate(ts):
                        seat = t["rs"].to_act
                        tr = t["trajs"][seat]
                        tr.S.append(S[k]), tr.O.append(O[k]), tr.A.append(A[off[k]:off[k] + n[k]])
                        tr.chosen.append(int(idx[k])), tr.logp.append(float(logp[k])), tr.value.append(float(v[k]))
                elif key[0] == "dmc":
                    idx, _, _ = sample_rows(q_logits(ts[0]["net"], S, A, n), n, rng, greedy=True)
                else:  # snapshot policy, sampled
                    logits, _ = policy_logits(ts[0]["net"], S, A, n)
                    idx, _, _ = sample_rows(logits, n, rng)
                core.batch_play(deals, [int(i) for i in idx])
        still = []
        for t in tables:
            if t["rs"].done:
                finish(t)
            else:
                still.append(t)
        tables = still

    res = {"S": np.stack(out["S"]), "O": np.stack(out["O"]), "A": np.concatenate(out["A"]),
           "n": np.asarray(out["n"], np.int32), "chosen": np.asarray(out["chosen"], np.int64),
           "logp": np.asarray(out["logp"], np.float32), "adv": np.asarray(out["adv"], np.float32),
           "ret": np.asarray(out["ret"], np.float32)}
    res.update(deals=n_deals, scores_by=dict(scores_by))
    return res
