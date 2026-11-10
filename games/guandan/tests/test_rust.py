"""The Rust core must behave exactly like the Python rules engine and feature encoders."""
import numpy as np
import pytest

from guandan.cards import N_CARDS
from guandan.combos import Combo, Kind, legal_moves_py, move_from_tuple
from guandan.game import Deal, deal_cards
from guandan.rl.features import ACTION_DIM, STATE_DIM, encode_actions, encode_state
from guandan.rl.policy import ORACLE_DIM, encode_oracle

core = pytest.importorskip("guandan_core")


def mv_key(m):
    return (int(m.combo.kind), m.combo.value, m.combo.size, tuple(m.cards))


def test_dimensions_match():
    assert (core.STATE_DIM, core.ACTION_DIM, core.ORACLE_DIM) == (STATE_DIM, ACTION_DIM, ORACLE_DIM)


def test_legal_moves_identical_to_python():
    rng = np.random.default_rng(0)
    checked = 0
    for _ in range(600):
        level = int(rng.integers(13))
        n = int(rng.integers(1, 28))
        hand = sorted((int(c) for c in rng.permutation(N_CARDS)[:n]), key=lambda c: (c % 54 % 13, c))
        rng.shuffle(hand)  # hand order drives which concrete cards get picked
        tables = [None] + [m.combo for m in legal_moves_py(hand, level, None)[:: max(1, n // 4)]]
        tables += [Combo(Kind.SINGLE, int(rng.integers(16)), 1), Combo(Kind.PAIR, int(rng.integers(16)), 2),
                   Combo(Kind.BOMB, int(rng.integers(13)), 4), Combo(Kind.STRAIGHT_FLUSH, int(rng.integers(10)), 5)]
        for table in tables:
            py = [mv_key(m) for m in legal_moves_py(hand, level, table)]
            t = None if table is None else (int(table.kind), table.value, table.size)
            rs = [(k, v, s, tuple(c)) for k, v, s, c in core.legal_moves_py(hand, level, t)]
            assert rs == py, (hand, level, table)
            checked += 1
    assert checked > 3000


def test_deals_play_identically():
    rng = np.random.default_rng(1)
    steps = 0
    for k in range(60):
        hands = deal_cards(rng)
        level, leader = int(rng.integers(13)), int(rng.integers(4))
        tl = (int(rng.integers(13)), int(rng.integers(13)))
        lt = [None, 0, 1][k % 3]
        py = Deal(hands, level, leader, tl, lt)
        rs = core.RsDeal(hands, level, leader, tl, lt)
        while not py.done:
            seat = py.to_act
            assert rs.to_act == seat and not rs.done
            obs = py.observation(seat)
            legal = obs["legal"]
            assert [mv_key(m) for m in legal] == [(k_, v, s, tuple(c)) for k_, v, s, c in rs.legal()]
            assert (rs.encode_state(seat) == encode_state(obs)).all()
            assert (rs.encode_actions() == encode_actions(obs)).all()
            assert (rs.encode_oracle(seat) == encode_oracle(py.hands, seat)).all()
            assert rs.hands == py.hands and rs.counts == obs["counts"] and rs.played == py.played
            assert rs.finished == py.finished and rs.leading == py.leading and rs.table_seat == py.table_seat
            i = int(rng.integers(len(legal))) if k % 2 else int(np.argmax([len(m.cards) for m in legal]))
            py.play(legal[i])
            rs.play_index(i)
            steps += 1
        assert rs.done and rs.result() == py.result() and rs.finished == py.finished
        assert [(s, mv_key(m)) for s, m in py.history] == [(s, (k_, v, sz, tuple(c))) for s, (k_, v, sz, c) in rs.history]
    assert steps > 3000


def test_batch_functions_and_resample():
    rng = np.random.default_rng(2)
    deals = [core.RsDeal(deal_cards(rng), int(rng.integers(13)), int(rng.integers(4))) for _ in range(8)]
    for _ in range(20):
        S, A, n = core.batch_encode(deals)
        assert S.shape == (8, STATE_DIM) and A.shape == (int(n.sum()), ACTION_DIM)
        O = core.batch_oracle(deals)
        assert O.shape == (8, ORACLE_DIM)
        for k, d in enumerate(deals):
            assert (S[k] == d.encode_state(d.to_act)).all() and n[k] == d.n_legal()
        core.batch_play(deals, [int(rng.integers(x)) for x in n])
        deals = [d for d in deals if not d.done]
        if not deals:
            break
    d = core.RsDeal(deal_cards(rng), 3, 0)
    for _ in range(10):
        d.play_index(int(rng.integers(d.n_legal())))
    seat = d.to_act
    w = d.resample(seat, 7)
    assert w.hands[seat] == d.hands[seat] and w.counts == d.counts and w.played == d.played
    assert sorted(c for h in w.hands for c in h) == sorted(c for h in d.hands for c in h)
    assert w.hands != d.hands
    assert w.hands == d.resample(seat, 7).hands != d.resample(seat, 8).hands  # deterministic per seed
    w.play_index(0)  # a sampled world is a playable deal


def test_feature_version_2_matches_python_and_extends_version_1():
    from guandan.rl.features import ACTION_DIM_V2, STATE_DIM_V2
    assert (core.STATE_DIM_V2, core.ACTION_DIM_V2) == (STATE_DIM_V2, ACTION_DIM_V2)
    rng = np.random.default_rng(3)
    steps = 0
    for k in range(40):
        hands = deal_cards(rng)
        level, leader = int(rng.integers(13)), int(rng.integers(4))
        py = Deal(hands, level, leader)
        rs = core.RsDeal(hands, level, leader)
        while not py.done:
            seat = py.to_act
            obs = py.observation(seat)
            s2, a2 = encode_state(obs, 2), encode_actions(obs, 2)
            assert s2.shape == (STATE_DIM_V2,) and a2.shape[1] == ACTION_DIM_V2
            assert (rs.encode_state(seat, 2) == s2).all() and (rs.encode_actions(2) == a2).all()
            # version 2 only appends columns to version 1
            assert (s2[:STATE_DIM] == encode_state(obs)).all() and (a2[:, :ACTION_DIM] == encode_actions(obs)).all()
            assert set(np.unique(s2)) <= {0, 1} and set(np.unique(a2)) <= {0, 1}
            S, A, n = core.batch_encode([rs], 2)
            assert (S[0] == s2).all() and (A == a2).all() and n[0] == len(obs["legal"])
            i = int(rng.integers(len(obs["legal"])))
            py.play(obs["legal"][i])
            rs.play_index(i)
            steps += 1
    assert steps > 1500


def test_joker_bombs_and_wild_straight_flushes_match_python():
    # rare combos the random hands above seldom contain
    from guandan.cards import parse
    cases = [("sj sj BJ BJ 3s 3h 4c", 5), ("sj sj BJ BJ 3s 3s 3c", 3), ("5h 3s 4s 6s 7s", 3), ("5h 3s 4s 6s 7s 5s 8s 9s", 6),
             ("3s 3h 3c 3d 3s 3h 3c 3d 7h 7h", 7), ("As 2s 3s 4s", 5), ("As 2s 3s 4s 5h", 3)]
    for text, level in cases:
        hand = parse(text)
        for table in (None, Combo(Kind.BOMB, 5, 4), Combo(Kind.STRAIGHT_FLUSH, 2, 5), Combo(Kind.PAIR, 3, 2)):
            t = None if table is None else (int(table.kind), table.value, table.size)
            py = [(int(m.combo.kind), m.combo.value, m.combo.size, tuple(m.cards)) for m in legal_moves_py(hand, level, table)]
            assert [(k, v, s, tuple(c)) for k, v, s, c in core.legal_moves_py(hand, level, t)] == py, (text, table)
