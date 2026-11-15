"""Failure-mode analysis of recorded human-vs-AI games.

  python scripts/analyse_failures.py --db games.db [--model runs/ppo/model.pt] [--procs 4]

For every deal it reports how the deal was lost and what the AI team was left holding, then scores every AI decision:
the AI's actual move is compared with its top alternatives by playing the rest of the deal out with the real hidden hands
(the model plays every seat, greedily). The regret of a decision is the best alternative's result minus the AI move's, in
levels for the AI team. This is hindsight (the AI could not see the hands), so small regrets are noise; the point is which
kinds of decisions carry most of the total regret.
"""
import argparse
import collections
import json
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from guandan.game import team  # noqa: E402

KIND = {0: "pass", 1: "single", 2: "pair", 3: "triple", 4: "full house", 5: "straight", 6: "tube", 7: "plate", 8: "bomb",
        9: "straight flush", 10: "joker bomb"}


def _tuple(m):
    return int(m.combo.kind), m.combo.value, m.combo.size, [int(c) for c in m.cards]


def real_world(d, version):
    import guandan_core as core
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
        [(s, _tuple(m)) for s, m in d.history], [list(p) for p in d.played], version)


def one_deal(args):
    rec, model = args
    import torch
    torch.set_num_threads(1)
    from guandan.review import move_from_record, start_deal
    from guandan.rl.features import encode_actions, encode_state
    from guandan.rl.policy import load_policy, policy_step
    from guandan.rl.search import rollout
    actor = load_policy(model)
    v = actor.version
    rng = np.random.default_rng(0)
    d = start_deal(rec)
    out = []
    human = rec["humans"][0]
    for i, entry in enumerate(rec["moves"]):
        seat = entry[0]
        m = move_from_record(entry)
        role = "human" if seat == human else "AI partner of the human" if seat == (human + 2) % 4 else "AI opponent"
        if True:
            legal = d.legal()
            if len(legal) > 1:
                obs = d.observation(seat)
                p = policy_step(actor, encode_state(obs, v), encode_actions(obs, v), rng, greedy=True)[2]
                idx = next((j for j, x in enumerate(legal) if x.combo == m.combo and sorted(x.cards) == sorted(m.cards)), None)
                if idx is not None:
                    cands = sorted(set([idx] + [int(j) for j in np.argsort(-p)[:5]]))
                    w = real_world(d, v)
                    sims = []
                    for j in cands:
                        c = w.copy()
                        c.play_index(j)
                        sims.append(c)
                    rollout(sims, actor, v, rng)
                    me = seat % 2
                    vals = {}
                    for j, c in zip(cands, sims):
                        win, up = c.result()
                        vals[j] = up if win == me else -up
                    counts = [len(h) for h in d.hands]
                    opp_min = min(counts[(seat + 1) % 4] or 99, counts[(seat + 3) % 4] or 99)
                    out.append({
                        "seat": seat, "role": role, "move": i, "kind": KIND[int(m.combo.kind)], "regret": max(vals.values()) - vals[idx],
                        "leading": d.leading, "partner_table": d.table_seat is not None and d.table_seat == (seat + 2) % 4,
                        "opp_min": opp_min, "hand": counts[seat], "total": sum(counts), "p_chosen": float(p[idx]),
                        "best": KIND[int(legal[max(vals, key=vals.get)].combo.kind)], "bomb_avail": any(x.combo.is_bomb for x in legal),
                    })
        d.play(m)
    # what the AI team held at the end
    from guandan.rl.plan import min_sets
    left = {s: (len(d.hands[s]), min_sets(d.hands[s], d.level) if d.hands[s] else 0,
                sum(1 for x in d.hands[s] if False)) for s in range(4)}
    bombs_left = {}
    for s in range(4):
        cnt = collections.Counter(c % 54 % 13 for c in d.hands[s] if c % 54 < 52)
        bombs_left[s] = sum(1 for k in cnt.values() if k >= 4)
    return {"human": human, "finished": list(d.finished), "left": left, "bombs_left": bombs_left, "decisions": out,
            "result": rec["result"]}


