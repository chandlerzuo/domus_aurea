"""Replay recorded human-vs-AI deals with the AI in every seat: luck of the hands versus skill of the play.

  python scripts/replay_luck.py --db games.db --reps 4 --procs 12

For each recorded deal (one human with an AI partner against two AIs) the same cards, level and leader are played again with
the AI in all four seats, several times. Results are levels for the human's team.
  replay    what the human's team gets from these hands when the AI plays them (the luck of the deal)
  actual    what the human's team really got
  actual - replay   how much the human played better (+) or worse (-) than the AI would have, on the same hands
"""
import argparse
import json
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402


def one(args):
    rec, reps, spec = args
    import torch
    torch.set_num_threads(1)
    from evaluate_suite import factory
    from guandan.game import team
    from guandan.review import start_deal
    make = factory(spec)
    h = rec["humans"][0]
    out = []
    for k in range(reps):
        d = start_deal(rec)
        agents = [make(1000 * k + s) for s in range(4)]
        while not d.done:
            obs = d.observation(d.to_act)
            d.play(obs["legal"][agents[d.to_act].act(obs)])
        win, up = d.result()
        out.append(up if win == team(h) else -up)
    win, up = rec["result"]["win_team"], rec["result"]["up"]
    return float(np.mean(out)), (up if win == team(h) else -up)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--ai", default="ppo+,worlds=32,topk=4,belief=1,eg=28,egworlds=64,egtopk=6", help="agent spec for every seat")
    a = ap.parse_args()
    recs = [json.loads(r) for (r,) in sqlite3.connect(a.db).execute("SELECT record FROM deals ORDER BY id")]
    recs = [r for r in recs if len(r["humans"]) == 1 and not r["assisted"]]
    with ProcessPoolExecutor(a.procs) as ex:
        res = list(ex.map(one, [(r, a.reps, a.ai) for r in recs], chunksize=1))
    replay, actual = np.array([r[0] for r in res]), np.array([r[1] for r in res])
    se = lambda x: x.std(ddof=1) / np.sqrt(len(x))
    d = actual - replay
    print(f"{len(res)} deals, {a.reps} AI replays each (AI plays all four seats)")
    print(f"  replay (luck of the hands, human team): {replay.mean():+.3f} ± {se(replay):.3f}")
    print(f"  actual (what the human team got):       {actual.mean():+.3f} ± {se(actual):.3f}")
    print(f"  actual - replay (human vs AI, same hands): {d.mean():+.3f} ± {se(d):.3f}")
    print(f"  deals where the human did better than the AI replay: {np.mean(d > 0.5):.0%}, worse: {np.mean(d < -0.5):.0%}")
    print(f"  replay and actual agree in sign on {np.mean(np.sign(replay) == np.sign(actual)):.0%} of deals; correlation {np.corrcoef(replay, actual)[0, 1]:.2f}")


if __name__ == "__main__":
    main()
