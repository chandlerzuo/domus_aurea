"""Imitation warm start from the heuristic, then PPO fine-tuning with an oracle critic.

  python scripts/train_ppo.py --bc-deals 200000 --ppo-deals 1000000 --out runs/ppo
  python scripts/train_ppo.py --bc-deals 0 --ppo-deals 1000000 --out runs/ppo   # PPO from runs/ppo/bc.pt
  python scripts/train_ppo.py --bc-deals 0 --ppo-deals 1000000 --resume          # continue from model.pt
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guandan.rl.ppo import PPOConfig, train  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bc-deals", type=int, default=200_000)
    ap.add_argument("--ppo-deals", type=int, default=1_000_000)
    ap.add_argument("--out", default="runs/ppo")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--entropy", type=float, default=0.003)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    cfg = PPOConfig(workers=a.workers, lr=a.lr, entropy=a.entropy, device=a.device, seed=a.seed)
    train(cfg, a.bc_deals, a.ppo_deals, a.out, resume=a.resume)
