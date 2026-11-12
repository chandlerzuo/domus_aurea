"""Endgame benchmark: play from positions where few cards are left, one agent against another.

  python scripts/evaluate_endgame.py --a "ppo+,eg=28" --b ppo --cards 28 --positions 400 --procs 6

Positions come from plain-policy self-play (random deals and levels), stopped the first time all four hands
together hold at most --cards cards. Each position is played twice with the teams swapped, so card luck
cancels; the score is levels for agent A (+up when A's team wins the deal, -up otherwise).
Agent specs are those of scripts/evaluate_suite.py.
"""
import argparse
import copy
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402


def chunk(args):
    a, b, cards, n, seed = args
    import torch
    torch.set_num_threads(1)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from evaluate_suite import factory
    from guandan.game import Deal, deal_cards, team
    from guandan.rl.policy import PolicyAgent, load_policy
    fa, fb = factory(a), factory(b)
    gen = PolicyAgent(load_policy("runs/ppo/model.pt"), seed=seed, greedy=False)
    rng = np.random.default_rng(seed)
    scores = []
    for k in range(n):
        d = Deal(deal_cards(rng), int(rng.integers(13)), int(rng.integers(4)))
        while not d.done and sum(len(h) for h in d.hands) > cards:
            obs = d.observation(d.to_act)
            d.play(obs["legal"][gen.act(obs)])
        if d.done:
            continue
        for a_team in (0, 1):
            e = copy.deepcopy(d)
            agents = [(fa if team(s) == a_team else fb)(seed * 100003 + 4 * k + s) for s in range(4)]
            while not e.done:
                obs = e.observation(e.to_act)
                e.play(obs["legal"][agents[e.to_act].act(obs)])
            win, up = e.result()
            scores.append(up if win == a_team else -up)
    return scores


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", default="ppo")
    ap.add_argument("--cards", type=int, default=28, help="stop self-play when all hands hold at most this many cards")
    ap.add_argument("--positions", type=int, default=400)
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--seed", type=int, default=4242)
    a = ap.parse_args()
    per = max(1, a.positions // a.procs)
    t0 = time.time()
    with ProcessPoolExecutor(a.procs) as ex:
        res = list(ex.map(chunk, [(a.a, a.b, a.cards, per, a.seed + 101 * k) for k in range(a.procs)]))
    s = np.asarray([x for r in res for x in r], dtype=float)
    print(f"{a.a} vs {a.b}, <= {a.cards} cards left: {s.mean():+.3f} ± {s.std(ddof=1) / np.sqrt(len(s)):.3f} levels "
          f"over {len(s)} games ({per * a.procs} positions), win {np.mean(s > 0):.1%}, {(time.time() - t0) / 60:.1f} min")
