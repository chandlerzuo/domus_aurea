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

from ..agents import HeuristicAgent, make_style
from ..cards import ACE
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
    __slots__ = ("S", "O", "A", "chosen", "logp", "value", "sets", "race")

    def __init__(self):
        self.S, self.O, self.A, self.chosen, self.logp, self.value = [], [], [], [], [], []
        self.sets, self.race = [], []      # fewest sets in the player's own hand / in each other hand, at each decision


def play_batch(rng: np.random.Generator, n_deals: int, mode: str, learner, opponents, p_tribute: float,
               lam: float, reward_scale: float, width: int = 64, version: int = 1, match_bonus: float = 0.0,
               p_endgame: float = 0.0, p_runout: float = 0.0, shape_first: float = 0.0,
               shape_bomb: float = 0.0, shape_sets: float = 0.0, shape_left: float = 0.0, want_race: bool = False) -> dict:
    """`learner` = (actor, critic); `opponents` = callable(rng) -> ("self"|"heuristic"|"dmc"|"snapshot", net or None).

    mode "bc": the heuristic plays all four seats and its choices are recorded (imitation data).
    mode "ppo": the learner's sampled moves are recorded, with GAE advantages from the oracle critic.
    `match_bonus` > 0 adds that many levels to the reward (and subtracts it for the other side) when the deal
    ends the match, i.e. the team playing its own level at A wins by 2 or more levels.
    `p_endgame` is the share of deals that start late: the heuristic plays the deal forward until a random
    12-40 cards are left in total, and the learner trains only on the rest. Late positions are rare in ordinary
    self-play, so this gives the endgame many more examples.
    `p_runout` is the share of deals that start from a constructed "saved runout" position (see rl/scenarios.py): an
    opponent holds only a bomb / full house / high single and is on lead, and the learner plays the other team.
    `shape_first` / `shape_bomb` add levels of reward to the *player* who goes out first / for each bomb a player
    plays: they make agents with different temperaments (selfish racer, bomb hoarder, bomb spender).
    `shape_sets` pays that many levels each time a move of the player's own shortens the hand's fewest-sets plan (and charges it
    for lengthening it); it is potential-based (the potential is zero when the deal ends), so it leaves the best play unchanged and
    only makes the learning signal denser. `shape_left` charges that many levels per set the player is still holding when the deal
    ends, which does change the objective: it says that being stuck with sets matters beyond the levels. `want_race` records, at
    every decision, the other players' fewest-sets counts (targets for the model's race head).
    """
    from .dmc import random_match

    actor, critic = learner if learner is not None else (None, None)
    out = {k: [] for k in ("S", "O", "A", "n", "chosen", "logp", "adv", "ret", "L", "R")}
    track = bool(shape_sets or shape_left or want_race)
    scores_by: dict[str, list] = defaultdict(list)
    tables: list[dict] = []
    started = 0

    def new_table() -> dict:
        while True:
            t = _new_table()
            if t is not None:
                return t

    def _runout_table():
        from .scenarios import runout_position
        d, h, scripted = runout_position(rng)
        ctrl, agents = [], [None] * 4
        for s in range(4):
            if team(s) == team(h):
                ctrl.append("heur")
                agents[s] = scripted[s]
            else:
                ctrl.append("learn")
        return {"rs": rs_from_deal(d), "ctrl": ctrl, "agents": agents, "me": 1 - team(h), "kind": "runout",
                "match_team": None, "net": None, "label": 12, "trajs": [_Traj() for _ in range(4)]}

    def _new_table():
        if mode == "ppo" and rng.random() < p_runout:
            return _runout_table()
        m = random_match(rng, p_tribute)
        d = m.new_deal()
        me = int(rng.integers(2))
        got = ("self", None) if mode == "bc" else opponents(rng)
        kind, net = got[0], got[1]
        label = got[2] if len(got) > 2 else {"self": 0, "heuristic": 1, "dmc": 2}.get(kind, 0)
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
            elif kind.startswith("style:"):    # a scripted opponent with a personality (agents.STYLES)
                ctrl.append("heur")
                agents[s] = make_style(kind[6:], seed)
            else:
                ctrl.append(kind)  # "dmc" or "snapshot": batched network controllers
        for t in m.pending_returns:
            m.give_return(t.receiver, HeuristicAgent(0).choose_return(d.hands[t.receiver], d.level))
        rs = rs_from_deal(d)
        if mode != "bc" and rng.random() < p_endgame:
            left, fw = int(rng.integers(12, 41)), HeuristicAgent(int(rng.integers(2**31)))
            while not rs.done and sum(rs.counts) > left:
                if rs.n_legal() == 1:
                    rs.play_index(0)
                else:
                    rs.play_index(fw.act(fast_observation(rs, rs.to_act)))
            if rs.done:
                return None
        ends = m.level_team is not None and m.team_levels[m.level_team] == ACE   # a win by this team with up >= 2 ends the match
        return {"rs": rs, "ctrl": ctrl, "agents": agents, "me": me, "kind": kind,
                "match_team": m.level_team if ends else None,
                "net": net, "label": label, "trajs": [_Traj() for _ in range(4)]}

    def finish(t: dict) -> None:
        win, up = t["rs"].result()
        scores_by["bc" if mode == "bc" else t["kind"]].append(up if win == t["me"] else -up)
        worth = up + (match_bonus if (t["match_team"] == win and up >= 2) else 0.0)
        for s, tr in enumerate(t["trajs"]):
            if not tr.S:
                continue
            r = (worth if win == team(s) else -worth)
            if shape_first or shape_bomb:
                r += shape_first * (t["rs"].finished[0] == s) + shape_bomb * sum(1 for hs, hm in t["rs"].history if hs == s and hm[0] >= 8)
            r /= reward_scale
            if mode == "bc":
                adv, ret = [0.0] * len(tr.S), [r] * len(tr.S)
            else:  # GAE over this player's decisions; the deal's result arrives at the last one (gamma = 1)
                K = len(tr.S)
                rew = [0.0] * K
                if shape_sets or shape_left:
                    h_end = t["rs"].min_sets(s)
                    for k in range(K - 1):
                        rew[k] = shape_sets * (tr.sets[k] - tr.sets[k + 1]) / reward_scale
                    rew[K - 1] = (shape_sets * tr.sets[K - 1] - shape_left * h_end) / reward_scale
                rew[K - 1] += r
                vals = tr.value + [0.0]
                adv, gae = [0.0] * K, 0.0
                for k in reversed(range(K)):
                    gae = rew[k] + vals[k + 1] - vals[k] + lam * gae
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
            out["L"] += [t["label"]] * len(tr.S)
            if want_race:
                out["R"] += tr.race

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
                        if track:
                            rs_ = t["rs"]
                            tr.sets.append(rs_.min_sets(seat))
                            if want_race:
                                tr.race.append([rs_.min_sets((seat + o) % 4) / 10.0 for o in (1, 2, 3)])
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
           "ret": np.asarray(out["ret"], np.float32), "L": np.asarray(out["L"], np.int64)}
    if want_race:
        res["R"] = np.asarray(out["R"], np.float32)
    res.update(deals=n_deals, scores_by=dict(scores_by))
    return res
