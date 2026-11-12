"""Test-time search on top of a policy network: perfect-information Monte Carlo (PIMC).

At a decision, the searcher sees only what the player sees: their hand, the cards played so
far, how many cards each player holds, the table and the move history. It then
  1. deals the unseen cards to the other three players at random (consistent with those counts),
     many times, giving sampled "worlds";
  2. for the policy's top few candidate moves, plays each one in every world and lets the policy
     play all four seats to the end of the deal (all rollouts advance together, in batches);
  3. picks the candidate with the best average result for the player's team, keeping the policy's
     own choice unless a candidate is clearly better.

Needs the Rust core (`guandan_core`).
"""
from __future__ import annotations

import numpy as np
import torch

from ..agents import Agent
from ..cards import N_CARDS, ctype
from ..combos import Kind
from . import fast
from .features import encode_actions, encode_state
from .policy import policy_step

core = fast.core


def _tuple(move) -> tuple:
    return int(move.combo.kind), move.combo.value, move.combo.size, [int(c) for c in move.cards]


def belief_probs(actor, obs: dict) -> np.ndarray:
    """(3, N_TYPES): the belief head's chance that the next / partner / previous player holds at least one
    copy of each card type."""
    s = torch.from_numpy(encode_state(obs, actor.version)).float()[None]
    with torch.no_grad():
        pr = torch.sigmoid(actor.belief(actor.state(s)))[0].numpy().reshape(3, -1)
    return pr[:, 0::2]


def sample_world(obs: dict, rng: np.random.Generator, version: int, bel: np.ndarray | None = None, power: float = 1.0):
    """One possible state of the whole table consistent with what this player can see.

    Without `bel` the unseen cards are dealt uniformly at random. With `bel` (see `belief_probs`) each card
    goes to a player with probability proportional to belief ** power, times the places that player still has
    free, so the hand sizes always come out right and `power` = 0 is the uniform deal."""
    seat = obs["seat"]
    hands: list = [None] * 4
    hands[seat] = [int(c) for c in obs["hand"]]
    seen = set(obs["hand"]) | {c for p in obs["played"] for c in p}
    unseen = [c for c in range(N_CARDS) if c not in seen]
    rng.shuffle(unseen)
    others = [(seat + 1 + k) % 4 for k in range(3)]
    if bel is None or power <= 0:
        at = 0
        for s in others:
            n = obs["counts"][s]
            hands[s] = [int(c) for c in unseen[at:at + n]]
            at += n
    else:
        w = (np.asarray(bel) + 1e-3) ** power          # (3, N_TYPES)
        cap = [obs["counts"][s] for s in others]
        out: list = [[], [], []]
        u = rng.random(len(unseen))
        for c, r in zip(unseen, u):
            t = ctype(c)
            ws = [w[k, t] * cap[k] for k in range(3)]
            tot = ws[0] + ws[1] + ws[2]
            if tot <= 0:
                break
            r *= tot
            k = 0 if r < ws[0] else 1 if r < ws[0] + ws[1] else 2
            out[k].append(int(c))
            cap[k] -= 1
        for k, s in enumerate(others):
            hands[s] = out[k]
    table, history = obs["table"], obs["history"]
    passes = 0
    if table is not None:
        for _, m in reversed(history):
            if m.combo.kind != Kind.PASS:
                break
            passes += 1
    return core.RsDeal.from_state(
        hands, obs["level"], seat, tuple(obs["team_levels"]), obs["level_team"],
        None if table is None else _tuple(table), obs["table_seat"], passes, list(obs["finished"]),
        [(s, _tuple(m)) for s, m in history], [[int(c) for c in p] for p in obs["played"]], version)


def rollout(sims: list, actor, version: int, rng: np.random.Generator) -> None:
    """Play every deal to the end with the policy (greedy), all together."""
    live = sims
    while True:
        nxt = []
        for s in live:
            while not s.done and s.n_legal() == 1:
                s.play_index(0)
            if not s.done:
                nxt.append(s)
        live = nxt
        if not live:
            return
        S, A, n = core.batch_encode(live, version)
        with torch.no_grad():
            logits, _ = fast.policy_logits(actor, S, A, n)
        idx, _, _ = fast.sample_rows(logits, n, rng, greedy=True)
        core.batch_play(live, [int(i) for i in idx])


def search_values(actor, obs: dict, rng: np.random.Generator, worlds: int = 16, topk: int = 3,
                  min_prob: float = 0.03, belief: float = 0.0):
    """Candidate moves, the policy's probabilities over all legal moves, and each candidate's
    estimated result (levels for the player's team). `None` when there is only one candidate."""
    v = actor.version
    _, _, p = policy_step(actor, encode_state(obs, v), encode_actions(obs, v), rng, greedy=True)
    order = [int(j) for j in np.argsort(-p)]
    cand = [order[0]] + [j for j in order[1:topk] if p[j] >= min_prob]
    if len(cand) < 2:
        return None
    bel = belief_probs(actor, obs) if belief > 0 else None
    ws = [sample_world(obs, rng, v, bel, belief) for _ in range(worlds)]
    sims, owner = [], []
    for w in ws:
        for k, j in enumerate(cand):
            c = w.copy()
            c.play_index(j)
            sims.append(c)
            owner.append(k)
    rollout(sims, actor, v, rng)
    me = obs["seat"] % 2
    tot, cnt = np.zeros(len(cand)), np.zeros(len(cand))
    for c, k in zip(sims, owner):
        win, up = c.result()
        tot[k] += up if win == me else -up
        cnt[k] += 1
    return cand, p, tot / cnt


