"""Find "saved runout" finishes in recorded games and show where the AI could have deviated.

  python scripts/find_runouts.py --db /var/lib/guandan/games.db            # copy the server's database first
  python scripts/find_runouts.py --db data/games.db --min-cards 6 --verbose

A runout is a run of at least --min-plays plays by one player, each one a trick lead (everybody else passed on the
previous play), that empties the hand with at least --min-cards cards. For every deal where a human's team won that way
against AI seats, it reports:
  * the runout: the player, the combos in order, and the move number it started at
  * the race: at that moment, the leads each player still needed (fewest sets, see rl/plan.py) and their card counts
  * the missed chances: earlier plays by an AI seat that passed (or played small) while holding a move that beat the
    runout player's lead, and how often the AI passed on its own chance to take the lead
Run it on games from the real server to see which situations to train on.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guandan.cards import card_str  # noqa: E402
from guandan.game import Deal, team  # noqa: E402
from guandan.rl.plan import min_sets  # noqa: E402
from guandan.review import label, move_from_record, start_deal  # noqa: E402


def runouts(record: dict, min_plays: int, min_cards: int):
    """Yield (seat, first move index, [move indexes]) for each qualifying finish."""
    moves = record["moves"]
    d = start_deal(record)
    leads, plays_of = [], {}
    for i, entry in enumerate(moves):
        m = move_from_record(entry)
        leads.append(d.leading)
        d.play(m)
    # group each player's trailing run of consecutive lead plays
    for seat in range(4):
        idx = [i for i, e in enumerate(moves) if e[0] == seat and e[2] != 0]
        run = []
        for i in reversed(idx):
            if not leads[i]:
                break
            # between this lead and the player's next play only passes may occur
            if run and any(moves[j][2] != 0 for j in range(i + 1, run[-1])):
                break
            run.append(i)
        run.reverse()
        if len(run) >= min_plays and sum(len(moves[i][1]) for i in run) >= min_cards and \
                len(record["hands"][seat]) == sum(len(moves[i][1]) for i in idx):
            yield seat, run[0], run


def analyse(record: dict, seat: int, first: int, run: list[int]) -> dict:
    d = start_deal(record)
    for entry in record["moves"][:first]:
        d.play(move_from_record(entry))
    state = {s: (len(d.hands[s]), min_sets(d.hands[s], d.level)) for s in range(4) if d.hands[s]}
    # chances to take the lead: after each of the runout player's leads, did an opponent pass holding a beating move?
    missed, d2 = [], start_deal(record)
    for i, entry in enumerate(record["moves"]):
        if i >= first and entry[0] != seat and entry[2] == 0 and d2.table_seat == seat and team(d2.to_act) != team(seat):
            beating = [m for m in d2.legal() if not m.is_pass]
            if beating and record["kinds"][d2.to_act] != "human":
                missed.append((i, d2.to_act, len(beating), min(beating, key=lambda m: (m.combo.is_bomb, len(m.cards)))))
        d2.play(move_from_record(entry))
    return {"state": state, "missed": missed, "combos": [label(move_from_record(record["moves"][i])) for i in run]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--min-plays", type=int, default=2)
    ap.add_argument("--min-cards", type=int, default=6)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    rows = db.execute("SELECT id, record FROM deals ORDER BY id").fetchall()
    found = vs_ai = 0
    for deal_id, rec in rows:
        record = json.loads(rec)
        for seat, first, run in runouts(record, a.min_plays, a.min_cards):
            found += 1
            human = record["kinds"][seat] == "human"
            ai_opponents = [s for s in range(4) if team(s) != team(seat) and record["kinds"][s] != "human"]
            if not (human and ai_opponents):
                continue
            vs_ai += 1
            info = analyse(record, seat, first, run)
            print(f"deal {deal_id} (table {record['table']}, deal {record['deal_no']}): {record['names'][seat]} (seat {seat}) "
                  f"ran out {len(run)} combos from move {first}: {' -> '.join(info['combos'])}")
            print("   at that moment (cards left, fewest sets):", {s: v for s, v in info["state"].items()})
            if info["missed"]:
                for i, s, n, m in info["missed"]:
                    print(f"   move {i}: AI seat {s} passed with {n} move(s) that beat the lead, e.g. {label(m)}")
            elif a.verbose:
                print("   no AI seat passed with a move that beat the lead")
    print(f"\n{len(rows)} deals scanned; {found} runout finishes; {vs_ai} by a human against AI seats")


if __name__ == "__main__":
    main()
