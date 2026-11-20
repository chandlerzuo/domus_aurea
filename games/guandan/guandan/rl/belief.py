"""A dedicated hidden-hand guesser.

The policy's belief head is a side task (weight 0.05) on a shared embedding. This network does only that: from the same
features as the policy (feature version 5, which includes the full play so far in summary, the last 16 plays and the
other players' behaviour counters) it predicts, for the next / partner / previous player, which cards they hold. It is trained
by supervised learning on millions of self-play positions where the real hands are known, so it can be much better trained
than the side head. `search.belief_probs` can use it to deal sampled hidden hands.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch import nn

from .features import encode_state, state_dim
from .policy import ORACLE_DIM


class BeliefNet(nn.Module):
    def __init__(self, hidden: int = 1024, version: int = 5, layers: int = 3):
        super().__init__()
        self.hidden, self.version, self.layers = hidden, version, layers
        mods: list[nn.Module] = []
        d = state_dim(version)
        for _ in range(layers):
            mods += [nn.Linear(d, hidden), nn.ReLU()]
            d = hidden
        self.body = nn.Sequential(*mods)
        self.out = nn.Linear(hidden, ORACLE_DIM)

    def forward(self, s: torch.Tensor) -> torch.Tensor:
        return self.out(self.body(s))                    # logits over (3 players x 54 types x 2 copy bits)


def save_belief(net: BeliefNet, path: str | Path, **extra) -> None:
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    torch.save({"hidden": net.hidden, "version": net.version, "layers": net.layers,
                "state": {k: v.detach().cpu() for k, v in net.state_dict().items()}, **extra}, tmp)
    tmp.replace(path)


def load_belief(path: str | Path, device: str = "cpu") -> BeliefNet:
    ck = torch.load(path, map_location=device, weights_only=True)
    net = BeliefNet(ck["hidden"], ck["version"], ck.get("layers", 3))
    net.load_state_dict(ck["state"])
    return net.to(device).eval()


def belief_from_net(net: BeliefNet, obs: dict) -> np.ndarray:
    """(3, 54): the chance that the next / partner / previous player holds at least one copy of each card type."""
    s = torch.from_numpy(encode_state(obs, net.version)).float()[None]
    with torch.no_grad():
        return torch.sigmoid(net(s))[0].numpy().reshape(3, -1)[:, 0::2]
