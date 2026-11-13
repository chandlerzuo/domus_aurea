"""Behaviour profile of an agent: what it does when it plays against a copy of the base model.

  python scripts/profile_agent.py --a ppo:runs/styles/pop_racer/model.pt --b ppo --deals 600

Reports per player: bombs played per deal, passes per deal, plays per deal, how often it goes out first, and
the average number of cards left in its hand when its team's deal ends. These are the behaviours that make
agents trained with different rewards play differently.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402


def main():
    import torch
    torch.set_num_threads(2)
    from evaluate_suite import factory
    from guandan.game import Deal, deal_cards, team
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", default="ppo")
    ap.add_argument("--deals", type=int, default=400)
    ap.add_argument("--seed", type=int, default=31)
    a = ap.parse_args()
    fa, fb = factory(a.a), factory(a.b)
    rng = np.random.default_rng(a.seed)
    stat = {k: np.zeros(2) for k in ("bombs", "passes", "plays", "first", "left")}
    wins = []
    for k in range(a.deals):
        hands, level, leader = deal_cards(rng), int(rng.integers(13)), int(rng.integers(4))
        a_team = k % 2
        agents = [(fa if team(s) == a_team else fb)(a.seed * 1000 + 4 * k + s) for s in range(4)]
        d = Deal(hands, level, leader)
        cnt = {s: [0, 0, 0] for s in range(4)}   # bombs, passes, plays
        while not d.done:
            s = d.to_act
            obs = d.observation(s)
            m = obs["legal"][agents[s].act(obs)]
            cnt[s][1] += m.is_pass
            cnt[s][2] += not m.is_pass
            cnt[s][0] += m.combo.is_bomb
            d.play(m)
        win, up = d.result()
        wins.append(up if win == a_team else -up)
        for s in range(4):
            who = int(team(s) != a_team)
            stat["bombs"][who] += cnt[s][0] / 2
            stat["passes"][who] += cnt[s][1] / 2
            stat["plays"][who] += cnt[s][2] / 2
            stat["first"][who] += (d.finished[0] == s)
            stat["left"][who] += len(d.hands[s]) / 2
    n = a.deals
    print(f"{a.a} (A) vs {a.b} (B): A scores {np.mean(wins):+.3f} ± {np.std(wins) / np.sqrt(n):.3f} levels per deal")
    for name, label in (("bombs", "bombs played / player / deal"), ("passes", "passes / player / deal"), ("plays", "plays / player / deal"),
                        ("first", "goes out first (share of deals, per player)"), ("left", "cards left at the end / player")):
        v = stat[name] / n
        if name == "first":
            v = v / 2
        print(f"  {label:44s} A {v[0]:6.2f}   B {v[1]:6.2f}")


if __name__ == "__main__":
    main()
