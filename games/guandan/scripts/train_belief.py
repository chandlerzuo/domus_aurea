"""Train the dedicated hidden-hand guesser (guandan/rl/belief.py) on fresh self-play, streaming (each position is used once).

  python scripts/train_belief.py --actor runs/all3/model.pt --out runs/belief/b1.pt --decisions 6000000

The actor (feature version 5) plays; every decision of every seat becomes a training example: the acting player's features and the
other three hands. A held-out set from other seeds is scored every few steps next to the actor's own belief head, so the gain over
the side head is measured on the same positions.
"""
import argparse
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch import nn  # noqa: E402

from guandan.rl import fast  # noqa: E402
from guandan.rl.belief import BeliefNet, save_belief  # noqa: E402
from guandan.rl.dmc import _device  # noqa: E402
from guandan.rl.policy import load_policy  # noqa: E402

_W: dict = {}


def gen(seed: int, n_deals: int, path: str):
    torch.set_num_threads(1)
    if "actor" not in _W:
        _W["actor"], _W["critic"] = load_policy(path, critic=True)
    rng = np.random.default_rng(seed)
    styles = ["bomber", "turtle", "breaker", "keeper", "noisy", "sprinter", "single_dumper", "overtaker"]

    def opponents(r):
        u = r.random()
        if u < 0.15:
            return "heuristic", None
        if u < 0.30:
            return "style:" + styles[int(r.integers(len(styles)))], None
        return "self", None
    a = _W["actor"]
    r = fast.play_batch(rng, n_deals, "ppo", (a, _W["critic"]), opponents, 0.75, 0.95, 3.0, width=32, version=a.version)
    return r["S"], r["O"]


def scores(logits: torch.Tensor, o: torch.Tensor) -> dict:
    """BCE and the mean log-probability the model gives the true holder of each hidden card type (3 players compared)."""
    bce = nn.functional.binary_cross_entropy_with_logits(logits, o).item()
    p = torch.sigmoid(logits).view(len(o), 3, -1)[:, :, 0::2] + 1e-4
    held = o.view(len(o), 3, -1)[:, :, 0::2]
    share = p / p.sum(1, keepdim=True)
    mask = held > 0
    logp = (torch.log(share) * mask).sum().item() / mask.sum().item()
    top1 = ((share.argmax(1, keepdim=True) == torch.arange(3, device=o.device).view(1, 3, 1)) & mask).sum().item() / mask.sum().item() * 3 / 3
    return {"bce": bce, "logp": logp}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--actor", default="runs/all3/model.pt")
    ap.add_argument("--out", default="runs/belief/b1.pt")
    ap.add_argument("--decisions", type=int, default=6_000_000)
    ap.add_argument("--hidden", type=int, default=1024)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    dev = _device("auto")
    actor = load_policy(a.actor, device="cpu")
    net = BeliefNet(a.hidden, actor.version, a.layers).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=a.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, a.decisions // a.batch), eta_min=a.lr / 20)
    rng = np.random.default_rng(a.seed)
    print(f"belief net {sum(p.numel() for p in net.parameters()) / 1e6:.1f}M parameters on {dev}; actor feature version {actor.version}", flush=True)
    t0 = time.time()
    seen = steps = 0
    buf_s, buf_o = [], []
    with ProcessPoolExecutor(a.workers) as pool:
        hold = pool.submit(gen, 99991, 400, a.actor).result()           # held-out positions (different seeds from training)
        hs, ho = torch.from_numpy(hold[0][:60000]).float().to(dev), torch.from_numpy(hold[1][:60000]).float().to(dev)
        with torch.no_grad():
            a_logits = actor.to(dev).belief(actor.state(hs))
        side = scores(a_logits, ho)
        print(f"held-out {len(hs)} positions; the actor's own belief head: BCE {side['bce']:.4f}, mean log p(holder) {side['logp']:.3f}", flush=True)
        inflight = {pool.submit(gen, int(rng.integers(2**31)), 16, a.actor) for _ in range(a.workers * 2)}
        while seen < a.decisions:
            done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
            for f in done:
                s, o = f.result()
                buf_s.append(s), buf_o.append(o)
                inflight.add(pool.submit(gen, int(rng.integers(2**31)), 16, a.actor))
            if sum(len(x) for x in buf_s) >= 65536:
                S = torch.from_numpy(np.concatenate(buf_s)).to(dev)
                O = torch.from_numpy(np.concatenate(buf_o)).to(dev)
                buf_s, buf_o = [], []
                perm = torch.randperm(len(S), device=dev)
                net.train()
                for i in range(0, len(S) - a.batch + 1, a.batch):
                    ix = perm[i:i + a.batch]
                    loss = nn.functional.binary_cross_entropy_with_logits(net(S[ix].float()), O[ix].float())
                    opt.zero_grad()
                    loss.backward()
                    opt.step()
                    sched.step()
                    steps += 1
                seen += len(S)
                if steps % 64 < 33 or seen >= a.decisions:
                    net.eval()
                    with torch.no_grad():
                        m = scores(net(hs), ho)
                    print(f"{seen:>9,} decisions  {time.time() - t0:5.0f}s  loss {loss.item():.4f}  held-out BCE {m['bce']:.4f} (side head {side['bce']:.4f})"
                          f"  log p(holder) {m['logp']:.3f} (side head {side['logp']:.3f})", flush=True)
                    save_belief(net, a.out, decisions=seen)
    save_belief(net, a.out, decisions=seen)


if __name__ == "__main__":
    main()
