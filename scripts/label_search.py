"""Label decisions with search under a fixed teacher policy (slow; run once, fit many times).

  python scripts/label_search.py --teacher runs/ppo/model.pt --out runs/labels --chunks 4 --labels 50000
Then: python scripts/fit_distill.py --labels runs/labels --init runs/ppo/model.pt --out runs/fit1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guandan.rl.distill import DistillConfig, label_dataset  # noqa: E402

if __name__ == "__main__":
    d = DistillConfig()
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", default="runs/ppo/model.pt")
    ap.add_argument("--out", default="runs/labels")
    ap.add_argument("--chunks", type=int, default=4)
    ap.add_argument("--labels", type=int, default=50_000, help="labelled decisions per file")
    ap.add_argument("--worlds", type=int, default=d.worlds)
    ap.add_argument("--topk", type=int, default=d.topk)
    ap.add_argument("--label-prob", type=float, default=d.label_prob)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    cfg = DistillConfig(worlds=a.worlds, topk=a.topk, label_prob=a.label_prob, labels_per_round=a.labels,
                        workers=a.workers, seed=a.seed)
    label_dataset(cfg, a.teacher, a.out, a.chunks, log=lambda s: print(s, flush=True))
