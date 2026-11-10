"""Guandan rules engine: one deal (`Deal`) and a full match (`Match`).

Seats 0..3 play counter-clockwise in index order; partners sit opposite
(teams are seat % 2). A deal ends as soon as both players of one team are
out. The team with the first finisher goes up 3 levels if the partner came
2nd, 2 if 3rd, 1 if last.

Trick play: the leader plays any combo; the others either beat it (same kind,
higher value, or a bomb) or pass. When everyone still in the deal has passed
since the last play, that player leads again; if they have gone out, their
partner leads (jie feng).

Tribute (from the second deal on): the last finisher gives their highest card
(never a wild) to the first finisher, who returns any card of rank 10 or
lower. If the losing team finished 3rd and 4th, both pay: the bigger tribute
goes to the 1st finisher and the smaller to the 2nd. Holding both big jokers
between the payers cancels the tribute. The payer of the bigger tribute leads
(the 3rd finisher on a tie); with no tribute the 1st finisher leads.

The match is won by the team that wins a deal played at their own level A
with the partner not last. (The common house rule that sends a team back to 2
after three failed attempts at A is not implemented.)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .cards import ACE, BJ, N_CARDS, RANKS, ctype, card_str, is_wild, sort_key, value
from .combos import PASS, Combo, Move, interpret, legal_moves

HAND_SIZE = 27
UPGRADE = {1: 3, 2: 2, 3: 1}  # partner's finishing index (0-based) -> levels gained


def team(seat: int) -> int:
    return seat % 2


def partner(seat: int) -> int:
    return (seat + 2) % 4


class Deal:
    def __init__(self, hands: list[list[int]], level: int, leader: int,
                 team_levels: tuple[int, int] = (0, 0), level_team: int | None = None):
        self.hands = [sorted(h, key=lambda c: sort_key(c, level)) for h in hands]
        self.level = level
        self.team_levels = tuple(team_levels)
        self.level_team = level_team
        self.to_act = leader
        self.table: Move | None = None    # last non-pass play of the current trick
        self.table_seat: int | None = None
        self.passes = 0
        self.finished: list[int] = []
        self.history: list[tuple[int, Move]] = []
        self.played: list[list[int]] = [[] for _ in range(4)]
        self.done = False

    @property
    def leading(self) -> bool:
        return self.table is None

    def active(self, seat: int) -> bool:
        return seat not in self.finished

    def legal(self) -> list[Move]:
        moves = legal_moves(self.hands[self.to_act], self.level, self.table.combo if self.table else None)
        return moves if self.leading else [PASS] + moves

    def move_from_cards(self, cards: list[int]) -> Move:
        """Validate a hand-picked set of cards for the player to act (empty = pass)."""
        if not cards:
            if self.leading:
                raise ValueError("the leader must play")
            return PASS
        hand = set(self.hands[self.to_act])
        if len(set(cards)) != len(cards) or not set(cards) <= hand:
            raise ValueError("those cards are not in your hand")
        combo = interpret(cards, self.level, self.table.combo if self.table else None)
        if combo is None:
            raise ValueError("not a valid combination" if self.leading else "does not beat the table")
        return Move(combo, tuple(cards))

    def play(self, move: Move) -> None:
        if self.done:
            raise ValueError("deal is over")
        seat = self.to_act
        if move.is_pass:
            if self.leading:
                raise ValueError("the leader must play")
            self.passes += 1
        else:
            if not move.combo.beats(self.table.combo if self.table else None):
                raise ValueError("does not beat the table")
            hand = self.hands[seat]
            for c in move.cards:
                hand.remove(c)
            self.played[seat].extend(move.cards)
            self.table, self.table_seat, self.passes = move, seat, 0
            if not hand:
                self.finished.append(seat)
                if self._team_out():
                    self.history.append((seat, move))
                    self._finish()
                    return
        self.history.append((seat, move))
        self._advance()

    def _team_out(self) -> bool:
        return any(sum(1 for s in self.finished if team(s) == t) == 2 for t in (0, 1))

    def _finish(self) -> None:
        self.done = True
        # Unfinished players take the remaining places in turn order after the last finisher.
        last = self.finished[-1]
        for k in range(1, 4):
            s = (last + k) % 4
            if s not in self.finished:
                self.finished.append(s)
        self.to_act = -1

    def _advance(self) -> None:
        responders = sum(1 for s in range(4) if self.active(s) and s != self.table_seat)
        if self.passes >= responders:
            # Trick over: the last player to play leads, or their partner if they are out.
            lead = self.table_seat if self.active(self.table_seat) else partner(self.table_seat)
            self.table, self.table_seat, self.passes = None, None, 0
            self.to_act = lead
            return
        s = self.to_act
        for _ in range(4):
            s = (s + 1) % 4
            if self.active(s):
                break
        self.to_act = s

    def result(self) -> tuple[int, int]:
        """(winning team, levels gained)."""
        first = self.finished[0]
        return team(first), UPGRADE[self.finished.index(partner(first))]

    def observation(self, seat: int) -> dict:
        return {
            "seat": seat, "level": self.level, "hand": list(self.hands[seat]),
            "leading": self.leading, "table": self.table, "table_seat": self.table_seat,
            "counts": [len(h) for h in self.hands], "finished": list(self.finished),
            "history": list(self.history), "played": [list(p) for p in self.played],
            "team_levels": self.team_levels, "level_team": self.level_team,
            "legal": self.legal() if seat == self.to_act and not self.done else [],
        }


def deal_cards(rng: np.random.Generator) -> list[list[int]]:
    deck = rng.permutation(N_CARDS)
    return [sorted(int(c) for c in deck[i * HAND_SIZE:(i + 1) * HAND_SIZE]) for i in range(4)]


def tribute_card(hand: list[int], level: int) -> int:
    """The payer's highest card by level-aware value, never a wild."""
    return max((c for c in hand if not is_wild(c, level)), key=lambda c: sort_key(c, level))