def table(rows, title, keyf):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[keyf(r)].append(r["regret"])
    total = sum(r["regret"] for r in rows)
    print(f"\n{title}")
    print(f"  {'':28s} {'decisions':>9s} {'mean regret':>11s} {'regret>=1':>9s} {'share of total regret':>22s}")
    for k, xs in sorted(groups.items(), key=lambda kv: -sum(kv[1])):
        x = np.array(xs)
        print(f"  {str(k):28s} {len(x):9d} {x.mean():11.3f} {np.mean(x >= 1):9.1%} {x.sum() / total:22.1%}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--model", default="runs/ppo/model.pt")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--assisted", action="store_true", help="include deals where the human used move suggestions")
    a = ap.parse_args()
    recs = [json.loads(r) for (r,) in sqlite3.connect(a.db).execute("SELECT record FROM deals ORDER BY id")]
    recs = [r for r in recs if len(r["humans"]) == 1 and (a.assisted or not r["assisted"])]
    with ProcessPoolExecutor(a.procs) as ex:
        res = list(ex.map(one_deal, [(r, a.model) for r in recs], chunksize=2))
    # --- how deals end
    ai_levels, order_kind = [], collections.Counter()
    leftovers = collections.defaultdict(list)
    for r in res:
        h = r["human"]
        win, up = r["result"]["win_team"], r["result"]["up"]
        ai_levels.append(up if win != team(h) else -up)
        fin = r["finished"]
        who = ["human" if s == h else "human's partner" if s == (h + 2) % 4 else "AI" for s in fin]
        order_kind[(win == team(h), up)] += 1
        for s in range(4):
            if team(s) != team(h):
                leftovers["AI team seats (all deals)"].append(r["left"][s][0])
                if win == team(h):
                    leftovers["AI team seats (deals the AI lost)"].append(r["left"][s][0])
                    leftovers["  of which fewest sets still to go"].append(r["left"][s][1])
                    leftovers["  bombs still unplayed in hand"].append(r["bombs_left"][s])
    x = np.array(ai_levels)
    print(f"{len(res)} deals. AI team: {x.mean():+.2f} ± {x.std(ddof=1) / np.sqrt(len(x)):.2f} levels per deal, wins {np.mean(x > 0):.0%}")
    print("\nHow deals ended (human team wins / loses, levels): " + ", ".join(
        f"{'human' if w else 'AI'} +{u}: {n}" for (w, u), n in sorted(order_kind.items(), key=lambda kv: (not kv[0][0], -kv[0][1]))))
    for k, xs in leftovers.items():
        print(f"  {k:42s} mean {np.mean(xs):.2f}")
    rows = [dec for r in res for dec in r["decisions"]]
    roles = ["human", "AI partner of the human", "AI opponent"]
    print(f"\n{len(rows)} decisions scored (the same measure for people and AIs, so the differences are meaningful; the absolute level is inflated:")
    print("  the best of six playouts always beats the move played).")
    print(f"  {'':26s} {'decisions':>9s} {'mean regret':>11s} {'regret>=2':>9s}")
    for ro in roles:
        x = np.array([d["regret"] for d in rows if d["role"] == ro])
        se = x.std(ddof=1) / np.sqrt(len(x))
        print(f"  {ro:26s} {len(x):9d} {x.mean():7.3f} ± {se:.3f} {np.mean(x >= 2):9.1%}")

    def compare(title, keyf):
        groups = collections.defaultdict(lambda: collections.defaultdict(list))
        for d in rows:
            groups[keyf(d)][d["role"]].append(d["regret"])
        print(f"\n{title}   (mean regret [decisions]: human | AI partner | AI opponent; last column = AI average minus human)")
        for k, g in sorted(groups.items(), key=lambda kv: -sum(len(v) for v in kv[1].values())):
            cells, means = [], {}
            for ro in roles:
                v = g.get(ro, [])
                means[ro] = np.mean(v) if v else float("nan")
                cells.append(f"{means[ro]:6.2f} [{len(v):4d}]")
            ai = np.mean([x for ro in roles[1:] for x in g.get(ro, [])]) if any(g.get(ro) for ro in roles[1:]) else float("nan")
            print(f"  {str(k):26s} " + " | ".join(cells) + f"   {ai - means['human']:+.2f}")

    compare("By the move played", lambda d: d["kind"])
    compare("By situation", lambda d: ("leading" if d["leading"] else "following partner's play" if d["partner_table"] else "following an opponent"))
    compare("By the opponents' smallest hand", lambda d: "<=3 cards" if d["opp_min"] <= 3 else "4-8 cards" if d["opp_min"] <= 8 else "9+ cards")
    compare("By the player's own hand size", lambda d: "<=6 cards" if d["hand"] <= 6 else "7-14 cards" if d["hand"] <= 14 else "15+ cards")
    compare("By game phase (cards left in all hands)", lambda d: "<=24" if d["total"] <= 24 else "25-60" if d["total"] <= 60 else "61+")
    compare("Passing while holding a bomb that could be played", lambda d: "bomb available: " + ("passed" if d["kind"] == "pass" else "played something else" if not d["bomb_avail"] else "played " + d["kind"]) if d["bomb_avail"] else "no bomb available")
    ai = [d for d in rows if d["role"] != "human" and d["regret"] >= 2]
    print("\nAI decisions with regret >= 2: what it played -> the better move")
    tab = collections.Counter(f"{d['kind']} -> {d['best']}" for d in ai)
    for k, n in tab.most_common(10):
        print(f"  {k:28s} {n}")


if __name__ == "__main__":
    main()
