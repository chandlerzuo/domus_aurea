"""Hand decomposition: the fewest sets a hand splits into (leads needed to go out unopposed).

A line-for-line mirror of rust/src/plan.rs (the two are tested against each other); see there for the details.
"""
from __future__ import annotations

from ..cards import BJ, SJ, ctype, wild_type


class St:
    __slots__ = ("nr", "sj", "bj", "w")

    def __init__(self, nr, sj, bj, w):
        self.nr, self.sj, self.bj, self.w = nr, sj, bj, w

    @staticmethod
    def from_cards(cards, level: int) -> "St":
        wt = wild_type(level)
        s = St([0] * 13, 0, 0, 0)
        for c in cards:
            t = ctype(c)
            if t == wt:
                s.w += 1
            elif t == SJ:
                s.sj += 1
            elif t == BJ:
                s.bj += 1
            else:
                s.nr[t % 13] += 1
        return s

    def minus(self, cards, level: int) -> "St":
        wt = wild_type(level)
        s = St(list(self.nr), self.sj, self.bj, self.w)
        for c in cards:
            t = ctype(c)
            if t == wt:
                s.w = max(0, s.w - 1)
            elif t == SJ:
                s.sj = max(0, s.sj - 1)
            elif t == BJ:
                s.bj = max(0, s.bj - 1)
            else:
                s.nr[t % 13] = max(0, s.nr[t % 13] - 1)
        return s

    def key(self):
        return (*self.nr, self.sj, self.bj, self.w)


class Planner:
    def __init__(self):
        self.memo: dict = {}

    def _step(self, st: St, demand):
        nr, deficit = list(st.nr), 0
        for r, need in demand:
            have = min(nr[r], need)
            nr[r] -= have
            deficit += need - have
        if deficit > st.w:
            return None
        return 1 + self.min_sets(St(nr, st.sj, st.bj, st.w - deficit))

    def min_sets(self, st: St) -> int:
        k = st.key()
        if k in self.memo:
            return self.memo[k]
        r = next((i for i in range(13) if st.nr[i] > 0), None)
        if r is None:
            jokers = 1 if (st.sj == 2 and st.bj == 2) else int(st.sj > 0) + int(st.bj > 0)
            v = jokers + (st.w + 1) // 2
            self.memo[k] = v
            return v
        c = st.nr[r]
        options = [[(r, n)] for n in (1, 2, 3, 4)]
        if c > 4:
            options.append([(r, c)])
        pairs = triples = 0
        for s in range(r + 1, 13):
            if st.nr[s] >= 2 and pairs < 2:
                pairs += 1
                options.append([(r, 3), (s, 2)])
            if st.nr[s] >= 3 and triples < 2:
                triples += 1
                options.append([(r, 2), (s, 3)])
        if r + 4 <= 12:
            options.append([(r, 1), (r + 1, 1), (r + 2, 1), (r + 3, 1), (r + 4, 1)])
        if r + 2 <= 12:
            options.append([(r, 2), (r + 1, 2), (r + 2, 2)])
        if r + 1 <= 12:
            options.append([(r, 3), (r + 1, 3)])
        if r == 0:
            options += [[(12, 1), (0, 1), (1, 1), (2, 1), (3, 1)], [(12, 2), (0, 2), (1, 2)], [(12, 3), (0, 3)]]
        best = min((v for v in (self._step(st, d) for d in options) if v is not None), default=255)
        self.memo[k] = best
        return best


def min_sets(hand, level: int) -> int:
    return Planner().min_sets(St.from_cards(hand, level))
