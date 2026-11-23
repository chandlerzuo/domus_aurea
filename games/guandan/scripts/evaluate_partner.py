"""How good a teammate is an AI when its partner is NOT a copy of itself?

  python scripts/evaluate_partner.py --a runs/round3/model.pt --b ppo --pairs 800 --procs 12

Team 1 is the candidate paired with a partner of another kind (the heuristic player, a scripted style, an older network, ...);
team 2 is two copies of the reference network. The same deals are played for each candidate, with the teams' seats swapped, so
the table's rows compare candidate A and candidate B as teammates for the same partners. The number is levels per deal for team 1.
Agent specs are those of scripts/evaluate_suite.py (e.g. ppo, ppo:PATH, style:bomber, heuristic).
"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

PARTNERS = ["heuristic", "style:bomber", "style:turtle", "style:keeper", "style:overtaker", "style:noisy", "style:sprinter",
            "style:single_dumper", "ppo:runs/ppo/v1.pt"]


def chunk(args):
    cand, partner, ref, pairs, seed = args
    import torch
    torch.set_num_threads(1)
    from evaluate_suite import factory
    from guandan.evaluate import play_deal
    from guandan.game import deal_cards
    fc, fp, fr = factory(cand), factory(partner), factory(ref)
    rng = np.random.default_rng(seed)
    scores = []
    for k in range(pairs):
        hands, level, leader = deal_cards(rng), int(rng.integers(13)), int(rng.integers(4))
        for team1 in (0, 1):                                    # the candidate's team sits at seats 0/2, then at 1/3
            agents = [None] * 4
            agents[team1], agents[team1 + 2] = fc(seed * 7 + 4 * k + team1), fp(seed * 11 + 4 * k + team1)
            agents[1 - team1], agents[3 - team1] = fr(seed * 13 + 4 * k), fr(seed * 17 + 4 * k)
            win, up = play_deal(agents, hands, level, leader)
            scores.append(up if win == team1 else -up)
    return scores


def run(cand, partner, ref, pairs, procs, seed):
    per = max(1, pairs // procs)
    with ProcessPoolExecutor(procs) as ex:
        res = list(ex.map(chunk, [(cand, partner, ref, per, seed + 101 * k) for k in range(procs)]))
    return np.array([x for r in res for x in r], dtype=float)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="candidate (a path to a model file, or any agent spec)")
    ap.add_argument("--b", default="ppo", help="the candidate to compare with")
    ap.add_argument("--ref", default="ppo", help="the two opponents")
    ap.add_argument("--partners", nargs="+", default=PARTNERS)
    ap.add_argument("--pairs", type=int, default=600)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--seed", type=int, default=909)
    a = ap.parse_args()
    spec = lambda s: s if (":" in s or s in ("ppo", "heuristic") or s.startswith("style")) else f"ppo:{s}"
    A, B = spec(a.a), spec(a.b)
    print(f"{'partner':24s} {'A: ' + a.a:>22s} {'B: ' + a.b:>22s} {'A - B':>16s}")
    ta = tb = []
    for p in a.partners:
        xa = run(A, p, a.ref, a.pairs, a.procs, a.seed)
        xb = run(B, p, a.ref, a.pairs, a.procs, a.seed)
        d = xa - xb
        ta, tb = ta + [xa], tb + [xb]
        se = lambda x: x.std(ddof=1) / np.sqrt(len(x))
        print(f"{p:24s} {xa.mean():+9.3f} ± {se(xa):.3f}  {xb.mean():+9.3f} ± {se(xb):.3f}  {d.mean():+8.3f} ± {se(d):.3f}", flush=True)
    d = np.concatenate(ta) - np.concatenate(tb)
    print(f"{'all partners':24s} {np.concatenate(ta).mean():+9.3f}                {np.concatenate(tb).mean():+9.3f}    {d.mean():+8.3f} ± {d.std(ddof=1) / np.sqrt(len(d)):.3f}")


if __name__ == "__main__":
    main()
