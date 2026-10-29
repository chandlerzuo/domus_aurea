"""Baseline agents. An agent picks an index into obs["legal"] and chooses tribute returns."""
from __future__ import annotations

import numpy as np

from .cards import ctype, is_wild, value
from .combos import Move
from .game import partner, return_options


class Agent:
    name = "agent"

    def __init__(self, seed: int | None = None):
        self.rng = np.random.default_rng(seed)
        self.info: dict = {}

    def act(self, obs: dict) -> int:
        raise NotImplementedError

    def choose_return(self, hand: list[int], level: int) -> int:
        """Return the lowest card that is not part of a pair or better."""
        opts = return_options(hand)
        ranks = [ctype(c) % 13 if ctype(c) < 52 else 13 + ctype(c) for c in hand]
        count = {r: ranks.count(r) for r in ranks}
        return min(opts, key=lambda c: (count[ctype(c) % 13 if ctype(c) < 52 else 13 + ctype(c)] > 1,
                                        value(ctype(c), level), c))


class RandomAgent(Agent):
    name = "random"

    def act(self, obs: dict) -> int:
        return int(self.rng.integers(len(obs["legal"])))


def _rank_counts(hand: list[int], level: int) -> list[int]:
    nr = [0] * 15  # 13 ranks, small joker, big joker; wilds excluded
    for c in hand:
        t = ctype(c)
        if not is_wild(c, level):
            nr[t % 13 if t < 52 else t - 39] += 1
    return nr


def structure_cost(hand: list[int], move: Move, level: int) -> float:
    """How much a move damages the rest of the hand: broken bombs, split pairs/triples, spent wilds."""
    nr = _rank_counts(hand, level)
    used = [0] * 15
    wilds = 0
    for c in move.cards:
        t = ctype(c)
        if is_wild(c, level):
            wilds += 1
        else:
            used[t % 13 if t < 52 else t - 39] += 1
    bomb = move.combo.is_bomb
    cost = 3.0 * wilds
    for r in range(15):
        if not used[r]:
            continue
        before, after = nr[r], nr[r] - used[r]
        if before >= 4 and not bomb:
            cost += 8.0 if after == 0 else 6.0
        elif before >= 4 and after > 0:
            cost += 2.0
        elif before in (2, 3) and after > 0:
            cost += 1.5
    return cost


def _strength(move: Move, level: int) -> float:
    """Rough level-aware height of the cards in a move (0..15)."""
    vals = [value(ctype(c), level) for c in move.cards]
    return sum(vals) / len(vals)


class HeuristicAgent(Agent):
    """Rule-based player.

    Leading: shed the lowest, longest combo that keeps the hand's structure,
    and avoid leading singles/pairs that an opponent about to go out could
    use. Following: never overtake the partner; beat opponents cheaply, and
    spend big cards or bombs only when an opponent is close to going out or
    when it nearly empties the hand.
    """

    name = "heuristic"

    def act(self, obs: dict) -> int:
        legal: list[Move] = obs["legal"]
        hand, level, seat = obs["hand"], obs["level"], obs["seat"]
        counts = obs["counts"]
        opp_min = min((counts[s] for s in ((seat + 1) % 4, (seat + 3) % 4) if s not in obs["finished"]), default=27)
        for i, m in enumerate(legal):  # going out beats everything
            if len(m.cards) == len(hand):
                return i
        if obs["leading"]:
            return self._lead(legal, hand, level, opp_min)
        return self._follow(obs, legal, hand, level, opp_min)

    def _lead(self, legal, hand, level, opp_min) -> int:
        def cost(m: Move) -> float:
            c = _strength(m, level) - 0.9 * len(m.cards) + structure_cost(hand, m, level)
            if m.combo.is_bomb:
                c += 25.0
            if opp_min <= 2 and len(m.cards) <= opp_min:  # don't feed an opponent's last cards
                c += 10.0 + 2.0 * (15 - _strength(m, level))
            return c
        return min(range(len(legal)), key=lambda i: cost(legal[i]))

    def _follow(self, obs, legal, hand, level, opp_min) -> int:
        seat, table_seat = obs["seat"], obs["table_seat"]
        counts = obs["counts"]
        if table_seat == partner(seat):
            # Never overtake the partner.
            return 0
        options = [(i, m) for i, m in enumerate(legal) if not m.is_pass]
        if not options:
            return 0
        urgent = counts[table_seat] <= 6 or opp_min <= 4
        plain = [(i, m) for i, m in options if not m.combo.is_bomb]
        if plain:
            i, m = min(plain, key=lambda im: _strength(im[1], level) + structure_cost(hand, im[1], level))
            cost = structure_cost(hand, m, level)
            big = _strength(m, level) >= 13 and counts[table_seat] > 10 and len(hand) > 10
            if cost < 6.0 and not (big and self.rng.random() < 0.5):
                return i
            if urgent:
                return i
        bombs = [(i, m) for i, m in options if m.combo.is_bomb]
        if bombs and (urgent or len(hand) - len(min(bombs, key=lambda im: im[1].combo.power())[1].cards) <= 6):
            return min(bombs, key=lambda im: (im[1].combo.power(), structure_cost(hand, im[1], level)))[0]
        return 0


AGENTS = {"random": RandomAgent, "heuristic": HeuristicAgent}
