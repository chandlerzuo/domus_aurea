"""How well does the model guess the hidden hands? Measured on recorded games (the real hands are known).

  python scripts/belief_quality.py --db games.db --model runs/ppo/model.pt

At every decision of every seat the model's belief head gives, for each of the 54 card types and each of the three other players,
the chance that player holds it. The score compares that with a model that knows nothing but the counts: for each hidden card
the log-probability given to its true holder (uniform = log(1/3) = -1.099; higher is better), by game stage, and the top-1
accuracy of "who holds this card" among the three players.
"""
import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from guandan.cards import N_TYPES, ctype  # noqa: E402
from guandan.review import move_from_record, start_deal  # noqa: E402
from guandan.rl.features import encode_state  # noqa: E402
from guandan.rl.policy import load_policy  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--model", default="runs/ppo/model.pt")
    ap.add_argument("--max-deals", type=int, default=120)
    ap.add_argument("--seq-model", help="score a sequence guesser (rl/seqbelief.py)")
    ap.add_argument("--belief-model", help="score a dedicated hidden-hand guesser (rl/belief.py) instead of the policy's belief head")
    a = ap.parse_args()
    actor = load_policy(a.model)
    v = actor.version
    bnet = snet = None
    if a.seq_model:
        from guandan.rl.seqbelief import load_seq
        snet = load_seq(a.seq_model)
    if a.belief_model:
        from guandan.rl.belief import load_belief
        bnet = load_belief(a.belief_model)
    recs = [json.loads(r) for (r,) in sqlite3.connect(a.db).execute("SELECT record FROM deals ORDER BY id")][-a.max_deals:]
    stats = collections.defaultdict(lambda: [0.0, 0.0, 0, 0.0, 0.0])      # stage -> [sum log p, top-1 hits, n cards, same for the counts-only guess]
    for rec in recs:
        d = start_deal(rec)
        for i, entry in enumerate(rec["moves"]):
            seat = d.to_act
            obs = d.observation(seat)
            with torch.no_grad():
                if snet is not None:
                    from guandan.rl.seqbelief import belief_from_seq
                    prob = belief_from_seq(snet, obs)
                elif bnet is not None:
                    prob = torch.sigmoid(bnet(torch.from_numpy(encode_state(obs, bnet.version)).float()[None]))[0].numpy().reshape(3, -1)[:, 0::2]
                else:
                    hs = actor.state(torch.from_numpy(encode_state(obs, v)).float()[None])
                    prob = torch.sigmoid(actor.belief(hs))[0].numpy().reshape(3, -1)[:, 0::2]       # (3 others, 54 types): holds at least one copy
            hidden = [(k, c) for k in range(3) for c in d.hands[(seat + 1 + k) % 4]]
            stage = "61+ cards on the table" if sum(map(len, d.hands)) > 60 else "31-60" if sum(map(len, d.hands)) > 30 else "<=30"
            sizes = np.array([len(d.hands[(seat + 1 + k) % 4]) for k in range(3)], dtype=float) + 1e-9
            share = sizes / sizes.sum()                      # the counts-only guess: a hidden card is anywhere in proportion to hand sizes
            for k, c in hidden:
                t = ctype(c)
                stats[stage][3] += float(np.log(share[k]))
                stats[stage][4] += float(np.argmax(share) == k)
                col = prob[:, t] + 1e-4
                stats[stage][0] += float(np.log(col[k] / col.sum()))
                stats[stage][1] += float(np.argmax(col) == k)
                stats[stage][2] += 1
            d.play(move_from_record(entry))
    print(f"{a.model}: {len(recs)} deals")
    print(f"  {'stage':26s} {'cards':>8s} | {'model: log p':>12s} {'top-1':>7s} | {'hand sizes only: log p':>22s} {'top-1':>7s} | {'what the model adds':>19s}")
    for st in ("61+ cards on the table", "31-60", "<=30"):
        s, h, n, bs, bh = stats[st]
        print(f"  {st:26s} {n:8d} | {s / n:12.3f} {h / n:7.1%} | {bs / n:22.3f} {bh / n:7.1%} | {s / n - bs / n:+19.3f}")


if __name__ == "__main__":
    main()
