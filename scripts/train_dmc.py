"""Train the DMC agent by self-play.

  python scripts/train_dmc.py --deals 2000000 --out runs/dmc
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guandan.rl.dmc import DMCConfig, train  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--deals", type=int, default=1_000_000)
    ap.add_argument("--out", default="runs/dmc")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--batch", type=int, default=4096)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    cfg = DMCConfig(workers=a.workers, batch=a.batch, lr=a.lr, device=a.device, seed=a.seed)
    train(cfg, a.deals, a.out, resume=a.resume)
