"""Deep Monte-Carlo (DMC) self-play, after DouZero (Zha et al. 2021) and DanZero (Lu et al. 2022).

Guandan's action space is large and varies by state (hundreds of legal
combos), so instead of a fixed policy head the network scores
(state, action) pairs: Q(s, a) predicts the final team result of the deal
(+levels gained / -levels conceded, scaled to [-1, 1]). Acting is argmax Q
over the legal moves with epsilon-greedy exploration, and training regresses
Q(s, a) onto the realised Monte-Carlo return of the deal. There is no
bootstrapping, so long, sparse-reward deals need no value-function tricks.

All four seats share one network. Opponents are mixed to avoid self-play
cycles, as in poker_ai's league: mostly the current network, sometimes the
heuristic baseline or a frozen past snapshot (only the learning team's
decisions are recorded then). Actor processes play deals with the latest
published weights; the main process trains on whatever they send back.
"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from ..agents import Agent, HeuristicAgent
from ..game import Match, team
from .features import ACTION_DIM, STATE_DIM, encode_actions, encode_state

torch.set_num_threads(1)  # batch-of-legal-moves inference is faster single-threaded; actors are processes
REWARD_SCALE = 3.0
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "runs" / "dmc" / "model.pt"


class QNet(nn.Module):
    def __init__(self, hidden: int = 512):
        super().__init__()
        self.hidden = hidden
        self.state = nn.Sequential(nn.Linear(STATE_DIM, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.action = nn.Sequential(nn.Linear(ACTION_DIM, 256), nn.ReLU())
        self.head = nn.Sequential(nn.Linear(hidden + 256, hidden), nn.ReLU(),
                                  nn.Linear(hidden, 256), nn.ReLU(), nn.Linear(256, 1))

    def forward(self, s: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
        return self.head(torch.cat([self.state(s), self.action(a)], -1)).squeeze(-1)

    def q_values(self, s: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
        """One state (S,) against n candidate actions (n, A); the state is embedded once."""
        hs = self.state(s[None]).expand(a.shape[0], -1)
        return self.head(torch.cat([hs, self.action(a)], -1)).squeeze(-1)


def load_net(path: str | Path, device: str = "cpu") -> QNet:
    ckpt = torch.load(path, map_location=device, weights_only=True)
    net = QNet(ckpt["hidden"])
    net.load_state_dict(ckpt["state"])
    return net.to(device).eval()


def save_net(net: QNet, path: str | Path, **extra) -> None:
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    torch.save({"hidden": net.hidden, "state": {k: v.detach().cpu() for k, v in net.state_dict().items()},
                **extra}, tmp)
    os.replace(tmp, path)  # actors may be reading the file


class DMCAgent(Agent):
    name = "dmc"

    def __init__(self, net: QNet | None = None, seed: int | None = None, epsilon: float = 0.0,
                 record: bool = False, path: str | Path = DEFAULT_MODEL):
        super().__init__(seed)
        self.net = net if net is not None else load_net(path)
        self.epsilon = epsilon
        self.record = record
        self.states: list[np.ndarray] = []
        self.actions: list[np.ndarray] = []

    def act(self, obs: dict) -> int:
        legal = obs["legal"]
        if len(legal) == 1:
            return 0
        s = encode_state(obs)
        a = encode_actions(obs)
        with torch.no_grad():
            q = self.net.q_values(torch.from_numpy(s).float(), torch.from_numpy(a).float()).numpy()
        i = int(self.rng.integers(len(legal))) if self.rng.random() < self.epsilon else int(q.argmax())
        if self.record:
            self.states.append(s)
            self.actions.append(a[i])
        top = np.argsort(-q)[:3]
        self.info = {"q": {f"{legal[j].combo} x{len(legal[j].cards)}": round(float(q[j]) * REWARD_SCALE, 2)
                           for j in top}}
        return i


@dataclass
class DMCConfig:
    hidden: int = 512
    lr: float = 1e-4
    batch: int = 4096
    epsilon: float = 0.01
    p_heuristic: float = 0.15      # opponent team: heuristic baseline
    p_snapshot: float = 0.15       # opponent team: frozen past network
    p_tribute: float = 0.75        # deals that start from a random previous finishing order
    publish_every: int = 5         # updates between weight publications to actors
    snapshot_every: int = 250
    max_snapshots: int = 20
    deals_per_task: int = 8
    workers: int = 0               # 0 = cores - 1
    device: str = "auto"
    seed: int = 0


def random_match(rng: np.random.Generator, p_tribute: float) -> Match:
    """A match positioned at a random point: random team levels, whose level, previous finishing order."""
    levels = [int(rng.integers(13)), int(rng.integers(13))]
    order = [int(s) for s in rng.permutation(4)] if rng.random() < p_tribute else None
    lt = None if order is None else team(order[0])
    return Match(seed=int(rng.integers(2**31)), team_levels=levels, level_team=lt, last_order=order)


# ---- actor process ----------------------------------------------------------

_W: dict = {}


def _worker_init(cfg: DMCConfig) -> None:
    torch.set_num_threads(1)
    _W.update(cfg=cfg, nets={})


def _net(path: str, version: int) -> QNet:
    nets = _W["nets"]
    key = (path, version)
    if key not in nets:
        if len(nets) > 8:
            nets.pop(next(iter(nets)))
        nets[key] = load_net(path)
    return nets[key]


def play_task(seed: int, n_deals: int, latest: tuple[str, int], opponent: tuple[str, str, int]) -> dict:
    """Play deals; return (state, action, return) arrays for the recorded seats plus learner-team scores."""
    cfg: DMCConfig = _W["cfg"]
    rng = np.random.default_rng(seed)
    net = _net(*latest)
    kind = opponent[0]
    S, A, G, scores = [], [], [], []
    for _ in range(n_deals):
        m = random_match(rng, cfg.p_tribute)
        d = m.new_deal()
        me = int(rng.integers(2))
        agents: list[Agent] = []
        for s in range(4):
            if kind == "self" or team(s) == me:
                agents.append(DMCAgent(net, seed=int(rng.integers(2**31)), epsilon=cfg.epsilon, record=True))
            elif kind == "heuristic":
                agents.append(HeuristicAgent(seed=int(rng.integers(2**31))))
            else:
                agents.append(DMCAgent(_net(opponent[1], opponent[2]), seed=int(rng.integers(2**31))))
        for t in m.pending_returns:
            m.give_return(t.receiver, agents[t.receiver].choose_return(d.hands[t.receiver], d.level))
        while not d.done:
            obs = d.observation(d.to_act)
            d.play(obs["legal"][agents[d.to_act].act(obs)])
        win, up = d.result()
        scores.append(up if win == me else -up)
        for s, ag in enumerate(agents):
            if isinstance(ag, DMCAgent) and ag.record and ag.states:
                S.extend(ag.states)
                A.extend(ag.actions)
                G.extend([(up if win == team(s) else -up) / REWARD_SCALE] * len(ag.states))
    return {"S": np.stack(S), "A": np.stack(A), "G": np.asarray(G, np.float32),
            "opponent": kind, "scores": scores, "deals": n_deals}


# ---- learner ----------------------------------------------------------------

def _device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def train(cfg: DMCConfig, deals: int, out: str | Path, resume: bool = False, log=print) -> QNet:
    out = Path(out)
    (out / "snapshots").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(cfg), indent=2))
    dev = _device(cfg.device)
    net = load_net(out / "model.pt") if resume and (out / "model.pt").exists() else QNet(cfg.hidden)
    net = net.to(dev).train()
    opt = torch.optim.Adam(net.parameters(), lr=cfg.lr)
    latest = out / "latest.pt"
    version = 0
    save_net(net, latest)
    snapshots: list[str] = []
    rng = np.random.default_rng(cfg.seed)
    workers = cfg.workers or max(1, (os.cpu_count() or 2) - 1)

    def opponent() -> tuple[str, str, int]:
        u = rng.random()
        if u < cfg.p_heuristic:
            return "heuristic", "", 0
        if u < cfg.p_heuristic + cfg.p_snapshot and snapshots:
            return "snapshot", snapshots[int(rng.integers(len(snapshots)))], 0
        return "self", "", 0

    buf_s, buf_a, buf_g, buffered = [], [], [], 0
    vs_heur: deque = deque(maxlen=2000)
    vs_snap: deque = deque(maxlen=2000)
    losses: deque = deque(maxlen=50)
    submitted = done_deals = updates = 0
    t0 = last_log = time.time()
    with ProcessPoolExecutor(workers, initializer=_worker_init, initargs=(cfg,)) as pool:
        inflight = set()

        def submit():
            nonlocal submitted
            inflight.add(pool.submit(play_task, int(rng.integers(2**31)), cfg.deals_per_task,
                                     (str(latest), version), opponent()))
            submitted += cfg.deals_per_task

        for _ in range(2 * workers):
            submit()
        while inflight:
            finished, _ = wait(inflight, timeout=None if buffered < cfg.batch else 0, return_when=FIRST_COMPLETED)
            for f in finished:
                inflight.discard(f)
                r = f.result()
                done_deals += r["deals"]
                if r["opponent"] == "heuristic":
                    vs_heur.extend(r["scores"])
                elif r["opponent"] == "snapshot":
                    vs_snap.extend(r["scores"])
                buf_s.append(r["S"])
                buf_a.append(r["A"])
                buf_g.append(r["G"])
                buffered += len(r["G"])
                if submitted < deals:
                    submit()
            while buffered >= cfg.batch:
                S, A, G = np.concatenate(buf_s), np.concatenate(buf_a), np.concatenate(buf_g)
                perm = rng.permutation(len(G))
                take, rest = perm[:cfg.batch], perm[cfg.batch:]
                buf_s, buf_a, buf_g, buffered = [S[rest]], [A[rest]], [G[rest]], len(rest)
                s = torch.from_numpy(S[take]).to(dev).float()
                a = torch.from_numpy(A[take]).to(dev).float()
                g = torch.from_numpy(G[take]).to(dev)
                loss = nn.functional.mse_loss(net(s, a), g)
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 40.0)
                opt.step()
                losses.append(loss.item())
                updates += 1
                if updates % cfg.publish_every == 0:
                    save_net(net, latest)
                    version += 1
                if updates % cfg.snapshot_every == 0:
                    p = out / "snapshots" / f"u{updates:07d}.pt"
                    save_net(net, p)
                    snapshots.append(str(p))
                    if len(snapshots) > cfg.max_snapshots:
                        snapshots.pop(0)  # files stay on disk; only the sampling pool shrinks
                    save_net(net, out / "model.pt", updates=updates, deals=done_deals)
            if time.time() - last_log > 30 or not inflight:
                last_log = time.time()
                el = last_log - t0
                mean = lambda q: f"{np.mean(q):+.3f}" if q else "  n/a"
                log(f"deals {done_deals:>9,}  {done_deals / el:6.0f}/s  updates {updates:>6}  "
                    f"loss {np.mean(losses) if losses else float('nan'):.4f}  "
                    f"vs heuristic {mean(vs_heur)}  vs snapshots {mean(vs_snap)} (levels/deal)")
                with open(out / "metrics.jsonl", "a") as fh:
                    fh.write(json.dumps({"time": el, "deals": done_deals, "updates": updates,
                                         "loss": float(np.mean(losses)) if losses else None,
                                         "vs_heuristic": float(np.mean(vs_heur)) if vs_heur else None,
                                         "vs_snapshots": float(np.mean(vs_snap)) if vs_snap else None}) + "\n")
    save_net(net, out / "model.pt", updates=updates, deals=done_deals)
    return net
