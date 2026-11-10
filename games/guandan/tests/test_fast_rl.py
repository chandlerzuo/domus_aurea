"""The batched Rust actors must record decisions that the networks reproduce exactly."""
import numpy as np
import pytest
import torch

from guandan.rl import ppo
from guandan.rl.features import STATE_DIM
from guandan.rl.policy import ORACLE_DIM, Actor, Critic, padded_log_probs, save_policy
from guandan.rl.ppo import Batch, PPOConfig, play_task_fast

pytest.importorskip("guandan_core")


def _task(tmp_path, mode, snaps=(), cfg=None, n=12, seed=3):
    torch.manual_seed(0)
    path = tmp_path / "latest.pt"
    save_policy(Actor(64), Critic(64), path)
    ppo._worker_init(cfg or PPOConfig(hidden=64, tables_per_worker=8))
    return play_task_fast(seed, n, mode, (str(path), 0), list(snaps)), path


def test_recorded_decisions_are_reproduced_by_the_networks(tmp_path):
    for p_heur in (0.0, 1.0):  # all self-play, then all against the heuristic
        cfg = PPOConfig(hidden=64, tables_per_worker=8, p_heuristic=p_heur, p_dmc=0.0, p_snapshot=0.0)
        r, path = _task(tmp_path, "ppo", cfg=cfg)
        assert r["S"].shape[1] == STATE_DIM and r["O"].shape[1] == ORACLE_DIM
        assert r["n"].sum() == len(r["A"]) and np.all(r["chosen"] < r["n"]) and np.all(r["n"] > 1)
        b = Batch([r])
        from guandan.rl.policy import load_policy
        actor, critic = load_policy(path, critic=True)
        idx = np.arange(len(b))
        mb = b.minibatch(idx, torch.device("cpu"))
        with torch.no_grad():
            hs = actor.state(mb["s"])
            lp = padded_log_probs(actor.logits(hs, mb["a"], mb["seg"]), mb["seg"], mb["pos"], len(idx), mb["width"])
            logp = lp.gather(1, mb["chosen"][:, None]).squeeze(1)
            v = critic(mb["s"], mb["o"])
        assert torch.allclose(logp, mb["logp"], atol=2e-4)
        # returns = advantages + value predictions, so value = ret - adv
        assert torch.allclose(v, mb["ret"] - mb["adv"], atol=2e-4)
        assert set(r["scores_by"]) <= {"self", "heuristic"} and sum(map(len, r["scores_by"].values())) == 12


def test_all_opponent_kinds_and_bc_run(tmp_path):
    r0, path = _task(tmp_path, "ppo")
    snap = tmp_path / "snap.pt"
    save_policy(Actor(64), Critic(64), snap)
    cfg = PPOConfig(hidden=64, tables_per_worker=8, p_heuristic=0.3, p_dmc=0.0, p_snapshot=0.7)
    r, _ = _task(tmp_path, "ppo", snaps=[str(snap)], cfg=cfg, n=16)
    assert "snapshot" in r["scores_by"] and "heuristic" in r["scores_by"]
    bc, _ = _task(tmp_path, "bc", n=6)
    assert set(bc["scores_by"]) == {"bc"} and np.all(bc["adv"] == 0) and np.all(bc["n"] > 1)
    assert np.all(np.abs(np.abs(bc["ret"])[:, None] - np.array([1 / 3, 2 / 3, 1.0])).min(1) < 1e-6)


def test_trains_end_to_end_on_the_batched_actors(tmp_path):
    cfg = PPOConfig(hidden=64, workers=2, tables_per_worker=16, steps_per_update=4000, bc_chunk=3000,
                    minibatch=512, snapshot_every=1, p_dmc=0.0)
    logs = []
    ppo.train(cfg, bc_deals=48, ppo_deals=96, out=tmp_path / "run", log=logs.append)
    assert any("batched, Rust core" in l for l in logs)
    assert (tmp_path / "run" / "model.pt").exists() and (tmp_path / "run" / "bc.pt").exists()
