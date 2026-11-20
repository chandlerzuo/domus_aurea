"""Train the sequence guesser (guandan/rl/seqbelief.py) on generated deals (scripts/gen_deals.py).

  python scripts/train_seqbelief.py --data runs/seq/data --out runs/seq/s1.pt --steps 60000

Each training example is a moment in a deal where the mover had a real choice: the model sees the plays so far and the mover's own
hand, and must say which cards each of the other three players holds. The last shard is held out (never trained on).
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch import nn  # noqa: E402

from guandan.rl.dmc import _device  # noqa: E402
from guandan.rl.seqbelief import N_CARDS, N_KIND, T_MAX, SeqBelief, save_seq  # noqa: E402


def load(paths, dev):
    parts = [np.load(p) for p in paths]
    cat = lambda k: np.concatenate([z[k] for z in parts])
    d = {"hands0": cat("hands0"), "level": cat("level"), "seat": cat("seat"), "kind": cat("kind"), "cards": cat("cards"), "multi": cat("multi"), "length": cat("length")}
    n = len(d["level"])
    h0 = np.zeros((n, 4, N_CARDS), np.float32)
    for s in range(4):
        np.put_along_axis(h0[:, s], d["hands0"][:, s].astype(np.int64), 1.0, axis=1)
    T = int(d["length"].max())
    t = {"h0": torch.from_numpy(h0).to(dev), "level": torch.from_numpy(d["level"].astype(np.int64)).to(dev),
         "seat": torch.from_numpy(d["seat"][:, :T].astype(np.int64)).to(dev), "kind": torch.from_numpy(d["kind"][:, :T].astype(np.int64)).to(dev),
         "cards": torch.from_numpy(d["cards"][:, :T].astype(np.int64)).to(dev)}
    deal, mv = np.nonzero(d["multi"][:, :T])
    return t, torch.from_numpy(deal).to(dev), torch.from_numpy(mv).to(dev)


def batch(t, di, mv, dev):
    """Model inputs and targets for examples (deal di, move mv)."""
    B = len(di)
    T = int(mv.max().item()) + 1
    seat = t["seat"][di, :T]                                  # (B, T) absolute seats
    kind = t["kind"][di, :T]
    cards = t["cards"][di, :T]                                # (B, T, 8), -1 = none
    a = seat[torch.arange(B, device=dev), mv]                 # the mover = the player whose view this is
    valid = torch.arange(T, device=dev)[None] < mv[:, None]
    bits = torch.zeros(B, T, N_CARDS + 1, device=dev).scatter_(2, torch.where(cards < 0, torch.full_like(cards, N_CARDS), cards), 1.0)[:, :, :N_CARDS]
    bits = bits * valid[..., None]
    rel = (seat - a[:, None]) % 4
    rel_oh = nn.functional.one_hot(rel.clamp(min=0), 4).float() * valid[..., None]
    kind_oh = nn.functional.one_hot(kind.clamp(min=0), N_KIND).float() * valid[..., None]
    tokens = torch.cat([bits, rel_oh, kind_oh], -1)
    # who has played what so far, by absolute seat
    seat_oh = nn.functional.one_hot(seat.clamp(min=0), 4).float() * valid[..., None]        # (B, T, 4)
    played = torch.einsum("bts,btc->bsc", seat_oh, bits).clamp(max=1)                       # (B, 4, 108)
    hand = (t["h0"][di] - played).clamp(min=0)                                              # (B, 4, 108): hands before this move
    order = (a[:, None] + torch.arange(4, device=dev)[None]) % 4                            # (B, 4): me, next, partner, previous
    take = lambda x: torch.gather(x, 1, order[..., None].expand(-1, -1, N_CARDS))
    hand_r, played_r = take(hand), take(played)
    unseen = 1 - (hand_r[:, 0] + played_r.sum(1)).clamp(max=1)
    counts = hand_r[:, 1:].sum(-1) / 27.0
    level = nn.functional.one_hot(t["level"][di], 13).float()
    state = torch.cat([hand_r[:, 0], unseen, played_r[:, 1], played_r[:, 2], played_r[:, 3], counts, level], -1)
    # target: the other three players' hands as two bits per card type (at least one copy, both copies)
    h = hand_r[:, 1:]                                                                       # (B, 3, 108)
    cnt = h[:, :, :54] + h[:, :, 54:]
    target = torch.stack([(cnt >= 1).float(), (cnt >= 2).float()], -1).reshape(B, 3 * 108)
    return tokens, mv, state, target


def evaluate(net, t, deal, mv, dev, n=20000):
    net.eval()
    g = torch.Generator().manual_seed(0)
    pick = torch.randperm(len(deal), generator=g)[:n].to(dev)
    tot_bce, tot_n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(pick), 1000):
            ix = pick[i:i + 1000]
            tok, nt, st, y = batch(t, deal[ix], mv[ix], dev)
            logits = net(tok, nt, st)
            tot_bce += nn.functional.binary_cross_entropy_with_logits(logits, y, reduction="sum").item()
            tot_n += y.numel()
    net.train()
    return tot_bce / tot_n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="runs/seq/data")
    ap.add_argument("--out", default="runs/seq/s1.pt")
    ap.add_argument("--steps", type=int, default=60000)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--d", type=int, default=256)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--max-shards", type=int, default=0)
    a = ap.parse_args()
    dev = _device("auto")
    shards = sorted(Path(a.data).glob("shard_*.npz"))
    if a.max_shards:
        shards = shards[:a.max_shards]
    train_t, tr_deal, tr_mv = load(shards[:-1], dev)
    hold_t, ho_deal, ho_mv = load(shards[-1:], dev)
    print(f"{len(shards) - 1} training shards: {len(train_t['level'])} deals, {len(tr_deal):,} decisions; held out {len(ho_deal):,}; device {dev}", flush=True)
    net = SeqBelief(a.d, a.layers).to(dev)
    print(f"{sum(p.numel() for p in net.parameters()) / 1e6:.1f}M parameters", flush=True)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=a.steps, pct_start=0.03, anneal_strategy="cos", final_div_factor=30)
    t0 = time.time()
    for step in range(1, a.steps + 1):
        ix = torch.randint(0, len(tr_deal), (a.batch,), device=dev)
        tok, nt, st, y = batch(train_t, tr_deal[ix], tr_mv[ix], dev)
        loss = nn.functional.binary_cross_entropy_with_logits(net(tok, nt, st), y)
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        if step % 1000 == 0 or step == a.steps:
            bce = evaluate(net, hold_t, ho_deal, ho_mv, dev)
            print(f"step {step:6d}  {time.time() - t0:6.0f}s  train loss {loss.item():.4f}  held-out BCE {bce:.4f}", flush=True)
            save_seq(net, a.out, steps=step)


if __name__ == "__main__":
    main()
