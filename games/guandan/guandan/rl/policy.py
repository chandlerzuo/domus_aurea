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
from .features import ACTION_DIM, CARD_DIM, STATE_DIM, action_dim, card_vec, encode_actions, encode_state, state_dim

ORACLE_DIM = 3 * CARD_DIM
DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "runs" / "ppo" / "model.pt"


def encode_oracle(hands: list[list[int]], seat: int) -> np.ndarray:
    """Hidden hands of the next, partner and previous player (relative to `seat`)."""
    x = np.zeros(ORACLE_DIM, np.uint8)
    for k in range(3):
        card_vec(hands[(seat + 1 + k) % 4], x[k * CARD_DIM:(k + 1) * CARD_DIM])
    return x


class Actor(nn.Module):
    def __init__(self, hidden: int = 512, version: int = 1):
        super().__init__()
        self.hidden, self.version = hidden, version
        self.state = nn.Sequential(nn.Linear(state_dim(version), hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.action = nn.Sequential(nn.Linear(action_dim(version), 256), nn.ReLU())
        self.score = nn.Sequential(nn.Linear(hidden + 256, 256), nn.ReLU(), nn.Linear(256, 1))
        self.belief = nn.Linear(hidden, ORACLE_DIM)

    def _score(self, hp: torch.Tensor, ea: torch.Tensor) -> torch.Tensor:
        """score([h, e]) with the first layer split: W [h, e] + b = W_h h + (W_e e + b). `hp` is the
        state half W_h h (computed once per state), `ea` the embedded moves (one row per move)."""
        l1, l2 = self.score[0], self.score[2]
        z = torch.relu(hp + nn.functional.linear(ea, l1.weight[:, self.hidden:], l1.bias))
        return l2(z).squeeze(-1)

    def logits(self, hs: torch.Tensor, a: torch.Tensor, seg: torch.Tensor) -> torch.Tensor:
        """hs (B, H) state embeddings, a (M, A) flat legal moves, seg (M,) owning state -> (M,) logits."""
        hp = nn.functional.linear(hs, self.score[0].weight[:, :self.hidden])
        return self._score(hp[seg], self.action(a))

    def move_logits(self, s: torch.Tensor, a: torch.Tensor) -> torch.Tensor:
        """One state (S,) against its n legal moves (n, A)."""
        hp = nn.functional.linear(self.state(s[None]), self.score[0].weight[:, :self.hidden])
        return self._score(hp, self.action(a))


class Critic(nn.Module):
    def __init__(self, hidden: int = 512, version: int = 1):
        super().__init__()
        self.version = version
        self.net = nn.Sequential(nn.Linear(state_dim(version) + ORACLE_DIM, hidden), nn.ReLU(),
                                 nn.Linear(hidden, hidden), nn.ReLU(),
                                 nn.Linear(hidden, 256), nn.ReLU(), nn.Linear(256, 1))

    def forward(self, s: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([s, o], -1)).squeeze(-1)


def widen_policy(actor: Actor, critic: Critic, version: int) -> tuple[Actor, Critic]:
    """The same networks with version-`version` inputs. The new input columns start at zero weight,
    so the widened policy plays exactly like the original until training uses them."""
    if version == actor.version:
        return actor, critic
    assert version > actor.version, "can only widen to a newer feature version"
    na, nc = Actor(actor.hidden, version), Critic(actor.hidden, version)
    old, new = actor.state_dict(), na.state_dict()
    for k, v in old.items():
        if v.shape == new[k].shape:
            new[k] = v.clone()
    for k, dim in (("state.0.weight", STATE_DIM), ("action.0.weight", ACTION_DIM)):
        new[k] = torch.zeros_like(new[k])
        new[k][:, :dim] = old[k]
    na.load_state_dict(new)
    old, new = critic.state_dict(), nc.state_dict()
    for k, v in old.items():
        if v.shape == new[k].shape:
            new[k] = v.clone()
    w = torch.zeros_like(new["net.0.weight"])  # inputs are [state | oracle]
    extra = state_dim(version) - STATE_DIM
    w[:, :STATE_DIM] = old["net.0.weight"][:, :STATE_DIM]
    w[:, STATE_DIM + extra:] = old["net.0.weight"][:, STATE_DIM:]
    new["net.0.weight"] = w
    nc.load_state_dict(new)
    return na.eval() if not actor.training else na, nc.eval() if not critic.training else nc


def padded_log_probs(logits: torch.Tensor, seg: torch.Tensor, pos: torch.Tensor, batch: int, width: int):
    """Flat per-move logits -> (batch, width) log-probabilities; padding gets probability 0."""
    pad = logits.new_full((batch, width), -1e9)
    pad[seg, pos] = logits
    return torch.log_softmax(pad, -1)


def save_policy(actor: Actor, critic: Critic, path: str | Path, **extra) -> None:
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    cpu = lambda m: {k: v.detach().cpu() for k, v in m.state_dict().items()}
    torch.save({"hidden": actor.hidden, "version": actor.version, "actor": cpu(actor), "critic": cpu(critic), **extra}, tmp)
    os.replace(tmp, path)  # actors may be reading the file


def load_policy(path: str | Path, device: str = "cpu", critic: bool = False):
    ckpt = torch.load(path, map_location=device, weights_only=True)
    version = ckpt.get("version", 1)
    actor = Actor(ckpt["hidden"], version)
    actor.load_state_dict(ckpt["actor"])
    actor = actor.to(device).eval()
    if not critic:
        return actor
    c = Critic(ckpt["hidden"], version)
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
        v = self.actor.version
        i, _, p = policy_step(self.actor, encode_state(obs, v), encode_actions(obs, v), self.rng, self.greedy)
        top = np.argsort(-p)[:3]
        self.info = {"policy": {f"{legal[j].combo} x{len(legal[j].cards)}": round(float(p[j]), 2) for j in top}}
        return i
