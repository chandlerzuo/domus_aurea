"""How well does an agent stop the "saved runout" pattern?

  python scripts/evaluate_runout.py --a ppo --positions 600 --procs 8
  python scripts/evaluate_runout.py --a "ppo+,worlds=32,topk=4,belief=1" --a2 ppo:runs/league2/model.pt

One opponent holds only a runout hand (e.g. a full house, a bomb and a high single) and is on lead; its partner is
the heuristic player; the other two seats are the agent under test, with ordinary mid-game hands. Score = levels per
deal for the agent's team (negative means the runout wins). Agent specs are those of scripts/evaluate_suite.py.
"""
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402


def chunk(args):
    spec, n, seed = args
    import torch
    torch.set_num_threads(1)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from evaluate_suite import factory
    from guandan.game import team
    from guandan.rl.scenarios import runout_position
    make = factory(spec)
    rng = np.random.default_rng(seed)
    scores, firsts = [], 0
    for k in range(n):
        d, h, scripted = runout_position(rng)
        agents = [scripted.get(s) or make(seed * 1009 + 4 * k + s) for s in range(4)]
        while not d.done:
            obs = d.observation(d.to_act)
            d.play(obs["legal"][agents[d.to_act].act(obs)])
        win, up = d.result()
        scores.append(up if win != team(h) else -up)
        firsts += d.finished[0] == h
    return scores, firsts


def run(spec, positions, procs, seed):
    per = max(1, positions // procs)
    with ProcessPoolExecutor(procs) as ex:
        res = list(ex.map(chunk, [(spec, per, seed + 31 * k) for k in range(procs)]))
    s = np.asarray([x for r in res for x in r[0]], dtype=float)
    return s, sum(r[1] for r in res)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True)
    ap.add_argument("--a2", help="a second agent on the same positions (reports the difference too)")
    ap.add_argument("--positions", type=int, default=600)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--seed", type=int, default=555)
    a = ap.parse_args()
    s1, f1 = run(a.a, a.positions, a.procs, a.seed)
    se = lambda x: x.std(ddof=1) / np.sqrt(len(x))
    print(f"{a.a}: {s1.mean():+.3f} ± {se(s1):.3f} levels, team wins {np.mean(s1 > 0):.1%}, runout player finishes first {f1 / len(s1):.1%} ({len(s1)} positions)")
    if a.a2:
        s2, f2 = run(a.a2, a.positions, a.procs, a.seed)
        print(f"{a.a2}: {s2.mean():+.3f} ± {se(s2):.3f} levels, team wins {np.mean(s2 > 0):.1%}, runout player finishes first {f2 / len(s2):.1%}")
        d = s1 - s2
        print(f"difference (first - second): {d.mean():+.3f} ± {se(d):.3f}")
