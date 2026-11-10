import numpy as np
import pytest
import torch

from guandan.rl.distill import DistillConfig, LabelBatch, distill, fit, label_task
from guandan.rl import distill as dm
from guandan.rl.policy import Actor, Critic, save_policy
from guandan.rl.search import improved_policy

pytest.importorskip("guandan_core")


def test_improved_policy_moves_mass_toward_better_candidates_only():
    p = np.array([0.5, 0.3, 0.1, 0.06, 0.04])
    t = improved_policy(p, [0, 1, 2], np.array([0.0, 1.0, -1.0]), tau=0.5)
    assert abs(t.sum() - 1) < 1e-9 and np.allclose(t[3:], p[3:])           # others untouched
    assert abs(t[:3].sum() - p[:3].sum()) < 1e-9                            # candidates keep their total
    assert t[1] > p[1] and t[2] < p[2] and t[0] < p[0]                      # mass flows to the best value
    assert np.allclose(improved_policy(p, [0, 1], np.zeros(2), tau=0.5), p)  # equal values change nothing


def _setup(tmp_path, **kw):
    torch.manual_seed(0)
    path = tmp_path / "start.pt"
    save_policy(Actor(64), Critic(64), path)
    cfg = DistillConfig(worlds=4, topk=3, labels_per_round=300, deals_per_task=2, workers=2, minibatch=128,
                        label_prob=0.5, **kw)
    return cfg, path


def test_labels_have_the_right_shapes_and_are_distributions(tmp_path):
    cfg, path = _setup(tmp_path)
    dm._worker_init(cfg)
    r = label_task(5, (str(path), 0))
    assert r["count"] > 5
    b = LabelBatch([r])
    assert len(b) == r["count"] and len(b.A) == len(b.T) == int(b.n.sum())
    for i in range(len(b)):
        t = b.T[b.off[i]:b.off[i] + b.n[i]]
        assert abs(t.sum() - 1) < 1e-4 and (t >= 0).all()


def test_fitting_reduces_the_loss_on_fixed_labels(tmp_path):
    cfg, path = _setup(tmp_path)
    dm._worker_init(cfg)
    batch = LabelBatch([label_task(s, (str(path), 0)) for s in (1, 2, 3)])
    actor = Actor(64).train()
    opt = torch.optim.Adam(actor.parameters(), lr=2e-3)
    rng, dev = np.random.default_rng(0), torch.device("cpu")
    first = fit(actor, opt, batch, DistillConfig(epochs=1, minibatch=128), rng, dev)
    for _ in range(12):
        last = fit(actor, opt, batch, DistillConfig(epochs=1, minibatch=128), rng, dev)
    assert last["ce"] < first["ce"] and last["agree"] > first["agree"]


def test_distill_rounds_run_and_write_a_loadable_model(tmp_path):
    cfg, path = _setup(tmp_path)
    logs = []
    distill(cfg, path, tmp_path / "out", rounds=2, log=logs.append)
    assert len(logs) == 2 and (tmp_path / "out" / "model.pt").exists()
    from guandan.rl.policy import load_policy
    load_policy(tmp_path / "out" / "model.pt", critic=True)
