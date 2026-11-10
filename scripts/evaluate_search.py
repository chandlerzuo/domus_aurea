"""Duplicate-deal match: policy + search against the plain policy (same network), in parallel.

  python scripts/evaluate_search.py --model runs/ppo/model.pt --pairs 300 --worlds 16 --procs 4
"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402


def chunk(args):
    import torch
    torch.set_num_threads(1)
    from guandan.evaluate import duplicate
    from guandan.rl.policy import PolicyAgent, load_policy
    from guandan.rl.search import SearchAgent
    model, opponent, pairs, seed, worlds, topk, margin = args
    actor = load_policy(model)
    other = load_policy(opponent) if opponent else actor
    t = [0.0, 0]

    class Timed(SearchAgent):
        def act(self, obs):
            t0 = time.time()
            i = super().act(obs)
            if len(obs["legal"]) > 1:
                t[0] += time.time() - t0
                t[1] += 1
            return i

    r = duplicate(lambda s: Timed(actor, seed=s, worlds=worlds, topk=topk, margin=margin),
                  lambda s: PolicyAgent(other, seed=s), pairs, seed)
    return r, t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="runs/ppo/model.pt")
    ap.add_argument("--opponent", help="plain policy for the other team (default: same network)")
    ap.add_argument("--pairs", type=int, default=300)
    ap.add_argument("--worlds", type=int, default=16)
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--margin", type=float, default=0.0)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--seed", type=int, default=777)
    a = ap.parse_args()
    per = max(1, a.pairs // a.procs)
    t0 = time.time()
    with ProcessPoolExecutor(a.procs) as ex:
        res = list(ex.map(chunk, [(a.model, a.opponent, per, a.seed + k, a.worlds, a.topk, a.margin) for k in range(a.procs)]))
    m = np.mean([r["points_per_deal"] for r, _ in res])
    se = np.sqrt(sum(r["stderr"] ** 2 for r, _ in res)) / len(res)
    win = np.mean([r["win_rate"] for r, _ in res])
    calls = sum(t[1] for _, t in res)
    secs = sum(t[0] for _, t in res)
    print(f"search(worlds={a.worlds}, topk={a.topk}, margin={a.margin}) vs plain policy: {m:+.3f} ± {se:.3f} levels/deal, "
          f"win {win:.1%} over {per * a.procs * 2} deals; {1000 * secs / max(calls, 1):.0f} ms/decision ({calls} decisions); "
          f"{time.time() - t0:.0f}s", flush=True)
