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
    ap.add_argument("--init", help="start from this policy checkpoint (widened to --version if older)")
    ap.add_argument("--version", type=int, default=1, help="feature version for new networks / widening (1 or 2)")
    ap.add_argument("--steps-per-update", type=int, default=65536)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--queue", type=int, default=1, help="tasks queued per actor; more keeps actors busy but trains on staler data")
    ap.add_argument("--tables", type=int, default=32, help="deals each actor plays side by side (Rust core)")
    ap.add_argument("--league", nargs="*", default=[], help="checkpoints that stay in the opponent pool all run (any feature version)")
    ap.add_argument("--p-heuristic", type=float, default=PPOConfig.p_heuristic)
    ap.add_argument("--p-dmc", type=float, default=PPOConfig.p_dmc)
    ap.add_argument("--p-snapshot", type=float, default=PPOConfig.p_snapshot, help="share of deals against league + snapshots")
    ap.add_argument("--match-bonus", type=float, default=0.0, help="extra levels of reward for the deal that ends the match")
    ap.add_argument("--p-endgame", type=float, default=0.0, help="share of deals that start late (12-40 cards left in total)")
    a = ap.parse_args()
    cfg = PPOConfig(p_endgame=a.p_endgame, match_bonus=a.match_bonus, league=a.league, p_heuristic=a.p_heuristic, p_dmc=a.p_dmc, p_snapshot=a.p_snapshot, workers=a.workers, lr=a.lr, entropy=a.entropy, device=a.device, seed=a.seed, version=a.version,
                    steps_per_update=a.steps_per_update, tables_per_worker=a.tables, epochs=a.epochs,
                    queue_per_worker=a.queue)
    train(cfg, a.bc_deals, a.ppo_deals, a.out, resume=a.resume, init=a.init)
