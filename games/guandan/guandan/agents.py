"""Baseline agents. An agent picks an index into obs["legal"] and chooses tribute returns."""
from __future__ import annotations

import numpy as np

from .cards import ctype, is_wild, value
from .combos import Kind, Move, legal_moves
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


class HoarderAgent(HeuristicAgent):
    """The "save a runout" pattern that human players used to beat the AI.

    Early on it keeps a reserve of strong combos back -- its best bomb, its best full house / plate / tube /
    straight, and its highest single or pair -- and sheds everything else like the heuristic player. Once only the
    reserve is left it leads the combos one after another (the non-bomb combo first, then the bomb, then the
    high single), so the opponents never get to play their leftover cards in between. When it must follow with only
    the reserve left, it takes the lead with the cheapest reserve combo that beats the table.
    """

    name = "hoarder"

    def __init__(self, seed: int | None = None, plan: list[frozenset] | None = None):
        super().__init__(seed)
        self.plan: list[frozenset] | None = plan      # combos to save and then lead in a row (given, or chosen from the hand)
        self.reserve: set[int] = set().union(*plan) if plan else set()

    def _make_plan(self, hand, level) -> list[frozenset]:
        moves = legal_moves(hand, level, None)
        used: set[int] = set()
        plan: list[frozenset] = []

        def take(cands, key):
            free = [m for m in cands if not used & set(m.cards)]
            if free:
                m = max(free, key=key)
                used.update(m.cards)
                plan.append(frozenset(m.cards))

        take([m for m in moves if m.combo.is_bomb], lambda m: m.combo.power())
        take([m for m in moves if m.combo.kind in (Kind.FULL_HOUSE, Kind.PLATE, Kind.TUBE, Kind.STRAIGHT)],
             lambda m: (len(m.cards), _strength(m, level)))
        take([m for m in moves if m.combo.kind in (Kind.SINGLE, Kind.PAIR)], lambda m: _strength(m, level) + 0.01 * len(m.cards))
        return plan if len(plan) >= 2 else []

    def act(self, obs: dict) -> int:
        legal: list[Move] = obs["legal"]
        hand, level, seat, counts = obs["hand"], obs["level"], obs["seat"], obs["counts"]
        for i, m in enumerate(legal):  # going out beats everything
            if len(m.cards) == len(hand):
                return i
        if self.plan is None:
            self.plan = self._make_plan(hand, level)
        self.plan = [c for c in self.plan if c <= set(hand)]   # combos already played drop out
        self.reserve = set().union(*self.plan) if self.plan else set()
        if not self.plan:
            return super().act(obs)
        opp_min = min((counts[s] for s in ((seat + 1) % 4, (seat + 3) % 4) if s not in obs["finished"]), default=27)
        rest = [i for i, m in enumerate(legal) if not m.is_pass and not (set(m.cards) & self.reserve)]
        shedding = any(c not in self.reserve for c in hand)
        if obs["leading"]:
            if shedding and rest:
                return rest[self._lead([legal[i] for i in rest], hand, level, opp_min)]
            run = [i for i, m in enumerate(legal) if frozenset(m.cards) in self.plan]
            if run:  # the runout: the non-bomb combo first, then the bomb, then the high single/pair
                return min(run, key=lambda i: (len(legal[i].cards) <= 2, legal[i].combo.is_bomb, -len(legal[i].cards)))
            return super().act(obs)
        if obs["table_seat"] == partner(seat):
            return 0
        if shedding and rest:
            sub = [legal[0]] + [legal[i] for i in rest]
            j = self._follow(obs, sub, hand, level, opp_min)
            return 0 if j == 0 else rest[j - 1]
        beat = [i for i, m in enumerate(legal) if not m.is_pass and frozenset(m.cards) in self.plan]
        if beat and not shedding:
            return min(beat, key=lambda i: (legal[i].combo.is_bomb, legal[i].combo.power()))
        return 0


class RunoutAgent(HoarderAgent):
    """A hoarder whose whole hand is the runout: it leads the given combos one after another."""

    name = "runout"


class PlanAgent(HeuristicAgent):
    """Plays by hand decomposition: split the hand into as few sets as possible and play the plan.

    Leading: the lowest set whose removal shortens the plan (a move that completes a set of the best split); if none
    does, the move that leaves the fewest sets. Following: never overtake the partner; beat an opponent with the
    cheapest move that completes a set; otherwise fall back to the heuristic's rules.
    """

    name = "plan"

    def act(self, obs: dict) -> int:
        from .rl.plan import Planner, St
        legal: list[Move] = obs["legal"]
        hand, level, seat = obs["hand"], obs["level"], obs["seat"]
        for i, m in enumerate(legal):  # going out beats everything
            if len(m.cards) == len(hand):
                return i
        planner, st = Planner(), St.from_cards(hand, level)
        now = planner.min_sets(st)
        scored = [(i, planner.min_sets(st.minus(m.cards, level)), m) for i, m in enumerate(legal) if not m.is_pass]
        free = [(i, a, m) for i, a, m in scored if a < now and not m.combo.is_bomb]
        if obs["leading"]:
            pool = free or [(i, a, m) for i, a, m in scored if not m.combo.is_bomb] or scored
            return min(pool, key=lambda t: (t[1], _strength(t[2], level), -len(t[2].cards)))[0]
        if obs["table_seat"] == partner(seat):
            return 0
        if free:
            counts = obs["counts"]
            opp_min = min((counts[s] for s in ((seat + 1) % 4, (seat + 3) % 4) if s not in obs["finished"]), default=27)
            return min(free, key=lambda t: (_strength(t[2], level), t[1]))[0]
        return self._follow(obs, legal, hand, level, min((obs["counts"][s] for s in ((seat + 1) % 4, (seat + 3) % 4)
                                                          if s not in obs["finished"]), default=27))


AGENTS = {"random": RandomAgent, "heuristic": HeuristicAgent, "hoarder": HoarderAgent, "plan": PlanAgent}
