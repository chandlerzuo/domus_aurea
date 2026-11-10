"""Fit a policy to saved search labels (see scripts/label_search.py). Fast; try several settings.

  python scripts/fit_distill.py --labels runs/labels --init runs/ppo/model.pt --out runs/fit1 --tau 0.5 --lr 1e-4 --epochs 4
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from guandan.rl.dmc import _device  # noqa: E402
from guandan.rl.distill import DistillConfig, LabelBatch, fit  # noqa: E402
from guandan.rl.policy import load_policy, save_policy  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, help="directory with labels_*.npz")
    ap.add_argument("--init", default="runs/ppo/model.pt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tau", type=float, default=0.5)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--passes", type=int, default=1, help="repeat the whole fit this many times")
    ap.add_argument("--holdout", type=float, default=0.1, help="share of labels kept to measure the fit")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    files = sorted(Path(a.labels).glob("labels_*.npz"))
    torch.set_num_threads(4)
    batch = LabelBatch.load(files, a.tau)
    rng = np.random.default_rng(a.seed)
    cfg = DistillConfig(lr=a.lr, epochs=a.epochs)
    dev = _device("auto")
    actor, critic = load_policy(a.init, critic=True)
    actor = actor.to(dev).train()
    opt = torch.optim.Adam(actor.parameters(), lr=a.lr)
    n = len(batch)
    perm = rng.permutation(n)
    hold = perm[: int(a.holdout * n)]
    train = perm[int(a.holdout * n):]

    def subset(idx):
        b = LabelBatch.__new__(LabelBatch)
        for k in ("S", "O", "n", "C", "V"):
            setattr(b, k, getattr(batch, k)[idx])
        rows = np.concatenate([np.arange(batch.off[i], batch.off[i] + batch.n[i]) for i in idx])
        b.A, b.P, b.T = batch.A[rows], batch.P[rows], batch.T[rows]
        b.off = np.concatenate([[0], np.cumsum(b.n)[:-1]])
        return b

    tr, ho = subset(train), subset(hold)

    def holdout_stats() -> tuple[float, float]:
        """Cross-entropy of the policy to the labels, and the same for the starting policy's own probabilities."""
        actor.eval()
        ce = 0.0
        with torch.no_grad():
            from guandan.rl.policy import padded_log_probs
            for st in range(0, len(ho), 4096):
                mb = ho.minibatch(np.arange(st, min(st + 4096, len(ho))), dev)
                hs = actor.state(mb["s"])
                lp = padded_log_probs(actor.logits(hs, mb["a"], mb["seg"]), mb["seg"], mb["pos"], len(mb["target"]), mb["width"])
                ce += float(-(mb["target"] * lp).sum(1).sum())
        actor.train()
        return ce / len(ho)

    print(f"{n} labels ({len(tr)} train, {len(ho)} held out); held-out cross-entropy to the labels: {holdout_stats():.4f}", flush=True)
    for ps in range(a.passes):
        st = fit(actor, opt, tr, cfg, rng, dev)
        print(f"pass {ps + 1}: train {st}; held-out cross-entropy {holdout_stats():.4f}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    save_policy(actor, critic, out / "model.pt")
    print("saved", out / "model.pt")
