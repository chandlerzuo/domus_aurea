import numpy as np

from guandan.rl.scenarios import runout_position


def test_runout_positions_are_consistent():
    rng = np.random.default_rng(0)
    for _ in range(60):
        d, h, scripted = runout_position(rng)
        cards = [c for hand in d.hands for c in hand] + [c for p in d.played for c in p]
        assert sorted(cards) == list(range(108))                      # every card is somewhere exactly once
        plan = scripted[h].plan
        assert sorted(c for combo in plan for c in combo) == sorted(d.hands[h])   # the runout seat holds exactly its plan
        assert 2 <= len(plan) <= 3 and len(d.hands[h]) <= 12


def test_runout_player_leads_its_combos_in_a_row_when_unopposed():
    rng = np.random.default_rng(1)
    for _ in range(20):
        d, h, scripted = runout_position(rng)
        d.to_act = h
        agent = scripted[h]
        n_combos = len(agent.plan)
        plays = 0
        while d.hands[h]:
            obs = d.observation(h)
            d.play(obs["legal"][agent.act(obs)])
            plays += 1
            while not d.done and d.to_act != h:      # everyone else passes
                o = d.observation(d.to_act)
                d.play(o["legal"][0] if not o["leading"] else o["legal"][0])
        assert plays == n_combos or d.done


def test_best_split_uses_every_card_once_with_the_fewest_sets():
    from guandan.rl.plan import best_split, min_sets
    rng = np.random.default_rng(0)
    for _ in range(80):
        level = int(rng.integers(13))
        hand = [int(c) for c in rng.permutation(108)[:int(rng.integers(3, 28))]]
        groups = best_split(hand, level)
        assert sorted(c for g in groups for c in g) == sorted(hand)
        assert len(groups) == min_sets(hand, level)
