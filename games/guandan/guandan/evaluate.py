"""Head-to-head evaluation with duplicate deals.

Each pair of deals uses the same cards, level and leader twice with the teams
swapped between seat pairs, which removes most of the card luck. Score is the
signed level gain per deal for team A (+up when A wins the deal, -up when B
does). Every deal is played at a random level, without tribute.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from .agents import Agent
from .game import Deal, deal_cards, team

Factory = Callable[[int], Agent]


def play_deal(agents: list[Agent], hands, level: int, leader: int) -> tuple[int, int]:
    d = Deal(hands, level, leader)
    while not d.done:
        obs = d.observation(d.to_act)
        d.play(obs["legal"][agents[d.to_act].act(obs)])
    return d.result()


def duplicate(a: Factory, b: Factory, pairs: int, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    scores, wins = [], 0
    for k in range(pairs):
        hands = deal_cards(rng)
        level, leader = int(rng.integers(13)), int(rng.integers(4))
        for a_team in (0, 1):
            agents = [(a if team(s) == a_team else b)(seed * 100003 + 4 * k + s) for s in range(4)]
            win, up = play_deal(agents, hands, level, leader)
            scores.append(up if win == a_team else -up)
            wins += win == a_team
    s = np.asarray(scores, dtype=float)
    return {"deals": len(s), "points_per_deal": float(s.mean()),
            "stderr": float(s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 1 else 0.0,
            "win_rate": wins / len(s)}
