"""The exact endgame solver agrees with plain minimax (no pruning, no table) on small positions."""
import numpy as np
import pytest

core = pytest.importorskip("guandan_core")


def minimax(d, me):
    if d.done:
        win, up = d.result()
        return up if win == me else -up
    vals = []
    for i in range(d.n_legal()):
        c = d.copy()
        c.play_index(i)
        vals.append(minimax(c, me))
    return max(vals) if d.to_act % 2 == me else min(vals)


def random_deal(rng, per_hand):
    cards = [int(c) for c in rng.permutation(108)[:4 * per_hand]]
    hands = [sorted(cards[i * per_hand:(i + 1) * per_hand]) for i in range(4)]
    return core.RsDeal(hands, int(rng.integers(13)), int(rng.integers(4)))


@pytest.mark.parametrize("per_hand", [1, 2, 3])
def test_solver_matches_minimax(per_hand):
    rng = np.random.default_rng(per_hand)
    for _ in range(15):
        d = random_deal(rng, per_hand)
        me = d.to_act % 2
        brute = []
        for i in range(d.n_legal()):
            c = d.copy()
            c.play_index(i)
            brute.append(minimax(c, me))
        assert d.solve() == brute


def test_solver_gives_up_when_over_budget():
    d = random_deal(np.random.default_rng(0), 4)
    assert d.solve(budget=3) is None
