"""How strong is the AI against people? Results of recorded games, by AI version and by player.

  python scripts/human_vs_ai.py --db /var/lib/guandan/games.db            # copy the server's database first
  python scripts/human_vs_ai.py --db games.db --include-assisted

Each recorded deal is one human (with an AI partner) against two AIs. The score is the human team's levels gained per deal:
0 means the human plus their AI partner are exactly as good as the AI team; positive means the human is better. Deals where the
human used the AI's move suggestions are left out unless --include-assisted. "model" is the AI version saved with each deal
(older deals have none). With about 2.2 levels of spread per deal, 100 deals give a standard error of about 0.22, so you need
a few hundred deals to tell small differences apart.
"""
import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from guandan.game import team  # noqa: E402


def line(label: str, xs) -> str:
    x = np.asarray(xs, dtype=float)
    se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else float("nan")
    return f"{label:34s} {len(x):5d} deals  {x.mean():+.2f} ± {se:.2f} levels/deal   human team wins {np.mean(x > 0):.0%}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--include-assisted", action="store_true")
    a = ap.parse_args()
    by_model, by_player, by_pair = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    skipped = total = 0
    for (rec,) in sqlite3.connect(a.db).execute("SELECT record FROM deals ORDER BY id"):
        r = json.loads(rec)
        humans = r["humans"]
        if len(humans) != 1 or any(k == "human" for i, k in enumerate(r["kinds"]) if i not in humans):
            continue                                    # only one-human-with-AI-partner deals are comparable
        total += 1
        if r["assisted"] and not a.include_assisted:
            skipped += 1
            continue
        h = humans[0]
        win, up = r["result"]["win_team"], r["result"]["up"]
        v = up if win == team(h) else -up
        model = r.get("model", "before tracking")
        by_model[model].append(v)
        by_player[r["names"][h]].append(v)
        by_pair[(model, r["names"][h])].append(v)
    print(f"{total} one-human deals ({skipped} left out because the human used move suggestions)\n")
    print("By AI version:")
    for m, xs in sorted(by_model.items()):
        print("  " + line(m, xs))
    print("\nBy player (all AI versions):")
    for n, xs in sorted(by_player.items(), key=lambda kv: -len(kv[1])):
        print("  " + line(n, xs))
    if len(by_model) > 1:
        print("\nBy AI version and player:")
        for (m, n), xs in sorted(by_pair.items()):
            if len(xs) >= 5:
                print("  " + line(f"{m} / {n}", xs))


if __name__ == "__main__":
    main()
