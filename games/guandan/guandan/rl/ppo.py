"""Imitation warm start, then PPO fine-tuning with an oracle critic.

Stage 1, behaviour cloning: actors stream fresh games of the heuristic
playing all four seats. The actor learns to pick the heuristic's move
(cross-entropy over the legal set), the critic learns the deal result, and the
belief head learns the hidden hands. Data is used once, so there is no overfitting
to a fixed dataset, and the policy starts at roughly heuristic strength instead
of random.

Stage 2, PPO (DanZero+-style fine-tuning): clipped policy-gradient updates with GAE
advantages from the oracle critic (it sees all four hands during training;
PerfectDou's perfect-training / imperfect-execution), plus the belief loss and
an entropy bonus. Opponents are mixed as in poker_ai's league: the current
policy against itself, the heuristic, the DMC model, and frozen snapshots.
Only the learning team's decisions are trained on against fixed opponents.
"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import field, asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from ..agents import Agent, HeuristicAgent
from ..game import team
from .dmc import DEFAULT_MODEL as DMC_MODEL, REWARD_SCALE, DMCAgent, _device, load_net, random_match
from . import fast as fast_rl
from .features import encode_actions, encode_state
from .policy import (Actor, Critic, PolicyAgent, encode_oracle, load_policy, padded_log_probs, policy_step,
                     save_policy, widen_policy)

torch.set_num_threads(1)
FIELDS = ("S", "O", "n", "chosen", "logp", "adv", "ret")


@dataclass
class PPOConfig:
    hidden: int = 512
    bc_lr: float = 3e-4
    lr: float = 3e-5
    clip: float = 0.2
    epochs: int = 2
    minibatch: int = 4096
    steps_per_update: int = 65536
    bc_chunk: int = 32768          # decisions per behaviour-cloning pass
    entropy: float = 0.003
    value_coef: float = 0.5
    belief_coef: float = 0.05
    lam: float = 0.95
    max_grad_norm: float = 1.0
    p_heuristic: float = 0.2
    p_dmc: float = 0.15
    p_snapshot: float = 0.15
    p_tribute: float = 0.75
    snapshot_every: int = 10       # PPO updates between snapshots
    max_snapshots: int = 20
    league: list = field(default_factory=list)   # fixed past checkpoints that stay in the opponent pool for the whole run
    deals_per_task: int = 8        # per task without the Rust core
    fast: bool = True              # batched actors on the Rust core when it is built
    version: int = 1               # feature version for networks created from scratch (see features.py)
    tables_per_worker: int = 32    # deals played side by side in one batched task
    queue_per_worker: int = 1      # tasks in flight per actor; more keeps actors busy but trains on staler data
    workers: int = 0
    device: str = "auto"
    seed: int = 0


# ---- actor process ----------------------------------------------------------

_W: dict = {}


def _worker_init(cfg: PPOConfig) -> None:
    torch.set_num_threads(1)
    _W.update(cfg=cfg, actors={}, dmc=None)


def _actor(path: str, version: int) -> Actor:
    cache = _W["actors"]
    key = (path, version)
    if key not in cache:
        if len(cache) > 8:
            cache.pop(next(iter(cache)))
        cache[key] = load_policy(path, critic=True)
    return cache[key]


def _dmc_net():
    if _W["dmc"] is None:
        _W["dmc"] = load_net(DMC_MODEL)
    return _W["dmc"]


class _Traj:
    def __init__(self):
        self.S, self.O, self.A, self.chosen, self.logp, self.value = [], [], [], [], [], []


def play_task(seed: int, n_deals: int, mode: str, latest: tuple[str, int] | None,
              opponent: tuple[str, str] = ("self", "")) -> dict:
    """mode 'bc': heuristic self-play, record its choices. mode 'ppo': record the learner's sampled moves."""
    cfg: PPOConfig = _W["cfg"]
    rng = np.random.default_rng(seed)
    lam = cfg.lam
    if mode == "ppo":
        actor, critic = _actor(*latest)
    kind = opponent[0]
    out = {k: [] for k in FIELDS}
    out["A"] = []
    scores = []
    for _ in range(n_deals):
        m = random_match(rng, cfg.p_tribute)
        d = m.new_deal()
        me = int(rng.integers(2))
        agents: list[Agent | None] = []
        learn = [False] * 4
        for s in range(4):
            sd = int(rng.integers(2**31))
            if mode == "bc":
                agents.append(HeuristicAgent(sd))
                learn[s] = True
            elif kind == "self" or team(s) == me:
                agents.append(None)  # the learner, driven below
                learn[s] = True
            elif kind == "heuristic":
                agents.append(HeuristicAgent(sd))
            elif kind == "dmc":
                agents.append(DMCAgent(_dmc_net(), seed=sd))
            else:
                agents.append(PolicyAgent(_actor(opponent[1], 0)[0], seed=sd, greedy=False))
        for t in m.pending_returns:
            ag = agents[t.receiver] or HeuristicAgent(0)
            m.give_return(t.receiver, ag.choose_return(d.hands[t.receiver], d.level))
        trajs = [_Traj() for _ in range(4)]
        while not d.done:
            seat = d.to_act
            obs = d.observation(seat)
            legal = obs["legal"]
            if len(legal) == 1:
                d.play(legal[0])
                continue
            if not learn[seat]:
                d.play(legal[agents[seat].act(obs)])
                continue
            ver = actor.version if mode == "ppo" else cfg.version
            s, a, o = encode_state(obs, ver), encode_actions(obs, ver), encode_oracle(d.hands, seat)
            tr = trajs[seat]
            if mode == "bc":
                i, lp, v = agents[seat].act(obs), 0.0, 0.0
            else:
                i, lp, _ = policy_step(actor, s, a, rng)
                with torch.no_grad():
                    v = float(critic(torch.from_numpy(s).float()[None], torch.from_numpy(o).float()[None])[0])
            tr.S.append(s), tr.O.append(o), tr.A.append(a), tr.chosen.append(i), tr.logp.append(lp), tr.value.append(v)
            d.play(legal[i])
        win, up = d.result()
        scores.append(up if win == me else -up)
        for s, tr in enumerate(trajs):
            if not tr.S:
                continue
            r = (up if win == team(s) else -up) / REWARD_SCALE
            if mode == "bc":
                adv, ret = [0.0] * len(tr.S), [r] * len(tr.S)
            else:  # GAE over this player's decisions; reward only at the end (gamma = 1)
                vals = tr.value + [r]
                adv, gae = [0.0] * len(tr.S), 0.0
                for t in reversed(range(len(tr.S))):
                    gae = vals[t + 1] - vals[t] + lam * gae
                    adv[t] = gae
                ret = [x + v for x, v in zip(adv, tr.value)]
            out["S"] += tr.S
            out["O"] += tr.O
            out["A"] += tr.A
            out["n"] += [len(x) for x in tr.A]
            out["chosen"] += tr.chosen
            out["logp"] += tr.logp
            out["adv"] += adv
            out["ret"] += ret
    res = {"S": np.stack(out["S"]), "O": np.stack(out["O"]), "A": np.concatenate(out["A"]),
           "n": np.asarray(out["n"], np.int32), "chosen": np.asarray(out["chosen"], np.int64),
           "logp": np.asarray(out["logp"], np.float32), "adv": np.asarray(out["adv"], np.float32),
           "ret": np.asarray(out["ret"], np.float32)}
    res.update(opponent=kind if mode == "ppo" else "bc", scores=scores, deals=n_deals)
    return res


