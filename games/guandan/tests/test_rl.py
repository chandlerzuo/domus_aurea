import numpy as np
import torch

from guandan.game import Deal, deal_cards
from guandan.rl import dmc
from guandan.rl.dmc import DMCAgent, DMCConfig, QNet, load_net, play_task, save_net
from guandan.rl.features import ACTION_DIM, STATE_DIM, encode_actions, encode_state


def test_feature_shapes_and_binary():
    d = Deal(deal_cards(np.random.default_rng(0)), level=4, leader=0)
    obs = d.observation(0)
    s, a = encode_state(obs), encode_actions(obs)
    assert s.shape == (STATE_DIM,) and a.shape == (len(obs["legal"]), ACTION_DIM)
    assert set(np.unique(s)) <= {0, 1} and set(np.unique(a)) <= {0, 1}
    assert s[:108].sum() == 27  # own hand


def test_q_values_match_batched_forward():
    net = QNet(64).eval()
    s = torch.rand(STATE_DIM)
    a = torch.rand(5, ACTION_DIM)
    assert torch.allclose(net.q_values(s, a), net(s.expand(5, -1), a), atol=1e-5)


def test_play_task_and_checkpoint_roundtrip(tmp_path):
    net = QNet(64)
    path = tmp_path / "latest.pt"
    save_net(net, path)
    assert torch.allclose(next(load_net(path).parameters()), next(net.parameters()))
    dmc._worker_init(DMCConfig(hidden=64))
    for opp in (("self", "", 0), ("heuristic", "", 0), ("snapshot", str(path), 0)):
        r = play_task(1, 2, (str(path), 0), opp)
        assert len(r["S"]) == len(r["A"]) == len(r["G"]) > 0 and len(r["scores"]) == 2
        assert np.all(np.abs(r["G"]) <= 1.0)


def test_dmc_agent_picks_legal_index():
    agent = DMCAgent(QNet(64).eval(), seed=0)
    d = Deal(deal_cards(np.random.default_rng(1)), level=0, leader=0)
    while not d.done:
        obs = d.observation(d.to_act)
        i = agent.act(obs)
        assert 0 <= i < len(obs["legal"])
        d.play(obs["legal"][i])
