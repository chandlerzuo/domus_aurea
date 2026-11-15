"""Binary feature encoding for the Q-network (DouZero / DanZero style).

Card sets are 108-bit vectors: two bits per card type ("at least one copy",
"both copies"). Seats are encoded relative to the acting player
(1 = next, 2 = partner, 3 = previous). Everything is 0/1 so it is stored as
uint8 and converted to float on the learner.
"""
from __future__ import annotations

import numpy as np

from ..cards import BJ, SJ, N_TYPES, ctype, is_wild, wild_type
from ..combos import SEQ, Kind, Move
from .plan import Planner, St

CARD_DIM = 2 * N_TYPES
HISTORY = 8
N_KINDS = len(Kind)
STATE_DIM = (CARD_DIM * 5          # hand, unseen, played by next / partner / previous
             + 3 * 28              # cards left per other player (one-hot)
             + CARD_DIM + 4 + N_KINDS  # table cards, who played them, its kind
             + 13 * 3 + 3          # level rank, my team level, their level, whose level
             + 3 + 1               # others finished, leading
             + HISTORY * (CARD_DIM + 4))
ACTION_DIM = CARD_DIM + N_KINDS + 3 + 1 + 16

# Version 2 appends to version 1 (a v1 network is widened with zero weights): 8 older history
# slots on the state; on each action, the hand left after the move (card bits) plus
# unary-coded summary counts. Mirrors rust/src/features.rs.
HISTORY_V2 = 16
STATE_DIM_V2 = STATE_DIM + (HISTORY_V2 - HISTORY) * (CARD_DIM + 4)
AGG = 27 + 6 * 4 + 4 + 2 + 14 * 3
ACTION_DIM_V2 = ACTION_DIM + CARD_DIM + AGG


# Version 3 appends the hand decomposition (rl/plan.py): on the state, the fewest sets the hand splits into (unary);
# on each action, that number after the move (unary) and how the move changes it (<= -1, 0, +1, >= +2).
PLAN_CAP = 14
STATE_DIM_V3 = STATE_DIM_V2 + PLAN_CAP
ACTION_DIM_V3 = ACTION_DIM_V2 + PLAN_CAP + 4


# Version 4 appends, for each of the three other players, counts of what they have done so far in this deal (unary,
# capped): plays, passes, bombs, leads, plays over their own partner, passes that declined to contest an opponent's play.
# They let the network tell a bomb-happy or passive opponent from a normal one. Mirrors rust/src/features.rs.
STYLE_CAPS = (12, 10, 3, 8, 3, 8)
STYLE_DIM = 3 * sum(STYLE_CAPS)
STATE_DIM_V4 = STATE_DIM_V3 + STYLE_DIM


def behaviour(history, seat: int, out: np.ndarray) -> None:
    stats = [[0] * 6 for _ in range(4)]
    for i, (s, m) in enumerate(history):
        last = None                                  # who last played (not passed) among the three moves before this one
        for j in range(i - 1, max(-1, i - 4), -1):
            if not history[j][1].is_pass:
                last = history[j][0]
                break
        if m.is_pass:
            stats[s][1] += 1
            if last is not None and last % 2 != s % 2:
                stats[s][5] += 1
        else:
            stats[s][0] += 1
            if m.combo.is_bomb:
                stats[s][2] += 1
            if last is None:
                stats[s][3] += 1
            elif last % 2 == s % 2:
                stats[s][4] += 1
    o = 0
    for k in range(3):
        for v, cap in zip(stats[(seat + 1 + k) % 4], STYLE_CAPS):
            out[o:o + min(v, cap)] = 1
            o += cap


# Version 5: how good the hand is for finishing, on the state and (for the hand left) after each move: high cards (ace and
# above, jokers, wilds), low singles and low pairs (value <= 8), bombs. Unary, capped. Mirrors rust/src/features.rs.
CTRL_CAPS = (8, 6, 6, 4)
CTRL_DIM = sum(CTRL_CAPS)
STATE_DIM_V5 = STATE_DIM_V4 + CTRL_DIM
ACTION_DIM_V5 = ACTION_DIM_V3 + CTRL_DIM


def control_features(cards, level: int, out: np.ndarray) -> None:
    wt = wild_type(level)
    nr, sj, bj, wild = [0] * 13, 0, 0, 0
    for c in cards:
        t = ctype(c)
        if t == wt:
            wild += 1
        elif t == SJ:
            sj += 1
        elif t == BJ:
            bj += 1
        else:
            nr[t % 13] += 1
    val = lambda r: 13 if r == level else r
    high = sum(nr[r] for r in range(13) if val(r) >= 12) + sj + bj + wild
    low_singles = sum(1 for r in range(13) if nr[r] == 1 and val(r) <= 8)
    low_pairs = sum(1 for r in range(13) if nr[r] == 2 and val(r) <= 8)
    bombs = sum(1 for r in range(13) if nr[r] >= 4) + int(sj == 2 and bj == 2)
    o = 0
    for v, cap in zip((high, low_singles, low_pairs, bombs), CTRL_CAPS):
        out[o:o + min(v, cap)] = 1
        o += cap


def state_dim(version: int = 1) -> int:
    return STATE_DIM_V5 if version >= 5 else STATE_DIM_V4 if version >= 4 else STATE_DIM_V3 if version >= 3 else STATE_DIM_V2 if version >= 2 else STATE_DIM


def action_dim(version: int = 1) -> int:
    return ACTION_DIM_V5 if version >= 5 else ACTION_DIM_V3 if version >= 3 else ACTION_DIM_V2 if version >= 2 else ACTION_DIM