def return_options(hand: list[int]) -> list[int]:
    """Cards that may be returned: rank 2..10 (any card if none)."""
    opts = [c for c in hand if ctype(c) < 52 and ctype(c) % 13 <= 8]
    return opts or list(hand)


@dataclass
class Tribute:
    payer: int
    receiver: int
    card: int
    returned: int | None = None


@dataclass
class Match:
    seed: int | None = None
    team_levels: list[int] = field(default_factory=lambda: [0, 0])
    level_team: int | None = None          # whose level is being played (None = first deal, level 2)
    last_order: list[int] | None = None    # finishing order of the previous deal

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        self.deal: Deal | None = None
        self.tributes: list[Tribute] = []
        self.resisted = False
        self.deals_played = 0
        self.winner: int | None = None
        self.log: list[str] = []

    @property
    def level(self) -> int:
        return 0 if self.level_team is None else self.team_levels[self.level_team]

    @property
    def over(self) -> bool:
        return self.winner is not None

    @property
    def pending_returns(self) -> list[Tribute]:
        return [t for t in self.tributes if t.returned is None]

    def new_deal(self, hands: list[list[int]] | None = None) -> Deal:
        if self.over:
            raise ValueError("match is over")
        level = self.level
        hands = [list(h) for h in (hands or deal_cards(self.rng))]
        self.tributes, self.resisted = [], False
        self.log.append(f"--- Deal {self.deals_played + 1}: playing {RANKS[level]} "
                        f"(levels {RANKS[self.team_levels[0]]}/{RANKS[self.team_levels[1]]}) ---")
        order = self.last_order
        if order is None:
            leader = int(self.rng.integers(4))
        else:
            first = order[0]
            payers = order[2:] if order[1] == partner(first) else order[3:]
            if sum(1 for p in payers for c in hands[p] if ctype(c) == BJ) == 2:
                self.resisted = True
                leader = first
                self.log.append("Tribute resisted (both big jokers)")
            else:
                cards = {p: tribute_card(hands[p], level) for p in payers}
                if len(payers) == 1:
                    pairs = [(payers[0], first)]
                    leader = payers[0]
                else:
                    a, b = payers
                    if value(ctype(cards[b]), level) > value(ctype(cards[a]), level):
                        a, b = b, a
                    pairs = [(a, first), (b, order[1])]
                    leader = a
                for p, r in pairs:
                    hands[p].remove(cards[p])
                    hands[r].append(cards[p])
                    self.tributes.append(Tribute(p, r, cards[p]))
                    self.log.append(f"Seat {p} pays tribute {card_str(cards[p])} to seat {r}")
        self.deal = Deal(hands, level, leader, tuple(self.team_levels), self.level_team)
        return self.deal

    def give_return(self, receiver: int, card: int) -> None:
        t = next((t for t in self.pending_returns if t.receiver == receiver), None)
        if t is None:
            raise ValueError("no return owed")
        d = self.deal
        if card not in return_options(d.hands[receiver]):
            raise ValueError("return a card of rank 10 or lower")
        d.hands[receiver].remove(card)
        d.hands[t.payer].append(card)
        d.hands[t.payer].sort(key=lambda c: sort_key(c, d.level))
        d.hands[receiver].sort(key=lambda c: sort_key(c, d.level))
        t.returned = card
        self.log.append(f"Seat {receiver} returns {card_str(card)} to seat {t.payer}")

    def finish_deal(self) -> tuple[int, int]:
        d = self.deal
        if not d.done:
            raise ValueError("deal not finished")
        win, up = d.result()
        self.deals_played += 1
        if self.level_team == win and self.team_levels[win] == ACE and up >= 2:
            self.winner = win
        self.team_levels[win] = min(ACE, self.team_levels[win] + up)
        self.level_team = win
        self.last_order = list(d.finished)
        self.log.append(f"Deal over: order {d.finished}; team {win} up {up}"
                        + (f"; team {win} wins the match" if self.over else ""))
        return win, up


def card_list(cards) -> str:
    return " ".join(card_str(c) for c in cards)


def combo_label(move: Move) -> str:
    return "pass" if move.is_pass else f"{move.combo} {card_list(move.cards)}"


__all__ = ["Deal", "Match", "Tribute", "Combo", "Move", "PASS", "team", "partner", "deal_cards",
           "tribute_card", "return_options", "combo_label", "card_list", "HAND_SIZE"]
