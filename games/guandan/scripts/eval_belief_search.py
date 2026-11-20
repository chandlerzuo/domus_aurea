"""A fast, low-noise test of hidden-hand sampling for the search, on positions from recorded games.

  python scripts/eval_belief_search.py --db games.db --positions 2500 \
      --variants uniform side:1 bnet:runs/belief/b2.pt:1 bnet:runs/belief/b2.pt:2 oracle

For every position (a decision of any seat in a recorded deal) each variant runs the same search (the model's top candidate moves,
32 sampled hidden hands each, played out by the model) and picks a move. The picked move is then valued with the REAL hidden hands:
the rest of the deal is played out many times (the model plays all seats, sampling) and the result for the player's team is
averaged. Reported per variant: the average true value of its pick minus the true value of the model's own top move on the
same position (so +0.1 means the search with this sampling gains 0.1 level per decision), with a paired standard error.
Variants:  uniform = hands dealt at random;  side:P = weighted by the policy's belief head, exponent P;
           bnet:PATH:P = weighted by a dedicated guesser (rl/belief.py);  oracle = the true hands (an upper bound for any guesser).
Extra keys after the exponent, e.g. bnet:PATH:1:mix=0.3, blend the guesser with the uniform deal.
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
    rec, model, variants, n_world, n_truth, per_deal, seed = args
    import torch
    torch.set_num_threads(1)
    import guandan_core as core  # noqa: F401
    from analyse_failures import real_world
    from guandan.review import move_from_record, start_deal
    from guandan.rl.features import encode_actions, encode_state
    from guandan.rl.policy import load_policy, policy_step
    from guandan.rl.search import belief_probs, sample_world, rollout
    from guandan.rl.belief import belief_from_net, load_belief
    from analyse_human_edge import rollouts as sampled_rollouts
    actor = load_policy(model)
    v = actor.version
    rng = np.random.default_rng(seed)
    nets = {}
    from guandan.server.zh import card_zh
    zh_ids = {}
    for c in range(108):
        zh_ids.setdefault(card_zh(c), []).append(c)
    known_all = []                                    # (holder seat, card id) from the public tribute at the start of the deal
    for t in rec["tributes"]:
        for who, text in ((t["receiver"], t["card"]), (t["payer"], t["returned"])):
            if text:
                hand0 = rec["hands"][who]
                cid = next((c for c in zh_ids.get(text, []) if c in hand0), None)
                if cid is not None:
                    known_all.append((who, cid))
    d = start_deal(rec)
    moves = rec["moves"]
    pick_at = set(rng.choice(len(moves), size=min(per_deal, len(moves)), replace=False).tolist())
    out = []
    for i, entry in enumerate(moves):
        if i in pick_at:
            legal = d.legal()
            if len(legal) > 1:
                seat = d.to_act
                obs = d.observation(seat)
                p = policy_step(actor, encode_state(obs, v), encode_actions(obs, v), rng, greedy=True)[2]
                order = [int(j) for j in np.argsort(-p)]
                cand = [order[0]] + [j for j in order[1:4] if p[j] >= 0.03]
                if len(cand) >= 2:
                    truth_w = real_world(d, v)
                    picks = {}
                    for name in variants:
                        use_known = name.endswith("+known")
                        name_ = name[:-6] if use_known else name
                        obs_k = dict(obs, known=known_all) if use_known else obs
                        kind, *rest = name_.split(":")
                        if kind == "oracle":
                            worlds = [truth_w for _ in range(1)]
                        else:
                            if kind == "uniform":
                                bel, power, mix = None, 0.0, 0.0
                            elif kind == "side":
                                bel, power, mix = belief_probs(actor, obs_k), float(rest[0]), 0.0
                            else:
                                path = rest[0]
                                if path not in nets:
                                    nets[path] = load_belief(path)
                                bel, power = belief_from_net(nets[path], obs_k), float(rest[1])
                                mix = float(dict(x.split("=") for x in rest[2:]).get("mix", 0)) if len(rest) > 2 else 0.0
                            if bel is not None and mix > 0:
                                bel = (1 - mix) * bel + mix * bel.mean(axis=0, keepdims=True)
                            worlds = [sample_world(obs_k, rng, v, bel, power) for _ in range(n_world)]
                        sims, owner = [], []
                        for w in worlds:
                            for k, j in enumerate(cand):
                                c = w.copy()
                                c.play_index(j)
                                sims.append(c)
                                owner.append(k)
                        rollout(sims, actor, v, rng)
                        tot, cnt = np.zeros(len(cand)), np.zeros(len(cand))
                        me = seat % 2
                        for c, k in zip(sims, owner):
                            win, up = c.result()
                            tot[k] += up if win == me else -up
                            cnt[k] += 1
                        val = tot / cnt
                        best = int(np.argmax(val))
                        picks[name] = cand[best] if val[best] - val[0] > 0 else cand[0]
                    # true value of every distinct pick (and of the model's top move) with the real hands
                    need = sorted(set(picks.values()) | {cand[0]})
                    sims, owner = [], []
                    for j in need:
                        for _ in range(n_truth):
                            c = truth_w.copy()
                            c.play_index(j)
                            sims.append(c)
                            owner.append(j)
                    sampled_rollouts(sims, actor, v, rng)
                    tv = {j: 0.0 for j in need}
                    for c, j in zip(sims, owner):
                        win, up = c.result()
                        tv[j] += (up if win == seat % 2 else -up) / n_truth
                    out.append({name: tv[picks[name]] - tv[cand[0]] for name in variants} | {"_changed": {name: picks[name] != cand[0] for name in variants}})
        d.play(move_from_record(entry))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True)
    ap.add_argument("--model", default="runs/ppo/model.pt")
    ap.add_argument("--variants", nargs="+", required=True)
    ap.add_argument("--positions", type=int, default=2500)
    ap.add_argument("--worlds", type=int, default=32)
    ap.add_argument("--truth", type=int, default=24, help="playouts with the real hands per valued move")
    ap.add_argument("--per-deal", type=int, default=40, help="decisions tried per recorded deal (some are skipped)")
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args()
    recs = [json.loads(r) for (r,) in sqlite3.connect(a.db).execute("SELECT record FROM deals ORDER BY id")]
    per_deal = a.per_deal
    with ProcessPoolExecutor(a.procs) as ex:
        res = list(ex.map(one, [(r, a.model, a.variants, a.worlds, a.truth, per_deal, a.seed + k) for k, r in enumerate(recs)], chunksize=2))
    rows = [x for r in res for x in r][:a.positions]
    print(f"{len(rows)} positions from {len(recs)} recorded deals; gain over the model's own top move, in levels per decision")
    base = None
    for name in a.variants:
        g = np.array([r[name] for r in rows])
        ch = np.mean([r["_changed"][name] for r in rows])
        extra = ""
        if base is not None:
            dd = g - base
            extra = f"   vs {a.variants[0]}: {dd.mean():+.4f} ± {dd.std(ddof=1) / np.sqrt(len(dd)):.4f}"
        print(f"  {name:48s} {g.mean():+.4f} ± {g.std(ddof=1) / np.sqrt(len(g)):.4f}   changes the move in {ch:.0%}{extra}")
        if base is None:
            base = g


if __name__ == "__main__":
    main()