def solve_choice(actor, obs: dict, rng: np.random.Generator, worlds: int = 16, budget: int = 100_000,
                 belief: float = 0.0):
    """Endgame by exact solving: sample hidden hands, solve each sampled world exactly (every player choosing the
    best move for their team), and pick the move with the best average value. The policy's probability breaks
    ties. Returns the chosen index into obs["legal"] and the per-move mean values, or None when too few of the
    sampled worlds could be solved within `budget` positions each."""
    v = actor.version
    bel = belief_probs(actor, obs) if belief > 0 else None
    tot, done = None, 0
    for _ in range(worlds):
        vals = sample_world(obs, rng, v, bel, belief).solve(budget)
        if vals is None:
            continue
        vals = np.asarray(vals, dtype=float)
        tot = vals if tot is None else tot + vals
        done += 1
    if done * 2 < worlds:
        return None
    mean = tot / done
    _, _, p = policy_step(actor, encode_state(obs, v), encode_actions(obs, v), rng, greedy=True)
    return int(np.argmax(mean + 1e-3 * p)), mean


def improved_policy(p: np.ndarray, cand: list[int], val: np.ndarray, tau: float) -> np.ndarray:
    """The policy shifted toward better-looking candidates: they share their original total
    probability in proportion to p * exp(value / tau); every other move keeps its probability."""
    w = np.log(p[cand] + 1e-12) + np.asarray(val) / tau
    w = np.exp(w - w.max())
    t = p.copy()
    t[cand] = p[cand].sum() * w / w.sum()
    return t


def search_choice(actor, obs: dict, rng: np.random.Generator, worlds: int = 16, topk: int = 3,
                  min_prob: float = 0.03, margin: float = 0.0, belief: float = 0.0) -> tuple[int, dict]:
    """Index into obs["legal"] and a report: candidates with their policy probability and
    estimated result (levels for the player's team)."""
    res = search_values(actor, obs, rng, worlds, topk, min_prob, belief)
    if res is None:
        _, _, p = policy_step(actor, encode_state(obs, actor.version), encode_actions(obs, actor.version),
                              rng, greedy=True)
        return int(p.argmax()), {"searched": False}
    cand, p, val = res
    best = int(np.argmax(val))
    pick = best if val[best] - val[0] > margin else 0
    return cand[pick], {"searched": True, "cands": [(int(j), round(float(p[j]), 3), round(float(x), 2))
                                                    for j, x in zip(cand, val)], "changed": pick != 0}


class SearchAgent(Agent):
    """The policy plus search; plays like `PolicyAgent` when the search finds nothing better."""

    name = "ppo+"

    def __init__(self, actor, seed: int | None = None, worlds: int = 16, topk: int = 3, margin: float = 0.0,
                 belief: float = 0.0, endgame_cards: int = 0, endgame_worlds: int = 128, endgame_topk: int = 99,
                 solve_cards: int = 0, solve_worlds: int = 16, solve_budget: int = 100_000):
        super().__init__(seed)
        self.actor, self.worlds, self.topk, self.margin, self.belief = actor, worlds, topk, margin, belief
        # With few cards left (all hands together), look at every legal move with many more sampled hands: the
        # hidden cards are few, so sampled worlds are close to the truth and the extra search is cheap.
        self.endgame_cards, self.endgame_worlds, self.endgame_topk = endgame_cards, endgame_worlds, endgame_topk
        # With very few cards left, solve sampled worlds exactly instead of playing them out with the policy.
        self.solve_cards, self.solve_worlds, self.solve_budget = solve_cards, solve_worlds, solve_budget

    def act(self, obs: dict) -> int:
        legal = obs["legal"]
        if len(legal) == 1:
            return 0
        if sum(obs["counts"]) <= self.solve_cards:
            res = solve_choice(self.actor, obs, self.rng, self.solve_worlds, self.solve_budget, self.belief)
            if res is not None:
                i, mean = res
                self.info = {"solved": {f"{legal[j].combo} x{len(legal[j].cards)}": {"value": round(float(x), 2)}
                                        for j, x in enumerate(mean)}}
                return i
        if sum(obs["counts"]) <= self.endgame_cards:
            i, report = search_choice(self.actor, obs, self.rng, self.endgame_worlds, min(len(legal), self.endgame_topk), min_prob=0.0,
                                      margin=self.margin, belief=self.belief)
        else:
            i, report = search_choice(self.actor, obs, self.rng, self.worlds, self.topk, margin=self.margin,
                                      belief=self.belief)
        if report["searched"]:
            self.info = {"search": {f"{legal[j].combo} x{len(legal[j].cards)}": {"p": pr, "value": v}
                                    for j, pr, v in report["cands"]}}
        return i
