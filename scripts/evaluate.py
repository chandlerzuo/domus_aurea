"""Duplicate-deal match between two agent types.

  python scripts/evaluate.py --a dmc --b heuristic --pairs 2000
  python scripts/evaluate.py --a dmc:runs/dmc/snapshots/u0002500.pt --b dmc
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guandan.agents import AGENTS  # noqa: E402
from guandan.evaluate import duplicate  # noqa: E402


def factory(spec: str):
    if spec.startswith("dmc"):
        from guandan.rl.dmc import DEFAULT_MODEL, DMCAgent, load_net
        net = load_net(spec.split(":", 1)[1] if ":" in spec else DEFAULT_MODEL)
        return lambda seed: DMCAgent(net, seed=seed)
    return lambda seed: AGENTS[spec](seed=seed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="dmc")
    ap.add_argument("--b", default="heuristic")
    ap.add_argument("--pairs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=12345)
    a = ap.parse_args()
    r = duplicate(factory(a.a), factory(a.b), a.pairs, a.seed)
    print(f"{a.a} vs {a.b}: {r['points_per_deal']:+.3f} ± {r['stderr']:.3f} levels/deal, "
          f"win rate {r['win_rate']:.1%} over {r['deals']} deals")
