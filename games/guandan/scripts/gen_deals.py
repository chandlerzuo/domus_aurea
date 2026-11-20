"""Generate self-play deals for the sequence guesser: the starting hands and every play and pass, in shards.

  python scripts/gen_deals.py --actor runs/all3/model.pt --out runs/seq/data --deals 200000 --workers 5

Each shard (npz): hands0 (N, 4, 27) card ids, level (N,), seat/kind (N, T), cards (N, T, 8) card ids padded with -1, multi (N, T) whether the
mover had a real choice (more than one legal move), length (N,).
"""
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

T_MAX = 192


def gen(seed: int, n_deals: int, actor_path: str, out: str, width: int = 32):
    import torch
    torch.set_num_threads(1)
    import guandan_core as core
    from guandan.agents import HeuristicAgent
    from guandan.rl import fast
    from guandan.rl.dmc import random_match
    from guandan.rl.policy import load_policy
    actor = load_policy(actor_path)
    rng = np.random.default_rng(seed)
    v = actor.version
    rec = {k: [] for k in ("hands0", "level", "seat", "kind", "cards", "multi", "length")}
    tables, started = [], 0

    def new_table():
        m = random_match(rng, 0.75)
        d = m.new_deal()
        for t in m.pending_returns:
            m.give_return(t.receiver, HeuristicAgent(0).choose_return(d.hands[t.receiver], d.level))
        return {"rs": fast.rs_from_deal(d), "h0": [sorted(int(c) for c in h) for h in d.hands], "level": d.level, "multi": []}

    while tables or started < n_deals:
        while len(tables) < width and started < n_deals:
            tables.append(new_table())
            started += 1
        live = []
        for t in tables:
            rs = t["rs"]
            while not rs.done and rs.n_legal() == 1:
                rs.play_index(0)
                t["multi"].append(False)
            if not rs.done:
                live.append(t)
        if live:
            S, A, n = core.batch_encode([t["rs"] for t in live], v)
            with torch.no_grad():
                logits, _ = fast.policy_logits(actor, S, A, n)
            idx, _, _ = fast.sample_rows(logits, n, rng)
            for t in live:
                t["multi"].append(True)
            core.batch_play([t["rs"] for t in live], [int(i) for i in idx])
        still = []
        for t in tables:
            if not t["rs"].done:
                still.append(t)
                continue
            hist = t["rs"].history
            if len(hist) > T_MAX or len(hist) != len(t["multi"]):
                continue
            seat = np.full(T_MAX, -1, np.int8)
            kind = np.zeros(T_MAX, np.int8)
            cards = np.full((T_MAX, 8), -1, np.int16)
            multi = np.zeros(T_MAX, bool)
            for i, (s, m) in enumerate(hist):
                seat[i], kind[i] = s, m[0]
                cards[i, :len(m[3])] = m[3]
            multi[:len(hist)] = t["multi"]
            for k, x in zip(rec, (np.array(t["h0"], np.int16), t["level"], seat, kind, cards, multi, len(hist))):
                rec[k].append(x)
        tables = still
    np.savez_compressed(Path(out) / f"shard_{seed}.npz", **{k: np.stack(v_) for k, v_ in rec.items()})
    return len(rec["level"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--actor", default="runs/all3/model.pt")
    ap.add_argument("--out", default="runs/seq/data")
    ap.add_argument("--deals", type=int, default=200_000)
    ap.add_argument("--per-shard", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1000)
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    shards = a.deals // a.per_shard
    with ProcessPoolExecutor(a.workers) as ex:
        done = 0
        for n in ex.map(gen, [a.seed + k for k in range(shards)], [a.per_shard] * shards, [a.actor] * shards, [a.out] * shards):
            done += n
            print(f"{done} deals", flush=True)


if __name__ == "__main__":
    main()