def play_task_fast(seed: int, n_deals: int, mode: str, latest: tuple[str, int], snapshots: list[str]) -> dict:
    """Batched equivalent of `play_task` on the Rust core; each deal draws its own opponent."""
    cfg: PPOConfig = _W["cfg"]
    rng = np.random.default_rng(seed)
    learner = _actor(*latest) if mode == "ppo" else None

    def opponents(r: np.random.Generator):
        u = r.random()
        if u < cfg.p_heuristic:
            return "heuristic", None
        if u < cfg.p_heuristic + cfg.p_dmc and DMC_MODEL.exists():
            return "dmc", _dmc_net()
        if u < cfg.p_heuristic + cfg.p_dmc + cfg.p_snapshot and snapshots:
            return "snapshot", _actor(snapshots[int(r.integers(len(snapshots)))], 0)[0]
        return "self", None

    return fast_rl.play_batch(rng, n_deals, mode, learner, opponents, cfg.p_tribute, cfg.lam, REWARD_SCALE,
                              width=cfg.tables_per_worker, version=cfg.version)


# ---- learner ----------------------------------------------------------------

class Batch:
    """Concatenated actor results; legal-move rows are flat with per-decision offsets."""

    def __init__(self, parts: list[dict]):
        for k in FIELDS:
            setattr(self, k, np.concatenate([p[k] for p in parts]))
        self.A = np.concatenate([p["A"] for p in parts])
        self.off = np.concatenate([[0], np.cumsum(self.n)[:-1]])

    def __len__(self) -> int:
        return len(self.n)

    def to_device(self, dev: torch.device) -> "Batch":
        """Keep the whole batch on the learner device (uint8 inputs are small), so minibatches are
        sliced there instead of gathered on the CPU and copied every step."""
        if dev.type == "cpu":
            return self
        t = lambda x: torch.from_numpy(np.ascontiguousarray(x)).to(dev)
        self._dev = {"S": t(self.S), "O": t(self.O), "A": t(self.A), "n": t(self.n.astype(np.int64)),
                     "off": t(self.off.astype(np.int64)), "chosen": t(self.chosen), "logp": t(self.logp),
                     "adv": t(self.adv), "ret": t(self.ret)}
        return self

    def minibatch(self, idx: np.ndarray, dev: torch.device) -> dict:
        d = getattr(self, "_dev", None)
        if d is not None:
            ix = torch.from_numpy(idx).to(dev)
            c = d["n"][ix]
            seg = torch.repeat_interleave(torch.arange(len(ix), device=dev), c)
            pos = torch.arange(int(c.sum()), device=dev) - torch.repeat_interleave(torch.cumsum(c, 0) - c, c)
            rows = d["off"][ix][seg] + pos
            return {"s": d["S"][ix].float(), "o": d["O"][ix].float(), "a": d["A"][rows].float(), "seg": seg,
                    "pos": pos, "width": int(c.max()), "chosen": d["chosen"][ix], "logp": d["logp"][ix],
                    "adv": d["adv"][ix], "ret": d["ret"][ix]}
        c = self.n[idx]
        seg = np.repeat(np.arange(len(idx)), c)
        pos = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)
        rows = self.off[idx][seg] + pos
        t = lambda x, dt=None: torch.from_numpy(np.ascontiguousarray(x)).to(dev, dt)
        return {"s": t(self.S[idx], torch.float32), "o": t(self.O[idx], torch.float32),
                "a": t(self.A[rows], torch.float32), "seg": t(seg), "pos": t(pos), "width": int(c.max()),
                "chosen": t(self.chosen[idx]), "logp": t(self.logp[idx]), "adv": t(self.adv[idx]),
                "ret": t(self.ret[idx])}


