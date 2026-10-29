"""Combination types, comparison, classification of a card set, and legal-move generation.

Combos: single, pair, triple, full house (triple + pair), straight (exactly 5),
tube (3 consecutive pairs), plate (2 consecutive triples), and the bombs:
4-10 of a kind, straight flush, and the four jokers. Bomb order:
4 < 5 < straight flush < 6 < 7 < 8 < 9 < 10 < jokers.

Sequences use natural rank order (the level rank sits at its natural place)
and the ace may be low (A2345) or high (TJQKA). Wilds (hearts of the level
rank) stand in for any non-joker card.

Move generation works on rank counts: for each rank-level combo it uses the
fewest wilds possible (a wild is never worse to keep than the natural card it
would replace), then picks concrete cards, preferring suits that are least
useful for straight flushes.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .cards import BJ, BJ_VALUE, LEVEL_VALUE, SJ, SJ_VALUE, ctype, value, wild_type


class Kind(IntEnum):
    PASS = 0
    SINGLE = 1
    PAIR = 2
    TRIPLE = 3
    FULL_HOUSE = 4
    STRAIGHT = 5
    TUBE = 6
    PLATE = 7
    BOMB = 8
    STRAIGHT_FLUSH = 9
    JOKER_BOMB = 10


BOMBS = (Kind.BOMB, Kind.STRAIGHT_FLUSH, Kind.JOKER_BOMB)
# Sequence position i -> rank; the ace appears at both ends.
SEQ = [12] + list(range(13))
SEQ_SPEC = {Kind.STRAIGHT: (5, 1), Kind.TUBE: (3, 2), Kind.PLATE: (2, 3)}  # (length, copies per rank)


@dataclass(frozen=True)
class Combo:
    kind: Kind
    value: int = 0  # level-aware rank value, or sequence start position
    size: int = 0   # number of cards

    @property
    def is_bomb(self) -> bool:
        return self.kind in BOMBS

    def power(self) -> tuple[int, int]:
        if self.kind == Kind.JOKER_BOMB:
            return 100, 0
        if self.kind == Kind.STRAIGHT_FLUSH:
            return 11, self.value
        return 2 * self.size, self.value

    def beats(self, other: Combo | None) -> bool:
        if self.kind == Kind.PASS:
            return False
        if other is None:
            return True
        if self.is_bomb:
            return not other.is_bomb or self.power() > other.power()
        return not other.is_bomb and self.kind == other.kind and self.value > other.value

    def __str__(self) -> str:
        return self.kind.name.lower().replace("_", " ")


PASS_COMBO = Combo(Kind.PASS)


@dataclass(frozen=True)
class Move:
    combo: Combo
    cards: tuple[int, ...] = ()

    @property
    def is_pass(self) -> bool:
        return self.combo.kind == Kind.PASS


PASS = Move(PASS_COMBO)


# ---- classification of a concrete card set ----------------------------------

class _Counts:
    """Natural (non-wild) counts per rank and per (suit, rank), plus wilds and jokers."""

    def __init__(self, cards, level: int):
        w = wild_type(level)
        self.nr = [0] * 13
        self.suited = [[0] * 13 for _ in range(4)]
        self.wild = self.sj = self.bj = 0
        for c in cards:
            t = ctype(c)
            if t == w:
                self.wild += 1
            elif t == SJ:
                self.sj += 1
            elif t == BJ:
                self.bj += 1
            else:
                self.nr[t % 13] += 1
                self.suited[t // 13][t % 13] += 1


def _same_rank_value(r: int, level: int) -> int:
    return LEVEL_VALUE if r == level else r


def classify(cards, level: int) -> list[Combo]:
    """Every combo this exact set of cards can be read as."""
    n = len(cards)
    if n == 0:
        return []
    c = _Counts(cards, level)
    out: set[Combo] = set()
    if n == 1:
        return [Combo(Kind.SINGLE, value(ctype(cards[0]), level), 1)]
    jokers = c.sj + c.bj
    natural = sum(c.nr)

    def fits(demand: dict[int, int]) -> bool:
        # Naturals must all fall inside the demand; wilds cover the rest.
        return sum(demand.values()) == n - jokers and all(c.nr[r] <= demand.get(r, 0) for r in range(13) if c.nr[r])

    if jokers:
        if n == 2 and (c.sj == 2 or c.bj == 2):
            out.add(Combo(Kind.PAIR, SJ_VALUE if c.sj else BJ_VALUE, 2))
        if n == 4 and c.sj == 2 and c.bj == 2:
            out.add(Combo(Kind.JOKER_BOMB, 0, 4))
        if n == 5 and (c.sj, c.bj) in ((2, 0), (0, 2)):
            for a in range(13):
                if (c.nr[a] or a == level) and fits({a: 3}):
                    out.add(Combo(Kind.FULL_HOUSE, _same_rank_value(a, level), 5))
        return sorted(out, key=lambda x: (x.is_bomb, x.power()))

    for r in range(13):
        if (c.nr[r] or r == level) and fits({r: n}):
            v = _same_rank_value(r, level)
            if n == 2:
                out.add(Combo(Kind.PAIR, v, 2))
            elif n == 3:
                out.add(Combo(Kind.TRIPLE, v, 3))
            elif n >= 4:
                out.add(Combo(Kind.BOMB, v, n))
    if n == 5:
        for a in range(13):
            for b in range(13):
                if a != b and (c.nr[a] or a == level) and fits({a: 3, b: 2}):
                    out.add(Combo(Kind.FULL_HOUSE, _same_rank_value(a, level), 5))
    for kind, (length, copies) in SEQ_SPEC.items():
        if n != length * copies:
            continue
        for i in range(len(SEQ) - length + 1):
            if fits({SEQ[i + k]: copies for k in range(length)}):
                out.add(Combo(kind, i, n))
    if n == 5 and natural:
        suits = {s for s in range(4) if any(c.suited[s])}
        if len(suits) == 1:
            s = suits.pop()
            for i in range(len(SEQ) - 4):
                if fits({SEQ[i + k]: 1 for k in range(5)}):
                    out.add(Combo(Kind.STRAIGHT_FLUSH, i, 5))
    return sorted(out, key=lambda x: (x.is_bomb, x.power(), x.kind, x.value))


def interpret(cards, level: int, table: Combo | None) -> Combo | None:
    """The reading of `cards` to use when played over `table` (None = leading).

    Following: the highest same-kind reading that beats the table, else the
    weakest bomb that does. Leading: the strongest reading (a bomb if possible).
    """
    combos = classify(cards, level)
    if table is None:
        return max(combos, key=lambda x: (x.is_bomb, x.power() if x.is_bomb else (0, 0), x.value), default=None)
    same = [x for x in combos if not x.is_bomb and x.beats(table)]
    if same:
        return max(same, key=lambda x: x.value)
    bombs = [x for x in combos if x.is_bomb and x.beats(table)]
    return min(bombs, key=lambda x: x.power(), default=None)


# ---- legal moves ------------------------------------------------------------

class _Picker:
    """Chooses concrete card ids for rank-level demands."""

    def __init__(self, hand, level: int):
        self.w = wild_type(level)
        self.by_type: dict[int, list[int]] = {}
        for c in hand:
            self.by_type.setdefault(ctype(c), []).append(c)
        self.counts = c = _Counts(hand, level)
        self.wild = self.by_type.get(self.w, [])
        # Naturals per rank, suits with the fewest same-suit neighbours first,
        # so ordinary plays don't break up straight-flush material.
        self.nat: list[list[int]] = []
        has = [[x > 0 for x in c.suited[s]] for s in range(4)]
        for r in range(13):
            def score(s, r=r):
                return sum(has[s][max(0, r - 4):r + 5]) - has[s][r], s
            self.nat.append([x for s in sorted(range(4), key=score) if s * 13 + r != self.w
                             for x in self.by_type.get(s * 13 + r, [])])

    def take(self, demand: dict[int, int], suit: int | None = None) -> tuple[int, ...] | None:
        cards: list[int] = []
        need_wild = 0
        for r, k in demand.items():
            if suit is None:
                got = self.nat[r][:k]
            else:
                got = [] if suit * 13 + r == self.w else self.by_type.get(suit * 13 + r, [])[:k]
            cards += got
            need_wild += k - len(got)
        if need_wild > len(self.wild):
            return None
        return tuple(cards + self.wild[:need_wild])


def legal_moves(hand, level: int, table: Combo | None) -> list[Move]:
    """All moves from `hand` that may be played over `table` (None = leading, PASS excluded)."""
    p = _Picker(hand, level)
    c = p.counts
    moves: dict[tuple, Move] = {}

    def add(combo: Combo, demand: dict[int, int] | None = None, suit: int | None = None, extra=()) -> None:
        if not combo.beats(table):  # cheap filter before picking cards
            return
        cards = p.take(demand, suit) if demand else ()
        if cards is not None:
            cards += tuple(extra)
            moves.setdefault((combo, tuple(sorted(ctype(x) for x in cards))), Move(combo, cards))

    def avail(r: int) -> bool:  # a same-rank combo needs a natural card, except at the level rank
        return c.nr[r] > 0 or (r == level and c.wild > 0)

    for r in range(13):
        if not avail(r):
            continue
        v = _same_rank_value(r, level)
        for n in range(1, c.nr[r] + c.wild + 1):
            add(Combo({1: Kind.SINGLE, 2: Kind.PAIR, 3: Kind.TRIPLE}.get(n, Kind.BOMB), v, n), {r: n})
    for jt, cnt, v in ((SJ, c.sj, SJ_VALUE), (BJ, c.bj, BJ_VALUE)):
        if cnt:
            add(Combo(Kind.SINGLE, v, 1), extra=p.by_type[jt][:1])
        if cnt == 2:
            add(Combo(Kind.PAIR, v, 2), extra=p.by_type[jt])
    if c.sj == 2 and c.bj == 2:
        add(Combo(Kind.JOKER_BOMB, 0, 4), extra=p.by_type[SJ] + p.by_type[BJ])

    # Full houses: any triple with any pair (including a joker pair).
    triples = [r for r in range(13) if avail(r) and c.nr[r] + c.wild >= 3]
    for a in triples:
        va = _same_rank_value(a, level)
        for b in range(13):
            if b != a and avail(b) and c.nr[b] + c.wild >= 2:
                add(Combo(Kind.FULL_HOUSE, va, 5), {a: 3, b: 2})
        for jt, cnt in ((SJ, c.sj), (BJ, c.bj)):
            if cnt == 2:
                add(Combo(Kind.FULL_HOUSE, va, 5), {a: 3}, extra=p.by_type[jt])

    for kind, (length, copies) in SEQ_SPEC.items():
        for i in range(len(SEQ) - length + 1):
            demand = {SEQ[i + k]: copies for k in range(length)}
            add(Combo(kind, i, length * copies), demand)
    for s in range(4):
        for i in range(len(SEQ) - 4):
            demand = {SEQ[i + k]: 1 for k in range(5)}
            if sum(1 for r in demand if c.suited[s][r]) + c.wild >= 5:
                add(Combo(Kind.STRAIGHT_FLUSH, i, 5), demand, suit=s)
    out = list(moves.values())
    out.sort(key=lambda m: (m.combo.is_bomb, m.combo.kind, m.combo.power() if m.combo.is_bomb else (0, m.combo.value)))
    return out

