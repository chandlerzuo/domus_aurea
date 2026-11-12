"""Constructed positions for training and testing against the "saved runout" pattern.

Human players beat the AI by saving a handful of strong combos -- say a full house, a bomb and a high single, ten cards
in all -- and, once they hold the lead, playing them in consecutive tricks so the AI never gets to use its leftover
cards. `runout_position` builds such a deal: one seat holds exactly a runout hand (and leads in 40% of the positions); the other
three seats hold ordinary random hands, small enough that racing the runout is possible.
"""
from __future__ import annotations

import numpy as np

from ..agents import HeuristicAgent, RunoutAgent
from ..cards import BJ, SJ, is_wild
from ..game import Deal, partner, team

N_PER_DECK = 54


def _ids(rank: int, n: int, rng: np.random.Generator, used: set[int]) -> list[int]:
    """n distinct cards of one rank (suits and decks mixed), not yet used."""
    pool = [copy * N_PER_DECK + suit * 13 + rank for copy in (0, 1) for suit in range(4)]
    pool = [c for c in pool if c not in used]
    pick = [int(c) for c in rng.choice(pool, n, replace=False)]
    used.update(pick)
    return pick


def runout_hand(rng: np.random.Generator, level: int) -> list[frozenset]:
    """A runout: 2-3 strong combos (never using wild cards), as a list of card sets."""
    used: set[int] = set()
    ranks = [r for r in range(13) if r != level]

    def pick_rank(avoid=()):
        return int(rng.choice([r for r in ranks if r not in avoid]))

    def run(length: int):
        starts = [r for r in ranks if all(r + k in ranks for k in range(length))]
        return int(rng.choice(starts))

    def high_single():
        opts = [SJ, BJ, SJ + N_PER_DECK, BJ + N_PER_DECK] + [copy * N_PER_DECK + s * 13 + level for copy in (0, 1) for s in (0, 2, 3)]
        opts = [c for c in opts if c not in used and not is_wild(c, level)]
        c = int(rng.choice(opts))
        used.add(c)
        return [c]

    # the weaker templates (no bomb) leave the other side something to fight with
    kind = rng.choice(["fh_bomb_single", "plate_bomb_pair", "fh_bomb", "bomb_bomb_single", "fh_single", "plate_single"],
                      p=[0.35, 0.15, 0.15, 0.05, 0.15, 0.15])
    combos: list[list[int]] = []
    if kind == "fh_bomb_single":
        a = pick_rank()
        b = pick_rank((a,))
        c = pick_rank((a, b))
        combos = [_ids(a, 3, rng, used) + _ids(b, 2, rng, used), _ids(c, 4, rng, used), high_single()]
    elif kind == "plate_bomb_pair":
        r = run(2)
        c = pick_rank((r, r + 1))
        d = pick_rank((r, r + 1, c))
        combos = [_ids(r, 3, rng, used) + _ids(r + 1, 3, rng, used), _ids(c, 4, rng, used), _ids(d, 2, rng, used)]
    elif kind == "fh_bomb":
        a = pick_rank()
        b = pick_rank((a,))
        c = pick_rank((a, b))
        combos = [_ids(a, 3, rng, used) + _ids(b, 2, rng, used), _ids(c, 4, rng, used)]
    elif kind == "fh_single":
        a = pick_rank()
        b = pick_rank((a,))
        combos = [_ids(a, 3, rng, used) + _ids(b, 2, rng, used), high_single()]
    elif kind == "plate_single":
        r = run(2)
        combos = [_ids(r, 3, rng, used) + _ids(r + 1, 3, rng, used), high_single()]
    else:
        a = pick_rank()
        b = pick_rank((a,))
        combos = [_ids(a, 4, rng, used), _ids(b, 4, rng, used), high_single()]
    return [frozenset(c) for c in combos]


def runout_position(rng: np.random.Generator):
    """(deal, runout seat, agents for the runout team) -- the runout seat is on lead; the learner plays the other team."""
    level = int(rng.integers(13))
    plan = runout_hand(rng, level)
    h = int(rng.integers(4))
    mine = set().union(*plan)
    rest = [c for c in rng.permutation(2 * N_PER_DECK) if int(c) not in mine]
    # The other side has to be able to fight back: with 9+ cards each it cannot race a ten-card runout at all.
    lo, hi = 4, int(rng.choice([8, 11, 14]))
    sizes = {partner(h): int(rng.integers(4, 13)), (h + 1) % 4: int(rng.integers(lo, hi + 1)), (h + 3) % 4: int(rng.integers(lo, hi + 1))}
    hands: list[list[int]] = [[] for _ in range(4)]
    hands[h] = sorted(mine)
    at = 0
    for s, n in sizes.items():
        hands[s] = [int(c) for c in rest[at:at + n]]
        at += n
    leader = h if rng.random() < 0.4 else int(rng.choice([(h + 1) % 4, (h + 3) % 4]))   # sometimes the runout player has the lead already
    d = Deal(hands, level, leader, (int(rng.integers(13)), int(rng.integers(13))), None)
    gone = [int(c) for c in rest[at:]]               # cards played earlier in this deal, shared out between the seats
    for i, c in enumerate(gone):
        d.played[i % 4].append(c)
    agents = {h: RunoutAgent(int(rng.integers(2**31)), plan), partner(h): HeuristicAgent(int(rng.integers(2**31)))}
    return d, h, agents


__all__ = ["runout_hand", "runout_position", "team"]