def card_vec(cards, out: np.ndarray | None = None) -> np.ndarray:
    v = np.zeros(CARD_DIM, np.uint8) if out is None else out
    for c in cards:
        t = 2 * ctype(c)
        v[t + 1 if v[t] else t] = 1
    return v


def encode_state(obs: dict, version: int = 1) -> np.ndarray:
    seat = obs["seat"]
    rel = [(seat + k) % 4 for k in (1, 2, 3)]
    slots = HISTORY_V2 if version >= 2 else HISTORY
    x = np.zeros(state_dim(version), np.uint8)
    o = 0

    def cards(cs):
        nonlocal o
        card_vec(cs, x[o:o + CARD_DIM])
        o += CARD_DIM

    def onehot(i, n):
        nonlocal o
        if i is not None:
            x[o + i] = 1
        o += n

    hand = obs["hand"]
    cards(hand)
    seen = np.zeros(CARD_DIM, np.uint8)
    card_vec(list(hand) + [c for p in obs["played"] for c in p], seen)
    x[o:o + CARD_DIM] = 1 - seen
    o += CARD_DIM
    for s in rel:
        cards(obs["played"][s])
    for s in rel:
        onehot(min(obs["counts"][s], 27), 28)
    table = obs["table"]
    cards(table.cards if table else ())
    onehot(0 if table is None else (obs["table_seat"] - seat) % 4, 4)
    onehot(int(table.combo.kind) if table else 0, N_KINDS)
    mine, theirs = obs["team_levels"][seat % 2], obs["team_levels"][1 - seat % 2]
    onehot(obs["level"], 13)
    onehot(mine, 13)
    onehot(theirs, 13)
    lt = obs["level_team"]
    onehot(2 if lt is None else int(lt != seat % 2), 3)
    for s in rel:
        onehot(0 if s in obs["finished"] else None, 1)
    onehot(0 if obs["leading"] else None, 1)
    hist = obs["history"][-slots:]
    for k in range(slots):
        if k < len(hist):
            s, m = hist[-1 - k]
            cards(m.cards)
            onehot((s - seat) % 4, 4)
        else:
            o += CARD_DIM + 4
    if version >= 3:
        x[STATE_DIM_V2:STATE_DIM_V2 + min(PLAN_CAP, min_sets_now(hand, obs["level"]))] = 1
        o += PLAN_CAP
    if version >= 4:
        behaviour(obs["history"], seat, x[STATE_DIM_V3:STATE_DIM_V4])
        o += STYLE_DIM
    if version >= 5:
        control_features(hand, obs["level"], x[STATE_DIM_V4:STATE_DIM_V5])
        o += CTRL_DIM
    assert o == state_dim(version)
    return x


def _remaining(m: Move, hand, level: int, out: np.ndarray) -> None:
    """Version-2 columns: the hand left after `m`, then unary-coded counts."""
    rem = list(hand)
    for c in m.cards:
        rem.remove(c)
    card_vec(rem, out[:CARD_DIM])
    wt = wild_type(level)
    nr, sj, bj, wild = [0] * 13, 0, 0, 0
    for c in rem:
        t = ctype(c)
        if t == wt:
            wild += 1
        elif t == SJ:
            sj += 1
        elif t == BJ:
            bj += 1
        else:
            nr[t % 13] += 1

    def run(k: int) -> int:
        best = cur = 0
        for r in SEQ:
            cur = cur + 1 if nr[r] >= k else 0
            best = max(best, cur)
        return best

    at = CARD_DIM
    for v, cap in ((len(rem), 27), (sum(1 for x in nr if x == 1), 6), (sum(1 for x in nr if x == 2), 6),
                   (sum(1 for x in nr if x == 3), 6), (sum(1 for x in nr if x >= 4), 6), (sj + bj, 4), (wild, 2),
                   (run(1), 14), (run(2), 14), (run(3), 14)):
        out[at:at + min(v, cap)] = 1
        at += cap
    assert at == CARD_DIM + AGG


def min_sets_now(hand, level: int) -> int:
    return Planner().min_sets(St.from_cards(hand, level))


def encode_action(m: Move, hand_size: int, level: int, version: int = 1, hand=None, plan=None) -> np.ndarray:
    """`plan` = (planner, state of the hand now, sets now) shared by all the moves of one decision (version 3)."""
    x = np.zeros(action_dim(version), np.uint8)
    card_vec(m.cards, x[:CARD_DIM])
    o = CARD_DIM
    x[o + int(m.combo.kind)] = 1
    o += N_KINDS
    x[o + min(2, sum(1 for c in m.cards if is_wild(c, level)))] = 1
    o += 3
    x[o] = len(m.cards) == hand_size
    o += 1
    x[o + min(15, m.combo.value)] = 1
    if version >= 2:
        _remaining(m, hand, level, x[ACTION_DIM:])
    if version >= 3:
        planner, st, now = plan
        after = planner.min_sets(st.minus(m.cards, level))
        x[ACTION_DIM_V2:ACTION_DIM_V2 + min(PLAN_CAP, after)] = 1
        x[ACTION_DIM_V2 + PLAN_CAP + (0 if after - now <= -1 else 1 if after == now else 2 if after - now == 1 else 3)] = 1
    if version >= 5:
        rem = list(hand)
        for c in m.cards:
            rem.remove(c)
        control_features(rem, level, x[ACTION_DIM_V3:ACTION_DIM_V5])
    return x


def encode_actions(obs: dict, version: int = 1) -> np.ndarray:
    hand, level = obs["hand"], obs["level"]
    plan = None
    if version >= 3:
        planner, st = Planner(), St.from_cards(hand, level)
        plan = (planner, st, planner.min_sets(st))
    return np.stack([encode_action(m, len(hand), level, version, hand, plan) for m in obs["legal"]])
