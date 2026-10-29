import numpy as np
import pytest

from guandan.agents import HeuristicAgent, RandomAgent
from guandan.cards import BJ, SJ, parse
from guandan.combos import PASS, Combo, Kind, classify, interpret, legal_moves
from guandan.evaluate import duplicate
from guandan.game import Deal, Match, deal_cards, return_options, tribute_card


def kinds(s, level=0):
    return {(c.kind, c.value) for c in classify(parse(s), level)}


def test_basic_combos():
    assert kinds("3s") == {(Kind.SINGLE, 1)}
    assert kinds("3s 3d") == {(Kind.PAIR, 1)}
    assert kinds("sj sj") == {(Kind.PAIR, 14)}
    assert kinds("sj BJ") == set()
    assert kinds("3s 3d 3c 9h 9s") == {(Kind.FULL_HOUSE, 1)}
    assert kinds("3s 3d 3c BJ BJ") == {(Kind.FULL_HOUSE, 1)}
    assert kinds("3s 3d 4c 4h 5s 5s") == {(Kind.TUBE, 2)}
    assert kinds("3s 3d 3c 4h 4s 4d") == {(Kind.PLATE, 2)}
    assert kinds("sj sj BJ BJ") == {(Kind.JOKER_BOMB, 0)}
    assert kinds("3s 4s 5s 6s 8s") == set()


def test_ace_low_and_high_straights():
    assert kinds("As 2d 3c 4h 5s", level=5) == {(Kind.STRAIGHT, 0)}
    assert kinds("Ts Jd Qc Kh As", level=5) == {(Kind.STRAIGHT, 9)}
    assert kinds("Qs Kd Ac 2h 3s", level=5) == set()  # no wrap-around
    assert kinds("Ts Js Qs Ks As", level=5) == {(Kind.STRAIGHT, 9), (Kind.STRAIGHT_FLUSH, 9)}


def test_level_rank_and_wilds():
    # Level 7 (rank index 5): 7s ranks above an ace as a single; 7h is wild.
    assert kinds("7s", level=5) == {(Kind.SINGLE, 13)}
    assert kinds("As", level=5) == {(Kind.SINGLE, 12)}
    assert kinds("9s 9d 7h", level=5) == {(Kind.TRIPLE, 7)}
    assert (Kind.STRAIGHT, 2) in kinds("3s 4d 7h 6c 7s", level=5)       # wild fills the 5
    assert kinds("7h 7h", level=5) == {(Kind.PAIR, 13)}
    assert kinds("sj 7h", level=5) == set()                             # wilds never stand in for jokers
    assert (Kind.BOMB, 7) in kinds("9s 9d 9c 7h 7h", level=5)


def test_bomb_order():
    four = Combo(Kind.BOMB, 1, 4)
    five = Combo(Kind.BOMB, 0, 5)
    sf = Combo(Kind.STRAIGHT_FLUSH, 9, 5)
    six = Combo(Kind.BOMB, 0, 6)
    jokers = Combo(Kind.JOKER_BOMB, 0, 4)
    chain = [Combo(Kind.SINGLE, 15, 1), four, five, sf, six, Combo(Kind.BOMB, 12, 10), jokers]
    for lo, hi in zip(chain, chain[1:]):
        assert hi.beats(lo) and not lo.beats(hi)
    assert not Combo(Kind.PAIR, 5, 2).beats(Combo(Kind.SINGLE, 1, 1))
    assert not Combo(Kind.SINGLE, 1, 1).beats(Combo(Kind.SINGLE, 1, 1))


def test_interpret_prefers_matching_kind():
    cards = parse("3s 3d 3c 2h 2h")  # level 2: full house or 5-bomb of threes
    assert interpret(cards, 0, Combo(Kind.FULL_HOUSE, 0, 5)).kind == Kind.FULL_HOUSE
    assert interpret(cards, 0, Combo(Kind.FULL_HOUSE, 5, 5)).kind == Kind.BOMB
    assert interpret(cards, 0, None).kind == Kind.BOMB


