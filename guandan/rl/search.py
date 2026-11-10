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
from ..cards import N_CARDS
from ..combos import Kind
from . import fast
from .features import encode_actions, encode_state
from .policy import policy_step

core = fast.core


def _tuple(move) -> tuple:
    return int(move.combo.kind), move.combo.value, move.combo.size, [int(c) for c in move.cards]


def sample_world(obs: dict, rng: np.random.Generator, version: int):
    """One possible state of the whole table consistent with what this player can see."""
    seat = obs["seat"]
    hands: list = [None] * 4
    hands[seat] = [int(c) for c in obs["hand"]]
    seen = set(obs["hand"]) | {c for p in obs["played"] for c in p}
    unseen = [c for c in range(N_CARDS) if c not in seen]
    rng.shuffle(unseen)
    at = 0
    for s in range(4):
        if s != seat:
            n = obs["counts"][s]
            hands[s] = [int(c) for c in unseen[at:at + n]]
            at += n
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
                  min_prob: float = 0.03):
    """Candidate moves, the policy's probabilities over all legal moves, and each candidate's
    estimated result (levels for the player's team). `None` when there is only one candidate."""
    v = actor.version
    _, _, p = policy_step(actor, encode_state(obs, v), encode_actions(obs, v), rng, greedy=True)
    order = [int(j) for j in np.argsort(-p)]
    cand = [order[0]] + [j for j in order[1:topk] if p[j] >= min_prob]
    if len(cand) < 2:
        return None
    ws = [sample_world(obs, rng, v) for _ in range(worlds)]
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


def improved_policy(p: np.ndarray, cand: list[int], val: np.ndarray, tau: float) -> np.ndarray:
    """The policy shifted toward better-looking candidates: they share their original total
    probability in proportion to p * exp(value / tau); every other move keeps its probability."""
    w = np.log(p[cand] + 1e-12) + np.asarray(val) / tau
    w = np.exp(w - w.max())
    t = p.copy()
    t[cand] = p[cand].sum() * w / w.sum()
    return t


def search_choice(actor, obs: dict, rng: np.random.Generator, worlds: int = 16, topk: int = 3,
                  min_prob: float = 0.03, margin: float = 0.0) -> tuple[int, dict]:
    """Index into obs["legal"] and a report: candidates with their policy probability and
    estimated result (levels for the player's team)."""
    res = search_values(actor, obs, rng, worlds, topk, min_prob)
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

    def __init__(self, actor, seed: int | None = None, worlds: int = 16, topk: int = 3, margin: float = 0.0):
        super().__init__(seed)
        self.actor, self.worlds, self.topk, self.margin = actor, worlds, topk, margin

    def act(self, obs: dict) -> int:
        legal = obs["legal"]
        if len(legal) == 1:
            return 0
        i, report = search_choice(self.actor, obs, self.rng, self.worlds, self.topk, margin=self.margin)
        if report["searched"]:
            self.info = {"search": {f"{legal[j].combo} x{len(legal[j].cards)}": {"p": pr, "value": v}
                                    for j, pr, v in report["cands"]}}
        return i
