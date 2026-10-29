import numpy as np
import torch

from guandan.game import Deal, deal_cards
from guandan.rl import ppo
from guandan.rl.features import STATE_DIM
from guandan.rl.policy import ORACLE_DIM, Actor, Critic, PolicyAgent, encode_oracle, load_policy, padded_log_probs, save_policy
from guandan.rl.ppo import Batch, PPOConfig, bc_update, play_task, ppo_update


def test_padded_log_probs_is_softmax_per_state():
    logits = torch.tensor([1.0, 2.0, 0.5, -1.0, 3.0])
    seg = torch.tensor([0, 0, 1, 1, 1])
    pos = torch.tensor([0, 1, 0, 1, 2])
    lp = padded_log_probs(logits, seg, pos, 2, 3)
    assert torch.allclose(lp[0, :2], torch.log_softmax(logits[:2], 0))
    assert torch.allclose(lp[1], torch.log_softmax(logits[2:], 0))
    assert lp[0, 2].exp() == 0


def test_oracle_is_hidden_hands():
    hands = deal_cards(np.random.default_rng(0))
    o = encode_oracle(hands, 1)
    assert o.shape == (ORACLE_DIM,) and o.sum() == 81


def _tasks(tmp_path, mode, opponent=("self", "")):
    path = tmp_path / "latest.pt"
    save_policy(Actor(64), Critic(64), path)
    ppo._worker_init(PPOConfig(hidden=64))
    return play_task(3, 2, mode, (str(path), 0), opponent)


def test_play_task_shapes_and_minibatch_rows(tmp_path):
    for mode, opp in (("bc", ("self", "")), ("ppo", ("self", "")), ("ppo", ("heuristic", ""))):
        r = _tasks(tmp_path, mode, opp)
        assert r["n"].sum() == len(r["A"]) and np.all(r["chosen"] < r["n"]) and np.all(r["n"] > 1)
        assert r["S"].shape[1] == STATE_DIM and r["O"].shape[1] == ORACLE_DIM
    b = Batch([r])
    idx = np.array([len(b) - 1, 0, 2])
    mb = b.minibatch(idx, torch.device("cpu"))
    for j, i in enumerate(idx):
        rows = mb["a"][mb["seg"] == j]
        assert len(rows) == b.n[i]
        assert torch.equal(rows, torch.from_numpy(b.A[b.off[i]:b.off[i] + b.n[i]]).float())


def test_bc_learns_and_ppo_runs(tmp_path):
    r = _tasks(tmp_path, "bc")
    b = Batch([r])
    actor, critic = Actor(64), Critic(64)
    cfg = PPOConfig(hidden=64, minibatch=256)
    opt = torch.optim.Adam([*actor.parameters(), *critic.parameters()], lr=1e-3)
    rng = np.random.default_rng(0)
    first = bc_update(actor, critic, opt, b, cfg, rng, torch.device("cpu"))
    for _ in range(15):
        last = bc_update(actor, critic, opt, b, cfg, rng, torch.device("cpu"))
    assert last["ce"] < first["ce"] and last["acc"] > first["acc"]
    stats = ppo_update(actor, critic, opt, Batch([_tasks(tmp_path, "ppo")]), cfg, rng, torch.device("cpu"))
    assert all(np.isfinite(v) for v in stats.values())
    save_policy(actor, critic, tmp_path / "m.pt")
    agent = PolicyAgent(load_policy(tmp_path / "m.pt"), seed=0)
    d = Deal(deal_cards(np.random.default_rng(1)), level=0, leader=0)
    while not d.done:
        obs = d.observation(d.to_act)
        d.play(obs["legal"][agent.act(obs)])