@pytest.mark.parametrize("seed", range(40))
def test_legal_moves_are_valid(seed):
    rng = np.random.default_rng(seed)
    level = int(rng.integers(13))
    hand = deal_cards(rng)[0]
    leads = legal_moves(hand, level, None)
    assert leads and all(not m.is_pass for m in leads)
    for table in [None] + [m.combo for m in leads[:: max(1, len(leads) // 15)]]:
        for m in legal_moves(hand, level, table):
            assert set(m.cards) <= set(hand) and len(set(m.cards)) == len(m.cards) == m.combo.size
            assert m.combo in classify(list(m.cards), level)
            assert m.combo.beats(table)


def test_legal_moves_complete_for_small_hands():
    # Every combo classify() finds in a subset must also be generated (at rank level).
    rng = np.random.default_rng(7)
    for _ in range(30):
        level = int(rng.integers(13))
        hand = [int(c) for c in rng.choice(108, 9, replace=False)]
        gen = {m.combo for m in legal_moves(hand, level, None)}
        for mask in range(1, 1 << len(hand)):
            sub = [hand[i] for i in range(len(hand)) if mask >> i & 1]
            if len(sub) <= 6:
                for combo in classify(sub, level):
                    assert combo in gen, (sub, combo)


def test_jie_feng_partner_leads_after_going_out():
    # Seat 0 goes out with its last card; everyone passes; partner (seat 2) leads.
    hands = [parse("As"), parse("3s 4s"), parse("5d 6d"), parse("7c 8c")]
    d = Deal(hands, level=0, leader=0)
    d.play(legal_moves(d.hands[0], 0, None)[0])
    assert d.finished == [0] and d.to_act == 1
    d.play(PASS)
    d.play(PASS)
    d.play(PASS)
    assert d.leading and d.to_act == 2


def test_deal_result_and_levels():
    hands = [parse("As"), parse("3s 4s"), parse("Ad"), parse("7c 8c")]
    d = Deal(hands, level=0, leader=0)
    d.play(legal_moves(d.hands[0], 0, None)[0])
    for _ in range(3):
        d.play(PASS)
    d.play(legal_moves(d.hands[2], 0, None)[0])
    assert d.done and d.finished[:2] == [0, 2] and d.result() == (0, 3)


def test_tribute_and_return():
    m = Match(seed=1, team_levels=[3, 0], level_team=0, last_order=[0, 1, 2, 3])
    hands = deal_cards(np.random.default_rng(3))
    expect = tribute_card(hands[3], 3)
    if sum(1 for c in hands[3] if c % 54 == BJ) == 2:
        pytest.skip("resisted")
    d = m.new_deal(hands)
    (t,) = m.tributes
    assert (t.payer, t.receiver, t.card) == (3, 0, expect) and d.to_act == 3
    assert len(d.hands[0]) == 28 and len(d.hands[3]) == 26
    card = return_options(d.hands[0])[0]
    m.give_return(0, card)
    assert card in d.hands[3] and all(len(h) == 27 for h in d.hands)


def test_double_tribute_resisted_with_both_big_jokers():
    hands = deal_cards(np.random.default_rng(0))
    # Move both big jokers into seats 1 and 3 (the losing team).
    bjs = [c for h in hands for c in h if c % 54 == BJ]
    for h in hands:
        for c in bjs:
            if c in h:
                h.remove(c)
    hands[1].append(bjs[0])
    hands[3].append(bjs[1])
    hands[0].append(hands[1].pop(0))
    hands[2].append(hands[3].pop(0))
    m = Match(seed=0, team_levels=[0, 0], level_team=0, last_order=[0, 2, 1, 3])
    d = m.new_deal(hands)
    assert m.resisted and not m.tributes and d.to_act == 0


def test_match_ends_at_ace():
    m = Match(seed=0, team_levels=[12, 4], level_team=0)
    d = m.new_deal()
    d.finished, d.done = [0, 2, 1, 3], True
    m.finish_deal()
    assert m.over and m.winner == 0


def test_tribute_never_wild():
    hand = parse("7h 7h 3s 4d") + [SJ]
    assert tribute_card(hand, 5) == SJ
    assert tribute_card(parse("7h 3s 4d"), 5) == parse("4d")[0]


def test_full_matches_with_agents():
    for kind in (RandomAgent, HeuristicAgent):
        agents = [kind(seed=s) for s in range(4)]
        m = Match(seed=5)
        while not m.over and m.deals_played < 100:
            d = m.new_deal()
            for t in m.pending_returns:
                m.give_return(t.receiver, agents[t.receiver].choose_return(d.hands[t.receiver], d.level))
            while not d.done:
                obs = d.observation(d.to_act)
                d.play(obs["legal"][agents[d.to_act].act(obs)])
            m.finish_deal()
        assert m.over


def test_heuristic_beats_random():
    r = duplicate(HeuristicAgent, RandomAgent, pairs=30)
    assert r["points_per_deal"] > 1.5