def _forward(actor: Actor, critic: Critic, mb: dict):
    hs = actor.state(mb["s"])
    B = len(mb["chosen"])
    logp_all = padded_log_probs(actor.logits(hs, mb["a"], mb["seg"]), mb["seg"], mb["pos"], B, mb["width"])
    logp = logp_all.gather(1, mb["chosen"][:, None]).squeeze(1)
    ent = -(logp_all.exp() * logp_all).sum(-1).mean()
    belief = nn.functional.binary_cross_entropy_with_logits(actor.belief(hs), mb["o"])
    v = critic(mb["s"], mb["o"])
    return logp_all, logp, ent, belief, v


def bc_update(actor, critic, opt, batch: Batch, cfg: PPOConfig, rng, dev) -> dict:
    stats = {"ce": 0.0, "acc": 0.0, "value_loss": 0.0, "belief": 0.0}
    order, k = rng.permutation(len(batch)), 0
    for st in range(0, len(order), cfg.minibatch):
        mb = batch.minibatch(order[st:st + cfg.minibatch], dev)
        logp_all, logp, _, belief, v = _forward(actor, critic, mb)
        ce = -logp.mean()
        vl = nn.functional.mse_loss(v, mb["ret"])
        loss = ce + cfg.value_coef * vl + cfg.belief_coef * belief
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_([*actor.parameters(), *critic.parameters()], cfg.max_grad_norm)
        opt.step()
        with torch.no_grad():
            stats["ce"] += ce.item()
            stats["acc"] += (logp_all.argmax(1) == mb["chosen"]).float().mean().item()
            stats["value_loss"] += vl.item()
            stats["belief"] += belief.item()
        k += 1
    return {key: val / max(k, 1) for key, val in stats.items()}


