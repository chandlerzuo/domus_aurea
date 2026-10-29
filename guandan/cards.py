"""Cards: two standard decks plus four jokers (108 cards).

A card id is 0..107; its *type* is id % 54. Types 0..51 are suit * 13 + rank
(rank 0 = '2' ... 12 = 'A'; suits S, H, C, D), 52 is the small joker and 53
the big joker. Every type appears exactly twice.

The current level rank is promoted above the ace for singles, pairs, triples,
full houses and bombs; the two hearts of the level rank are wild.
"""
from __future__ import annotations

RANKS = "23456789TJQKA"
SUITS = "SHCD"
HEARTS = 1
SJ, BJ = 52, 53
N_TYPES = 54
N_CARDS = 108
ACE = 12
LEVEL_VALUE, SJ_VALUE, BJ_VALUE = 13, 14, 15


def ctype(card: int) -> int:
    return card % N_TYPES


def rank_of(t: int) -> int | None:
    return None if t >= SJ else t % 13


def suit_of(t: int) -> int | None:
    return None if t >= SJ else t // 13


def wild_type(level: int) -> int:
    return HEARTS * 13 + level


def is_wild(card: int, level: int) -> bool:
    return ctype(card) == wild_type(level)


def value(t: int, level: int) -> int:
    """Level-aware strength of one card: 2..A = 0..12 except the level rank (13), jokers 14 and 15."""
    if t == SJ:
        return SJ_VALUE
    if t == BJ:
        return BJ_VALUE
    r = t % 13
    return LEVEL_VALUE if r == level else r


def type_str(t: int) -> str:
    if t == SJ:
        return "sj"
    if t == BJ:
        return "BJ"
    return RANKS[t % 13] + SUITS[t // 13].lower()


def card_str(card: int) -> str:
    return type_str(ctype(card))


def parse_type(s: str) -> int:
    if s in ("sj", "SJ"):
        return SJ
    if s == "BJ":
        return BJ
    return SUITS.index(s[1].upper()) * 13 + RANKS.index(s[0].upper())


def parse(cards: str) -> list[int]:
    """'3s 3h sj' -> card ids, using the first copy of each type, then the second."""
    out: list[int] = []
    for tok in cards.split():
        t = parse_type(tok)
        out.append(t + N_TYPES if t in out else t)
    return out


def sort_key(card: int, level: int) -> tuple[int, int]:
    t = ctype(card)
    return value(t, level), t
