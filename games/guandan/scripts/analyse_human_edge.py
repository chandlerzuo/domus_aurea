"""Where does a human beat the AI? The human's choices that differ from the model's, and what they were worth.

  python scripts/analyse_human_edge.py --db games.db --player Blackstar [--model runs/ppo/model.pt] [--rollouts 12]

At every decision of the chosen human (deals without move suggestions) where the human's move is not the model's top choice,
both moves are valued by playing the rest of the deal out several times with the real hidden hands (the model plays every seat,
sampling its moves). The gain is the human move's value minus the model move's value, in levels for the human's team, so a positive
gain means the human's deviation was better. Gains are grouped by kind of deviation and by situation: a group with a clearly
positive mean is something the human does that the model does not, i.e. a weakness to train away.
"""
import argparse
import collections
import json
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

KIND = {0: "pass", 1: "single", 2: "pair", 3: "triple", 4: "full house", 5: "straight", 6: "tube", 7: "plate", 8: "bomb",
        9: "straight flush", 10: "joker bomb"}


def rollouts(sims, actor, version, rng):
    """Play every deal to the end, sampling the model's moves."""
    import torch
    import guandan_core as core
    from guandan.rl import fast
    live = sims
    while True:
        nxt = []
        for s in live:
            while not s.done and s.n_legal() == 1:
                s.play_index(0)
            if not s.done:
                nxt.append(s)
        live = nxt
        if not live:
            return
        S, A, n = core.batch_encode(live, version)
        with torch.no_grad():
            logits, _ = fast.policy_logits(actor, S, A, n)
        idx, _, _ = fast.sample_rows(logits, n, rng, greedy=False)
        core.batch_play(live, [int(i) for i in idx])