def ppo_update(actor, critic, opt, batch: Batch, cfg: PPOConfig, rng, dev) -> dict:
    stats = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "belief": 0.0, "clip_frac": 0.0, "kl": 0.0}
    adv_mean, adv_std = batch.adv.mean(), batch.adv.std() + 1e-8
    k = 0
    for _ in range(cfg.epochs):
        order = rng.permutation(len(batch))
        for st in range(0, len(order), cfg.minibatch):
            mb = batch.minibatch(order[st:st + cfg.minibatch], dev)
            _, logp, ent, belief, v = _forward(actor, critic, mb)
            ratio = torch.exp(logp - mb["logp"])
            a = (mb["adv"] - float(adv_mean)) / float(adv_std)
            pl = -torch.min(ratio * a, ratio.clamp(1 - cfg.clip, 1 + cfg.clip) * a).mean()
            vl = nn.functional.mse_loss(v, mb["ret"])
            loss = pl + cfg.value_coef * vl + cfg.belief_coef * belief - cfg.entropy * ent
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_([*actor.parameters(), *critic.parameters()], cfg.max_grad_norm)
            opt.step()
            with torch.no_grad():
                stats["policy_loss"] += pl.item()
                stats["value_loss"] += vl.item()
                stats["entropy"] += ent.item()
                stats["belief"] += belief.item()
                stats["clip_frac"] += ((ratio - 1).abs() > cfg.clip).float().mean().item()
                stats["kl"] += (mb["logp"] - logp).mean().item()
            k += 1
    return {key: val / max(k, 1) for key, val in stats.items()}


