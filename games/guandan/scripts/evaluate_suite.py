"""Fixed evaluation suite: one agent against several opponents on the same duplicate deals, in parallel.

  python scripts/evaluate_suite.py --a ppo+ --vs ppo ppo:runs/ppo/v1.pt heuristic --pairs 1000 --procs 10

An agent spec is  KIND[:PATH][,key=value ...]  with KIND one of
  heuristic, random, dmc, ppo (greedy policy), ppo~ (sampled), ppo+ / search (policy + search)
e.g.  ppo+:runs/ppo/model.pt,worlds=64,topk=5,margin=0.1,belief=1.0
Search keys: worlds, topk, margin, belief (0 = uniform hidden hands, 1 = weight by the belief head),
  eg (use the endgame search once all hands together hold at most this many cards), egworlds, egtopk,
  solve (exactly solve sampled worlds once all hands together hold at most this many cards), sworlds, sbudget.

Every number is levels per deal for the first agent, with its standard error over 2 x pairs deals
(each deal is played twice with the teams swapped). The same seeds are used for every opponent,
so differences between rows are paired.
"""
import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402


def parse(spec: str):
    head, _, opts = spec.partition(",")
    kind, _, path = head.partition(":")
    kw = dict(p.split("=", 1) for p in opts.split(",") if p)
    return kind, path, kw


def factory(spec: str):
    import torch
    torch.set_num_threads(1)
    kind, path, kw = parse(spec)
    if kind in ("ppo+", "search"):
        from guandan.rl.policy import DEFAULT_POLICY, load_policy
        from guandan.rl.search import SearchAgent
        actor = load_policy(path or DEFAULT_POLICY)
        return lambda seed: SearchAgent(actor, seed=seed, worlds=int(kw.get("worlds", 32)), topk=int(kw.get("topk", 4)),
                                        margin=float(kw.get("margin", 0.0)), belief=float(kw.get("belief", 0.0)),
                                        endgame_cards=int(kw.get("eg", 0)), endgame_worlds=int(kw.get("egworlds", 128)), endgame_topk=int(kw.get("egtopk", 99)),
                                        solve_cards=int(kw.get("solve", 0)), solve_worlds=int(kw.get("sworlds", 16)),
                                        solve_budget=int(kw.get("sbudget", 100000)))
    if kind in ("ppo", "ppo~", "bc"):
        from guandan.rl.policy import DEFAULT_POLICY, PolicyAgent, load_policy
        actor = load_policy(path or (DEFAULT_POLICY if kind != "bc" else DEFAULT_POLICY.with_name("bc.pt")))
        return lambda seed: PolicyAgent(actor, seed=seed, greedy=kind != "ppo~")
    if kind == "dmc":
        from guandan.rl.dmc import DEFAULT_MODEL, DMCAgent, load_net
        net = load_net(path or DEFAULT_MODEL)
        return lambda seed: DMCAgent(net, seed=seed)
    from guandan.agents import AGENTS
    return lambda seed: AGENTS[kind](seed=seed)


def chunk(args):
    a, b, pairs, seed = args
    from guandan.evaluate import duplicate
    r = duplicate(factory(a), factory(b), pairs, seed)
    return r["points_per_deal"], r["stderr"], r["win_rate"], r["deals"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True)
    ap.add_argument("--vs", nargs="+", required=True)
    ap.add_argument("--pairs", type=int, default=1000, help="duplicate pairs per opponent (total, across processes)")
    ap.add_argument("--procs", type=int, default=10)
    ap.add_argument("--seed", type=int, default=2024, help="the same seed for every opponent")
    a = ap.parse_args()
    per = max(1, a.pairs // a.procs)
    print(f"{a.a}  |  {per * a.procs} pairs = {2 * per * a.procs} deals per row")
    print(f"{'opponent':46s} {'levels/deal':>16s} {'win rate':>9s} {'minutes':>8s}")
    with ProcessPoolExecutor(a.procs) as ex:
        for b in a.vs:
            t0 = time.time()
            res = list(ex.map(chunk, [(a.a, b, per, a.seed + 7919 * k) for k in range(a.procs)]))
            m = np.mean([r[0] for r in res])
            se = np.sqrt(sum(r[1] ** 2 for r in res)) / len(res)
            win = np.mean([r[2] for r in res])
            print(f"{b:46s} {m:+9.3f} ± {se:.3f} {win:9.1%} {(time.time() - t0) / 60:8.1f}", flush=True)
