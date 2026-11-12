"""Where do the AI seats lose levels in recorded games? Exact-solver regret on late-game decisions.

  python scripts/analyse_ai_endgames.py --db games.db --cards 22

Replays each recorded deal. At every decision of an AI seat with at most --cards cards left in total, the exact solver
(perfect play by everybody, using the real hidden hands) values every legal move; the regret of the AI's choice is the
best value minus its value, in levels for the AI's team. This is hindsight: the AI could not see the other hands, so
small regrets are normal -- look at how often a regret of 1+ level happens and at the kinds of moves involved.
"""
import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

import guandan_core as core  # noqa: E402
from guandan.game import team  # noqa: E402
from guandan.review import label, move_from_record, start_deal  # noqa: E402


def _tuple(m):
    return int(m.combo.kind), m.combo.value, m.combo.size, [int(c) for c in m.cards]


def real_world(d):
    """The true state as an RsDeal (all four real hands)."""
    passes = 0
    if d.table is not None:
        for _, m in reversed(d.history):
            if m.is_pass:
                passes += 1
            else:
                break
    return core.RsDeal.from_state(
        [list(h) for h in d.hands], d.level, d.to_act, tuple(d.team_levels), d.level_team,
        None if d.table is None else _tuple(d.table), d.table_seat, passes, list(d.finished),
        [(s, _tuple(m)) for s, m in d.history], [list(p) for p in d.played], 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--cards", type=int, default=22)
    ap.add_argument("--budget", type=int, default=1_500_000)
    ap.add_argument("--show", type=int, default=12, help="how many of the worst decisions to print")
    a = ap.parse_args()
    rows = [json.loads(r) for (r,) in sqlite3.connect(a.db).execute("SELECT record FROM deals ORDER BY id")]
    regrets, worst, skipped, kinds = [], [], 0, collections.Counter()
    for k, rec in enumerate(rows):
        d = start_deal(rec)
        for i, entry in enumerate(rec["moves"]):
            seat = entry[0]
            m = move_from_record(entry)
            if rec["kinds"][seat] != "human" and sum(len(h) for h in d.hands) <= a.cards:
                legal = d.legal()
                if len(legal) > 1:
                    vals = real_world(d).solve(a.budget)
                    idx = next((j for j, x in enumerate(legal) if x.combo == m.combo and sorted(x.cards) == sorted(m.cards)), None)
                    if vals is None or idx is None:
                        skipped += 1
                    else:
                        reg = max(vals) - vals[idx]
                        regrets.append(reg)
                        if reg >= 1:
                            kinds[("pass" if m.is_pass else str(m.combo))] += 1
                            best = max(range(len(vals)), key=lambda j: vals[j])
                            worst.append((reg, k, i, seat, label(m), label(legal[best]), [len(h) for h in d.hands]))
            d.play(m)
    r = np.array(regrets)
    print(f"{len(rows)} deals; {len(r)} AI decisions with <= {a.cards} cards left ({skipped} skipped: too big to solve)")
    print(f"mean regret {r.mean():.3f} levels; regret >= 1 in {np.mean(r >= 1):.1%} of decisions, >= 2 in {np.mean(r >= 2):.1%}")
    print("moves with regret >= 1 by kind:", dict(kinds.most_common()))
    for reg, k, i, seat, played, best, counts in sorted(worst, reverse=True)[:a.show]:
        print(f"  deal #{k} move {i} seat {seat} cards {counts}: played {played}  (best: {best}; regret {reg})")


if __name__ == "__main__":
    main()
