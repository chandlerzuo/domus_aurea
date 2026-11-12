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


def _options(st: St, r: int):
    """The sets the lowest remaining rank `r` can be part of, as lists of (rank, copies) demands."""
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
    return options


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
        options = _options(st, r)
        best = min((v for v in (self._step(st, d) for d in options) if v is not None), default=255)
        self.memo[k] = best
        return best


def min_sets(hand, level: int) -> int:
    return Planner().min_sets(St.from_cards(hand, level))


# ---- the split itself (for showing the user their hand grouped into sets) -------------------------------------

def _set_value(demand, level: int) -> float:
    """How much a set is worth keeping together: bombs and long/high combos most, loose low singles least.
    A stand-in for "chance of winning": the policy network cannot score a split of the hand directly."""
    n = sum(k for _, k in demand)
    top = max(r for r, _ in demand)
    h = (13 if top == level else top) / 13        # 0..1, the level rank is the highest natural rank
    if len(demand) == 1:
        k = demand[0][1]
        return {1: 0.3 + 0.7 * h, 2: 1.0 + 0.7 * h, 3: 1.6 + 0.7 * h}.get(k, 5.0 + 0.4 * k + 0.7 * h)
    ks = sorted(k for _, k in demand)
    if ks == [2, 3]:
        return 2.2 + 0.7 * h                                   # full house
    return {5: 2.0, 6: 3.0}.get(n, 3.0) + 0.7 * h              # straight / tube / plate


def best_split(hand, level: int) -> list[list[int]]:
    """The hand as groups of card ids: the fewest sets, and among those the one worth the most (see `_set_value`).
    Every card is in exactly one group."""
    st0 = St.from_cards(hand, level)
    memo: dict = {}

    def solve(st: St):
        k = st.key()
        if k in memo:
            return memo[k][:2]
        r = next((i for i in range(13) if st.nr[i] > 0), None)
        if r is None:
            jokers = 1 if (st.sj == 2 and st.bj == 2) else int(st.sj > 0) + int(st.bj > 0)
            memo[k] = (jokers + (st.w + 1) // 2, 0.0, None)
            return memo[k][:2]
        best = (255, 0.0, None)
        for d in _options(st, r):
            nr, deficit = list(st.nr), 0
            for rr, need in d:
                have = min(nr[rr], need)
                nr[rr] -= have
                deficit += need - have
            if deficit > st.w:
                continue
            sets, score = solve(St(nr, st.sj, st.bj, st.w - deficit))
            cand = (1 + sets, _set_value(d, level) + score, d)
            if (cand[0], -cand[1]) < (best[0], -best[1]):
                best = cand
        memo[k] = best
        return best[:2]

    solve(st0)
    by_rank: dict[int, list[int]] = {}
    wilds, sj, bj = [], [], []
    wt = wild_type(level)
    for c in hand:
        t = ctype(c)
        if t == wt:
            wilds.append(c)
        elif t == SJ:
            sj.append(c)
        elif t == BJ:
            bj.append(c)
        else:
            by_rank.setdefault(t % 13, []).append(c)
    groups: list[list[int]] = []
    st = st0
    while True:
        entry = memo.get(st.key())
        if entry is None or entry[2] is None:
            break
        nr, group = list(st.nr), []
        deficit = 0
        for rr, need in entry[2]:
            have = min(nr[rr], need)
            nr[rr] -= have
            group += [by_rank[rr].pop() for _ in range(have)]
            deficit += need - have
        group += [wilds.pop() for _ in range(deficit)]
        groups.append(group)
        st = St(nr, st.sj, st.bj, st.w - deficit)
    if st.sj == 2 and st.bj == 2:
        groups.append(sj + bj)
    else:
        if sj:
            groups.append(sj)
        if bj:
            groups.append(bj)
    for i in range(0, len(wilds), 2):
        groups.append(wilds[i:i + 2])
    return groups
