"""Train the policy toward the search player's choices (expert iteration; see guandan/rl/distill.py).

  python scripts/train_distill.py --init runs/ppo/model.pt --out runs/distill --rounds 20
Each round labels ~100k decisions with search (about 10 minutes on 10 cores) and fits the policy to them.
Check progress with scripts/evaluate.py, e.g. --a ppo:runs/distill/model.pt --b ppo --pairs 500
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guandan.rl.distill import DistillConfig, distill  # noqa: E402

if __name__ == "__main__":
    d = DistillConfig()
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", default="runs/ppo/model.pt")
    ap.add_argument("--out", default="runs/distill")
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--labels", type=int, default=d.labels_per_round, help="labelled decisions per round")
    ap.add_argument("--worlds", type=int, default=d.worlds)
    ap.add_argument("--topk", type=int, default=d.topk)
    ap.add_argument("--tau", type=float, default=d.tau)
    ap.add_argument("--label-prob", type=float, default=d.label_prob)
    ap.add_argument("--lr", type=float, default=d.lr)
    ap.add_argument("--epochs", type=int, default=d.epochs)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    cfg = DistillConfig(worlds=a.worlds, topk=a.topk, tau=a.tau, label_prob=a.label_prob,
                        labels_per_round=a.labels, lr=a.lr, epochs=a.epochs, workers=a.workers, seed=a.seed)
    distill(cfg, a.init, a.out, a.rounds, log=lambda s: print(s, flush=True))