def one_deal(args):
    rec, model, n_roll, human = args
    import torch
    torch.set_num_threads(1)
    from analyse_failures import real_world
    from guandan.game import team
    from guandan.review import move_from_record, start_deal
    from guandan.rl.features import encode_actions, encode_state
    from guandan.rl.policy import load_policy, policy_step
    actor = load_policy(model)
    v = actor.version
    rng = np.random.default_rng(1)
    seat = next(s for s in rec["humans"] if rec["names"][s] == human)
    d = start_deal(rec)
    out = []
    for i, entry in enumerate(rec["moves"]):
        m = move_from_record(entry)
        if entry[0] == seat:
            legal = d.legal()
            if len(legal) > 1:
                obs = d.observation(seat)
                p = policy_step(actor, encode_state(obs, v), encode_actions(obs, v), rng, greedy=True)[2]
                top = int(np.argmax(p))
                idx = next((j for j, x in enumerate(legal) if x.combo == m.combo and sorted(x.cards) == sorted(m.cards)), None)
                if idx is not None and idx != top:
                    w = real_world(d, v)
                    sims, owner = [], []
                    for k, j in enumerate((idx, top)):
                        for _ in range(n_roll):
                            c = w.copy()
                            c.play_index(j)
                            sims.append(c)
                            owner.append(k)
                    rollouts(sims, actor, v, rng)
                    tot, cnt = [0.0, 0.0], [0, 0]
                    for c, k in zip(sims, owner):
                        win, up = c.result()
                        tot[k] += up if win % 2 == seat % 2 else -up
                        cnt[k] += 1
                    from guandan.cards import ctype, value
                    from guandan.rl.plan import min_sets
                    sets_now = min_sets(d.hands[seat], d.level)

                    def after(mv):
                        rest = list(d.hands[seat])
                        for c in mv.cards:
                            rest.remove(c)
                        return min_sets(rest, d.level) - sets_now

                    strength = lambda mv: float(np.mean([value(ctype(c), d.level) for c in mv.cards])) if mv.cards else -1.0
                    counts = [len(h) for h in d.hands]
                    opp_min = min(counts[(seat + 1) % 4] or 99, counts[(seat + 3) % 4] or 99)
                    out.append({
                        "gain": tot[0] / cnt[0] - tot[1] / cnt[1], "human": KIND[int(m.combo.kind)], "model": KIND[int(legal[top].combo.kind)],
                        "leading": d.leading, "partner_table": d.table_seat is not None and d.table_seat == (seat + 2) % 4,
                        "opp_min": opp_min, "hand": counts[seat], "total": sum(counts), "p_human": float(p[idx]), "p_top": float(p[top]),
                        "human_bomb": m.combo.is_bomb, "model_bomb": legal[top].combo.is_bomb,
                        "human_cards": len(m.cards), "model_cards": len(legal[top].cards),
                        "dsets_h": after(m), "dsets_m": after(legal[top]), "str_h": strength(m), "str_m": strength(legal[top]),
                        "sets_now": sets_now})
        d.play(m)
    return out, sum(1 for e in rec["moves"] if e[0] == seat)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--player", required=True)
    ap.add_argument("--model", default="runs/ppo/model.pt")
    ap.add_argument("--rollouts", type=int, default=12)
    ap.add_argument("--procs", type=int, default=12)
    a = ap.parse_args()
    recs = [json.loads(r) for (r,) in sqlite3.connect(a.db).execute("SELECT record FROM deals ORDER BY id")]
    recs = [r for r in recs if len(r["humans"]) == 1 and not r["assisted"] and r["names"][r["humans"][0]] == a.player]
    with ProcessPoolExecutor(a.procs) as ex:
        res = list(ex.map(one_deal, [(r, a.model, a.rollouts, a.player) for r in recs], chunksize=1))
    rows = [d for out, _ in res for d in out]
    total_dec = sum(n for _, n in res)
    g = np.array([d["gain"] for d in rows])
    print(f"{len(recs)} deals of {a.player}; {total_dec} of their plays, {len(rows)} ({len(rows) / total_dec:.0%}) differ from the model's top move")
    print(f"mean gain of the human's deviation over the model's move: {g.mean():+.3f} ± {g.std(ddof=1) / np.sqrt(len(g)):.3f} levels "
          f"(per deal: {g.sum() / len(recs):+.2f}); the human's move was better in {np.mean(g > 0):.0%} of them")

    def table(title, keyf, minn=25):
        groups = collections.defaultdict(list)
        for d in rows:
            groups[keyf(d)].append(d["gain"])
        print(f"\n{title}")
        print(f"  {'':44s} {'n':>5s} {'mean gain':>10s} {'± se':>6s} {'total':>7s}")
        for k, xs in sorted(groups.items(), key=lambda kv: -sum(kv[1])):
            if len(xs) >= minn:
                x = np.array(xs)
                print(f"  {str(k):44s} {len(x):5d} {x.mean():+10.3f} {x.std(ddof=1) / np.sqrt(len(x)):6.3f} {x.sum():+7.1f}")

    table("What the human did differently (human move vs model move)",
          lambda d: ("human passes, model plays" if d["human"] == "pass" else "human plays, model passes" if d["model"] == "pass"
                     else "both play: human plays more cards" if d["human_cards"] > d["model_cards"]
                     else "both play: human plays fewer cards" if d["human_cards"] < d["model_cards"] else "both play: same size, different cards"))
    table("Bombs", lambda d: ("human bombs, model does not" if d["human_bomb"] and not d["model_bomb"]
                              else "model bombs, human does not" if d["model_bomb"] and not d["human_bomb"]
                              else "both bomb" if d["human_bomb"] else "neither bombs"))
    table("Situation", lambda d: ("leading" if d["leading"] else "following partner's play" if d["partner_table"] else "following an opponent"))
    table("Opponents' smallest hand", lambda d: "<=3 cards" if d["opp_min"] <= 3 else "4-8 cards" if d["opp_min"] <= 8 else "9+ cards")
    table("Human's own hand", lambda d: "<=6 cards" if d["hand"] <= 6 else "7-14 cards" if d["hand"] <= 14 else "15+ cards")
    table("Move kinds (human -> model)", lambda d: f"{d['human']} -> {d['model']}", minn=30)
    lead = [d for d in rows if d["leading"]]
    print(f"\n--- the {len(lead)} leads where the human chose differently from the model ---")
    for title, keyf in (
        ("how the human's lead changes the plan (fewest sets after the move) compared with the model's lead",
         lambda d: ("human's lead shortens the plan, model's does not" if d["dsets_h"] < d["dsets_m"] else
                    "model's lead shortens the plan more" if d["dsets_h"] > d["dsets_m"] else "same effect on the plan")),
        ("strength of the lead (average card value; human minus model)",
         lambda d: "human leads higher cards" if d["str_h"] > d["str_m"] + 1 else "human leads lower cards" if d["str_h"] < d["str_m"] - 1 else "similar strength"),
        ("size of the lead", lambda d: "human leads fewer cards" if d["human_cards"] < d["model_cards"] else
         "human leads more cards" if d["human_cards"] > d["model_cards"] else "same number of cards"),
        ("what the human leads (human -> model)", lambda d: f"{d['human']} -> {d['model']}"),
        ("number of sets in the human's hand", lambda d: f"{min(d['sets_now'], 9)} sets"),
    ):
        groups = collections.defaultdict(list)
        for d in lead:
            groups[keyf(d)].append(d["gain"])
        print(f"\n{title}")
        for k, xs in sorted(groups.items(), key=lambda kv: -sum(kv[1])):
            if len(xs) >= 15:
                x = np.array(xs)
                print(f"  {str(k):52s} n={len(x):4d}  mean gain {x.mean():+.3f} ± {x.std(ddof=1) / np.sqrt(len(x)):.3f}")
    sure = [d for d in rows if d["p_top"] - d["p_human"] > 0.4]
    if sure:
        x = np.array([d["gain"] for d in sure])
        print(f"\nWhen the model was confident (top move > 0.4 more likely than the human's): {len(x)} decisions, mean gain {x.mean():+.3f} ± {x.std(ddof=1) / np.sqrt(len(x)):.3f}")


if __name__ == "__main__":
    main()
