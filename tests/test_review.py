import json

import numpy as np

from guandan.agents import HeuristicAgent
from guandan.game import Deal, deal_cards
from guandan.review import lead_flags, record_move, review_deal
from guandan.rl.policy import Actor


def recorded_deal(seed=0):
    hands = deal_cards(np.random.default_rng(seed))
    d = Deal(hands, level=3, leader=0)
    rec = {"hands": [list(h) for h in d.hands], "level": 3, "leader": 0, "team_levels": [0, 0],
           "level_team": None, "moves": []}
    agents = [HeuristicAgent(s) for s in range(4)]
    while not d.done:
        obs = d.observation(d.to_act)
        m = obs["legal"][agents[d.to_act].act(obs)]
        rec["moves"].append(record_move(d.to_act, m))
        d.play(m)
    return rec, d.result()


def test_review_replays_and_scores_decisions():
    rec, (win, up) = recorded_deal()
    flags = lead_flags(rec)
    assert flags[0] and len(flags) == len(rec["moves"])
    r = review_deal(rec, Actor(64).eval(), seat=0, rollouts=2, max_flagged=2)
    assert r["result"] == (up if win == 0 else -up)
    assert r["decisions"] and all(0 <= x["p_played"] <= 1 for x in r["decisions"])
    assert all(x["step"] < len(rec["moves"]) and rec["moves"][x["step"]][0] == 0 for x in r["decisions"])
    measured = [x for x in r["decisions"] if "impact" in x]
    assert len(measured) <= 2 and all(x["flag"] for x in measured)
    assert json.loads(json.dumps(r)) == r  # stored as JSON