def train(cfg: PPOConfig, bc_deals: int, ppo_deals: int, out: str | Path, resume: bool = False, log=print,
          init: str | Path | None = None):
    out = Path(out)
    (out / "snapshots").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(cfg), indent=2))
    dev = _device(cfg.device)
    rng = np.random.default_rng(cfg.seed)
    workers = cfg.workers or max(1, (os.cpu_count() or 2) - 1)
    start = out / "model.pt" if resume and (out / "model.pt").exists() else None
    if start is None and init is not None:
        start = Path(init)
    if start is None and bc_deals == 0 and (out / "bc.pt").exists():
        start = out / "bc.pt"
    if start is not None:
        actor, critic = load_policy(start, critic=True)
        log(f"starting from {start} (feature version {actor.version})")
        if actor.version < cfg.version:
            actor, critic = widen_policy(actor, critic, cfg.version)
            log(f"widened to feature version {cfg.version}: new input columns start at zero weight")
        cfg.version = actor.version
    else:
        actor, critic = Actor(cfg.hidden, cfg.version), Critic(cfg.hidden, cfg.version)
    actor, critic = actor.to(dev).train(), critic.to(dev).train()
    latest = out / "latest.pt"
    metrics = open(out / "metrics.jsonl", "a")

    def run(stage: str, deals: int, lr: float) -> None:
        opt = torch.optim.Adam([*actor.parameters(), *critic.parameters()], lr=lr)
        version = 0
        save_policy(actor, critic, latest)
        fixed = [str(x) for x in cfg.league]       # never evicted
        snapshots: list[str] = list(fixed)
        need = cfg.bc_chunk if stage == "bc" else cfg.steps_per_update
        parts, buffered, submitted, done, updates = [], 0, 0, 0, 0
        scores = {k: deque(maxlen=2000) for k in ("self", "heuristic", "dmc", "snapshot", "bc")}
        t0 = last = time.time()
        last_stats: dict = {}
        learn_time = 0.0

        use_fast = cfg.fast and fast_rl.AVAILABLE
        log(f"[{stage}] actors: {'batched, Rust core' if use_fast else 'one deal at a time, Python'}")

        def opponent() -> tuple[str, str]:
            u = rng.random()
            if u < cfg.p_heuristic:
                return "heuristic", ""
            if u < cfg.p_heuristic + cfg.p_dmc and DMC_MODEL.exists():
                return "dmc", ""
            if u < cfg.p_heuristic + cfg.p_dmc + cfg.p_snapshot and snapshots:
                return "snapshot", snapshots[int(rng.integers(len(snapshots)))]
            return "self", ""

        with ProcessPoolExecutor(workers, initializer=_worker_init, initargs=(cfg,)) as pool:
            inflight = set()

            def submit():
                nonlocal submitted
                if use_fast:
                    args = (int(rng.integers(2**31)), cfg.tables_per_worker, stage, (str(latest), version), list(snapshots))
                    inflight.add(pool.submit(play_task_fast, *args))
                    submitted += cfg.tables_per_worker
                    return
                args = (int(rng.integers(2**31)), cfg.deals_per_task, stage, (str(latest), version))
                inflight.add(pool.submit(play_task, *args, opponent() if stage == "ppo" else ("self", "")))
                submitted += cfg.deals_per_task

            for _ in range(cfg.queue_per_worker * workers):
                if submitted < deals:
                    submit()
            while inflight:
                finished, _ = wait(inflight, return_when=FIRST_COMPLETED)
                for f in finished:
                    inflight.discard(f)
                    r = f.result()
                    done += r["deals"]
                    if "scores_by" in r:
                        for k, v in r["scores_by"].items():
                            scores[k].extend(v)
                    else:
                        scores[r["opponent"]].extend(r["scores"])
                    parts.append(r)
                    buffered += len(r["n"])
                    if submitted < deals:
                        submit()
                if buffered >= need or (not inflight and buffered):
                    batch = Batch(parts).to_device(dev)
                    parts, buffered = [], 0
                    upd = bc_update if stage == "bc" else ppo_update
                    tu = time.time()
                    last_stats = upd(actor, critic, opt, batch, cfg, rng, dev)
                    learn_time += time.time() - tu
                    updates += 1
                    save_policy(actor, critic, latest)
                    version += 1
                    if stage == "ppo" and updates % cfg.snapshot_every == 0:
                        p = out / "snapshots" / f"u{updates:05d}.pt"
                        save_policy(actor, critic, p)
                        snapshots.append(str(p))
                        if len(snapshots) - len(fixed) > cfg.max_snapshots:
                            snapshots.pop(len(fixed))
                        save_policy(actor, critic, out / "model.pt", updates=updates, deals=done)
                if time.time() - last > 30 or not inflight:
                    last = time.time()
                    el = last - t0
                    vs = {k: round(float(np.mean(q)), 3) for k, q in scores.items() if q and k not in ("bc", "self")}
                    st = " ".join(f"{k} {v:.3f}" for k, v in last_stats.items())
                    log(f"[{stage}] deals {done:>9,}  {done / el:5.0f}/s  learner {100 * learn_time / el:3.0f}%  "
                        f"updates {updates:>5}  {st}  vs {vs}")
                    metrics.write(json.dumps({"stage": stage, "time": el, "deals": done, "updates": updates,
                                              **last_stats, **{f"vs_{k}": v for k, v in vs.items()}}) + "\n")
                    metrics.flush()

    if bc_deals:
        run("bc", bc_deals, cfg.bc_lr)
        save_policy(actor, critic, out / "bc.pt")
    if ppo_deals:
        run("ppo", ppo_deals, cfg.lr)
    save_policy(actor, critic, out / "model.pt")
    metrics.close()
    return actor
