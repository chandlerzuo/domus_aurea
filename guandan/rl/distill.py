"""Train the policy toward what look-ahead search would play ("expert iteration").

Each round:
  1. Workers play deals with the current policy. At a sample of decisions they run the search
     (guandan/rl/search.py): the policy's top few moves are played out in many sampled worlds, which
     gives each candidate an estimated result. The label is the policy shifted toward the better
     candidates (`improved_policy`); the deal continues with a move drawn from that label, so the
     visited states come from the improved player.
  2. The learner fits the policy to the labels (cross-entropy), keeping the hidden-hand prediction
     head trained too. Labels are used for this round only, so memory stays small.
The next round searches with the improved policy, so search and policy improve together.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from ..agents import HeuristicAgent
from .dmc import _device, random_match
from .features import encode_actions, encode_state
from .policy import encode_oracle, load_policy, padded_log_probs, policy_step, save_policy
from .search import improved_policy, search_values

torch.set_num_threads(1)


@dataclass
class DistillConfig:
    worlds: int = 32
    topk: int = 4
    tau: float = 0.5            # lower = trust the search more (values are in levels)
    label_prob: float = 0.4     # share of multi-move decisions that get a search label
    labels_per_round: int = 100_000
    deals_per_task: int = 6
    p_tribute: float = 0.75
    lr: float = 5e-5
    epochs: int = 2
    minibatch: int = 4096
    belief_coef: float = 0.05
    max_grad_norm: float = 1.0
    workers: int = 0
    device: str = "auto"
    seed: int = 0


_W: dict = {}


def _worker_init(cfg: DistillConfig) -> None:
    torch.set_num_threads(1)
    _W.update(cfg=cfg, actors={})


def _actor(path: str, version: int):
    cache = _W["actors"]
    if (path, version) not in cache:
        cache.clear()
        cache[(path, version)] = load_policy(path)
    return cache[(path, version)]


def label_task(seed: int, latest: tuple[str, int]) -> dict:
    """Play a few deals and label a sample of the decisions with search."""
    cfg: DistillConfig = _W["cfg"]
    rng = np.random.default_rng(seed)
    actor = _actor(*latest)
    v = actor.version
    out = {"S": [], "A": [], "O": [], "P": [], "C": [], "V": [], "n": [], "top1": [], "shift": []}
    for _ in range(cfg.deals_per_task):
        m = random_match(rng, cfg.p_tribute)
        d = m.new_deal()
        for t in m.pending_returns:
            m.give_return(t.receiver, HeuristicAgent(0).choose_return(d.hands[t.receiver], d.level))
        while not d.done:
            seat = d.to_act
            obs = d.observation(seat)
            legal = obs["legal"]
            if len(legal) == 1:
                d.play(legal[0])
                continue
            res = search_values(actor, obs, rng, cfg.worlds, cfg.topk) if rng.random() < cfg.label_prob else None
            if res is None:
                _, _, p = policy_step(actor, encode_state(obs, v), encode_actions(obs, v), rng)
                d.play(legal[int(rng.choice(len(p), p=p / p.sum()))])
                continue
            cand, p, val = res
            target = improved_policy(p, cand, val, cfg.tau)
            out["S"].append(encode_state(obs, v))
            out["A"].append(encode_actions(obs, v))
            out["O"].append(encode_oracle(d.hands, seat))
            out["P"].append(p.astype(np.float32))
            c = np.full(cfg.topk, -1, np.int16)
            c[:len(cand)] = cand
            vv = np.zeros(cfg.topk, np.float32)
            vv[:len(cand)] = val
            out["C"].append(c)
            out["V"].append(vv)
            out["n"].append(len(legal))
            out["top1"].append(int(np.argmax(target) == np.argmax(p)))
            out["shift"].append(float(0.5 * np.abs(target - p).sum()))  # total variation distance
            d.play(legal[int(rng.choice(len(target), p=target / target.sum()))])
    if not out["n"]:
        return {"count": 0}
    return {"count": len(out["n"]), "S": np.stack(out["S"]), "O": np.stack(out["O"]), "A": np.concatenate(out["A"]),
            "P": np.concatenate(out["P"]), "C": np.stack(out["C"]), "V": np.stack(out["V"]),
            "n": np.asarray(out["n"], np.int32),
            "top1_same": float(np.mean(out["top1"])), "shift": float(np.mean(out["shift"]))}


class LabelBatch:
    """Concatenated labelled decisions; legal-move rows and probabilities are flat.
    `P` = the policy's probabilities, `C`/`V` = the searched candidates and their estimated results;
    the training target `T` is derived from them for a chosen temperature `tau`."""

    def __init__(self, parts: list[dict], tau: float = 0.5):
        parts = [p for p in parts if p["count"]]
        for k in ("S", "O", "A", "P", "C", "V", "n"):
            setattr(self, k, np.concatenate([p[k] for p in parts]))
        self.off = np.concatenate([[0], np.cumsum(self.n)[:-1]])
        self.set_tau(tau)

    def set_tau(self, tau: float) -> None:
        T = self.P.copy()
        for i in range(len(self.n)):
            c = self.C[i]
            k = int((c >= 0).sum())
            lo = self.off[i]
            T[lo:lo + self.n[i]] = improved_policy(self.P[lo:lo + self.n[i]], list(c[:k]), self.V[i][:k], tau)
        self.T = T

    def save(self, path) -> None:
        np.savez_compressed(path, **{k: getattr(self, k) for k in ("S", "O", "A", "P", "C", "V", "n")})

    @classmethod
    def load(cls, paths, tau: float = 0.5) -> "LabelBatch":
        parts = []
        for path in paths:
            z = np.load(path)
            parts.append({**{k: z[k] for k in ("S", "O", "A", "P", "C", "V", "n")}, "count": len(z["n"])})
        return cls(parts, tau)

    def __len__(self) -> int:
        return len(self.n)

    def minibatch(self, idx: np.ndarray, dev: torch.device) -> dict:
        c = self.n[idx]
        seg = np.repeat(np.arange(len(idx)), c)
        pos = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)
        rows = self.off[idx][seg] + pos
        t = lambda x, dt=None: torch.from_numpy(np.ascontiguousarray(x)).to(dev, dt)
        width = int(c.max())
        target = np.zeros((len(idx), width), np.float32)
        target[seg, pos] = self.T[rows]
        return {"s": t(self.S[idx], torch.float32), "o": t(self.O[idx], torch.float32),
                "a": t(self.A[rows], torch.float32), "seg": t(seg), "pos": t(pos), "width": width,
                "target": t(target)}


def fit(actor, opt, batch: LabelBatch, cfg: DistillConfig, rng: np.random.Generator, dev) -> dict:
    """Cross-entropy toward the labels (plus the hidden-hand head), `cfg.epochs` passes."""
    stats = {"ce": 0.0, "agree": 0.0, "belief": 0.0}
    k = 0
    for _ in range(cfg.epochs):
        order = rng.permutation(len(batch))
        for st in range(0, len(order), cfg.minibatch):
            mb = batch.minibatch(order[st:st + cfg.minibatch], dev)
            hs = actor.state(mb["s"])
            lp = padded_log_probs(actor.logits(hs, mb["a"], mb["seg"]), mb["seg"], mb["pos"], len(mb["target"]), mb["width"])
            ce = -(mb["target"] * lp).sum(1).mean()
            belief = nn.functional.binary_cross_entropy_with_logits(actor.belief(hs), mb["o"])
            loss = ce + cfg.belief_coef * belief
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(actor.parameters(), cfg.max_grad_norm)
            opt.step()
            with torch.no_grad():
                stats["ce"] += ce.item()
                stats["belief"] += belief.item()
                stats["agree"] += (lp.argmax(1) == mb["target"].argmax(1)).float().mean().item()
            k += 1
    return {key: val / max(k, 1) for key, val in stats.items()}


def distill(cfg: DistillConfig, init: str | Path, out: str | Path, rounds: int, log=print) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(cfg), indent=2))
    dev = _device(cfg.device)
    rng = np.random.default_rng(cfg.seed)
    actor, critic = load_policy(init, critic=True)
    actor = actor.to(dev).train()
    opt = torch.optim.Adam(actor.parameters(), lr=cfg.lr)
    latest = out / "latest.pt"
    save_policy(actor, critic, latest)
    workers = cfg.workers or max(1, (os.cpu_count() or 2) - 2)
    metrics = open(out / "metrics.jsonl", "a")
    t0 = time.time()
    with ProcessPoolExecutor(workers, initializer=_worker_init, initargs=(cfg,)) as pool:
        for r in range(1, rounds + 1):
            tr = time.time()
            inflight, parts, got = set(), [], 0
            version = r

            def submit():
                inflight.add(pool.submit(label_task, int(rng.integers(2**31)), (str(latest), version)))

            for _ in range(workers):
                submit()
            while inflight:
                done, _ = wait(inflight, return_when=FIRST_COMPLETED)
                for f in done:
                    inflight.discard(f)
                    res = f.result()
                    parts.append(res)
                    got += res["count"]
                    if got + workers * 25 < cfg.labels_per_round:  # keep workers busy, don't overshoot much
                        submit()
            tg = time.time() - tr
            batch = LabelBatch(parts, cfg.tau)
            (out / "labels").mkdir(exist_ok=True)
            batch.save(out / "labels" / f"round_{r:03d}.npz")
            st = fit(actor, opt, batch, cfg, rng, dev)
            save_policy(actor, critic, latest)
            save_policy(actor, critic, out / "model.pt", round=r)
            same = float(np.average([p["top1_same"] for p in parts if p["count"]], weights=[p["count"] for p in parts if p["count"]]))
            shift = float(np.average([p["shift"] for p in parts if p["count"]], weights=[p["count"] for p in parts if p["count"]]))
            row = {"round": r, "labels": len(batch), "label_time": round(tg), "elapsed": round(time.time() - t0),
                   "search_changes_top_move": round(1 - same, 3), "label_shift": round(shift, 3), **{k: round(v, 4) for k, v in st.items()}}
            metrics.write(json.dumps(row) + "\n")
            metrics.flush()
            log(f"[distill] round {r}/{rounds}  {row}")
    metrics.close()


def label_dataset(cfg: DistillConfig, teacher: str | Path, out: str | Path, chunks: int, log=print) -> None:
    """Label decisions with search under a fixed teacher policy, `cfg.labels_per_round` per file
    (out/labels_NNN.npz). Fit to them afterwards with `scripts/fit_distill.py`, as often as you like."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(cfg), indent=2))
    workers = cfg.workers or max(1, (os.cpu_count() or 2) - 2)
    rng = np.random.default_rng(cfg.seed)
    t0 = time.time()
    with ProcessPoolExecutor(workers, initializer=_worker_init, initargs=(cfg,)) as pool:
        for c in range(1, chunks + 1):
            inflight, parts, got = set(), [], 0
            for _ in range(workers):
                inflight.add(pool.submit(label_task, int(rng.integers(2**31)), (str(teacher), 0)))
            while inflight:
                done, _ = wait(inflight, return_when=FIRST_COMPLETED)
                for f in done:
                    inflight.discard(f)
                    res = f.result()
                    parts.append(res)
                    got += res["count"]
                    if got + workers * 25 < cfg.labels_per_round:
                        inflight.add(pool.submit(label_task, int(rng.integers(2**31)), (str(teacher), 0)))
            batch = LabelBatch(parts, cfg.tau)
            batch.save(out / f"labels_{c:03d}.npz")
            same = np.average([p["top1_same"] for p in parts if p["count"]], weights=[p["count"] for p in parts if p["count"]])
            log(f"[labels] chunk {c}/{chunks}: {len(batch)} labels, search changed the top move in {1 - same:.1%}, "
                f"{time.time() - t0:.0f}s elapsed")
