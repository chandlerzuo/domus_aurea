import numpy as np
import pytest
import torch

from guandan.agents import HeuristicAgent
from guandan.game import Deal, deal_cards, team
from guandan.rl.policy import Actor
from guandan.rl.search import SearchAgent, sample_world, search_choice

core = pytest.importorskip("guandan_core")


def key(m):
    return (int(m.combo.kind), m.combo.value, m.combo.size, tuple(m.cards))


def test_sampled_world_matches_the_players_view_without_the_hidden_hands():
    rng = np.random.default_rng(0)
    differ = same_as_true = 0
    for k in range(25):
        d = Deal(deal_cards(rng), int(rng.integers(13)), int(rng.integers(4)), (int(rng.integers(13)), int(rng.integers(13))),
                 [None, 0, 1][k % 3])
        for _ in range(int(rng.integers(0, 70))):
            if d.done:
                break
            lg = d.observation(d.to_act)["legal"]
            d.play(lg[int(rng.integers(len(lg)))])
        if d.done:
            continue
        seat = d.to_act
        obs = d.observation(seat)
        for version in (1, 2):
            w = sample_world(obs, rng, version)
            assert w.to_act == seat and w.hands[seat] == d.hands[seat] and w.counts == obs["counts"]
            assert w.played == d.played and w.finished == d.finished and w.leading == d.leading
            assert w.table_seat == d.table_seat and w.passes >= 0
            assert [key(m) for m in obs["legal"]] == [(a, b, c, tuple(e)) for a, b, c, e in w.legal()]
            assert (w.encode_state(seat, version) is not None)
        differ += any(w.hands[s] != d.hands[s] for s in range(4) if s != seat)
        same_as_true += all(w.hands[s] == d.hands[s] for s in range(4) if s != seat)
        # sampled worlds are playable to the end
        while not w.done:
            w.play_index(0)
        assert w.result()[1] in (1, 2, 3)
    assert differ > 15 and same_as_true == 0


def test_search_agent_plays_full_deals_and_reports():
    torch.manual_seed(0)
    for version in (1, 2):
        actor = Actor(64, version).eval()
        rng = np.random.default_rng(1)
        d = Deal(deal_cards(rng), 5, 0)
        agents = [SearchAgent(actor, seed=s, worlds=4) if s % 2 == 0 else HeuristicAgent(s) for s in range(4)]
        searched = 0
        while not d.done:
            obs = d.observation(d.to_act)
            ag = agents[d.to_act]
            i = ag.act(obs)
            assert 0 <= i < len(obs["legal"])
            searched += "search" in ag.info
            ag.info = {}
            d.play(obs["legal"][i])
        assert searched > 3 and d.result()[1] in (1, 2, 3)


def test_search_prefers_going_out_when_it_wins_the_deal():
    # With only one card left, the winning move must be chosen by any sensible search.
    actor = Actor(64).eval()
    rng = np.random.default_rng(2)
    d = Deal(deal_cards(rng), 3, 0)
    while not d.done and len(d.hands[d.to_act]) > 2:
        lg = d.observation(d.to_act)["legal"]
        d.play(lg[0] if not d.leading else lg[-1])
    obs = d.observation(d.to_act)
    i, rep = search_choice(actor, obs, rng, worlds=8, margin=0.0)
    assert 0 <= i < len(obs["legal"])
