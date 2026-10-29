"""Policy over legal moves (with a belief head) and an oracle critic, for imitation + PPO.

Actor: embeds the state once, scores each legal move with f(state, move), and
takes a softmax over the legal set, so the action space can be any size. A
belief head predicts the three hidden hands from the state embedding; it is
trained as an auxiliary loss (the simulator knows the true hands) to shape the
representation.

Critic: sees the state *and* the three hidden hands (perfect-information
training, imperfect-information execution, as in PerfectDou). Only the actor
is needed to play, so the trained agent never uses information a real player
would not have.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch
from torch import nn

from ..agents import Agent
from .features import ACTION_DIM, CARD_DIM, STATE_DIM, card_vec, encode_actions, encode_state

ORACLE_DIM = 3 * CARD_DIM
DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "runs" / "ppo" / "model.pt"


def encode_oracle(hands: list[list[int]], seat: int) -> np.ndarray:
    """Hidden hands of the next, partner and previous player (relative to `seat`)."""
    x = np.zeros(ORACLE_DIM, np.uint8)
    for k in range(3):
        card_vec(hands[(seat + 1 + k) % 4], x[k * CARD_DIM:(k + 1) * CARD_DIM])
    return x


class Actor(nn.Module):
    def __init__(self, hidden: int = 512):
        super().__init__()
        self.hidden = hidden
        self.state = nn.Sequential(nn.Linear(STATE_DIM, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.action = nn.Sequential(nn.Linear(ACTION_DIM, 256), nn.ReLU())
        self.score = nn.Sequential(nn.Linear(hidden + 256, 256), nn.ReLU(), nn.Linear(256, 1))
        self.belief = nn.Linear(hidden, ORACLE_DIM)

    def logits(self, hs: torch.Tensor, a: torch.Tensor, seg: torch.Tensor) -> torch.Tensor:
        """hs (B, H) state embeddings, a (M, A) flat legal moves, seg (M,) owning state -> (M,) logits."""
        return self.score(torch.cat([hs[seg], self.action(a)], -1)).squeeze(-1)

    def move_logits(self, s: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
        """One state (S,) against its n legal moves (n, A)."""
        hs = self.state(s[None]).expand(a.shape[0], -1)
        return self.score(torch.cat([hs, self.action(a)], -1)).squeeze(-1)


class Critic(nn.Module):
    def __init__(self, hidden: int = 512):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(STATE_DIM + ORACLE_DIM, hidden), nn.ReLU(),
                                 nn.Linear(hidden, hidden), nn.ReLU(),
                                 nn.Linear(hidden, 256), nn.ReLU(), nn.Linear(256, 1))

    def forward(self, s: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([s, o], -1)).squeeze(-1)


def padded_log_probs(logits: torch.Tensor, seg: torch.Tensor, pos: torch.Tensor, batch: int, width: int):
    """Flat per-move logits -> (batch, width) log-probabilities; padding gets probability 0."""
    pad = logits.new_full((batch, width), -1e9)
    pad[seg, pos] = logits
    return torch.log_softmax(pad, -1)


def save_policy(actor: Actor, critic: Critic, path: str | Path, **extra) -> None:
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    cpu = lambda m: {k: v.detach().cpu() for k, v in m.state_dict().items()}
    torch.save({"hidden": actor.hidden, "actor": cpu(actor), "critic": cpu(critic), **extra}, tmp)
    os.replace(tmp, path)  # actors may be reading the file


def load_policy(path: str | Path, device: str = "cpu", critic: bool = False):
    ckpt = torch.load(path, map_location=device, weights_only=True)
    actor = Actor(ckpt["hidden"])
    actor.load_state_dict(ckpt["actor"])
    actor = actor.to(device).eval()
    if not critic:
        return actor
    c = Critic(ckpt["hidden"])
    c.load_state_dict(ckpt["critic"])
    return actor, c.to(device).eval()


def policy_step(actor: Actor, s: np.ndarray, a: np.ndarray, rng: np.random.Generator,
                greedy: bool = False) -> tuple[int, float, np.ndarray]:
    """Pick a move index; returns (index, log-prob, probabilities)."""
    with torch.no_grad():
        lg = actor.move_logits(torch.from_numpy(s).float(), torch.from_numpy(a).float())
        p = torch.softmax(lg, -1).numpy().astype(float)
    p /= p.sum()
    i = int(p.argmax()) if greedy else int(rng.choice(len(p), p=p))
    return i, float(np.log(p[i] + 1e-12)), p


class PolicyAgent(Agent):
    name = "ppo"

    def __init__(self, actor: Actor | None = None, seed: int | None = None, greedy: bool = True,
                 path: str | Path = DEFAULT_POLICY):
        super().__init__(seed)
        self.actor = actor if actor is not None else load_policy(path)
        self.greedy = greedy

    def act(self, obs: dict) -> int:
        legal = obs["legal"]
        if len(legal) == 1:
            return 0
        i, _, p = policy_step(self.actor, encode_state(obs), encode_actions(obs), self.rng, self.greedy)
        top = np.argsort(-p)[:3]
        self.info = {"policy": {f"{legal[j].combo} x{len(legal[j].cards)}": round(float(p[j]), 2) for j in top}}
        return i
