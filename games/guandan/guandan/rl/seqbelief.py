"""A sequence model for guessing the hidden hands: a transformer over the whole history of the deal.

The MLP guesser (rl/belief.py) sees the last 16 plays and some counters. This one reads every play so far, as a token each:
who played it (relative to the player who is guessing), what kind of combination, and which cards (a 108-bit set). Passes are tokens
too: who declined to answer which play is the information a person reasons from. One extra "state" token carries the guesser's own
hand, the unseen cards, what each player has played, hand sizes and the level.

Output: for the next / partner / previous player, two bits per card type ("holds at least one copy", "holds both"), the same
encoding as the oracle target used everywhere else (324 logits).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from torch import nn

from .compact import state_of

T_MAX = 192          # history tokens kept (a deal has about 100-150 plays and passes)
N_CARDS = 108
N_KIND = 11
TOKEN_DIM = N_CARDS + 4 + N_KIND
STATE_DIM = N_CARDS * 5 + 3 + 13        # own hand, unseen, played by the next / partner / previous player, their hand sizes, level
OUT_DIM = 3 * 108


class SeqBelief(nn.Module):
    def __init__(self, d: int = 256, layers: int = 4, heads: int = 8, ff: int = 1024):
        super().__init__()
        self.cfg = dict(d=d, layers=layers, heads=heads, ff=ff)
        self.tok = nn.Linear(TOKEN_DIM, d)
        self.pos = nn.Embedding(T_MAX + 1, d)
        self.state = nn.Sequential(nn.Linear(STATE_DIM, d), nn.ReLU(), nn.Linear(d, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=0.0, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers)
        self.norm = nn.LayerNorm(d)
        self.head = nn.Sequential(nn.Linear(d, 512), nn.ReLU(), nn.Linear(512, OUT_DIM))

    def forward(self, tokens: torch.Tensor, n_tok: torch.Tensor, state: torch.Tensor) -> torch.Tensor:
        """tokens (B, T, TOKEN_DIM) float, n_tok (B,) how many are real, state (B, STATE_DIM) -> logits (B, 324)."""
        B, T, _ = tokens.shape
        pos = torch.arange(1, T + 1, device=tokens.device)
        x = self.tok(tokens) + self.pos(pos)[None]
        x = torch.cat([self.state(state)[:, None], x], 1)                           # the state token comes first
        pad = torch.arange(T + 1, device=tokens.device)[None] > n_tok[:, None]       # True = padding (the state token is always real)
        x = self.enc(x, src_key_padding_mask=pad)
        return self.head(self.norm(x[:, 0]))


def save_seq(net: SeqBelief, path: str | Path, **extra) -> None:
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    torch.save({"cfg": net.cfg, "state": {k: v.detach().cpu() for k, v in net.state_dict().items()}, **extra}, tmp)
    tmp.replace(path)


def load_seq(path: str | Path, device: str = "cpu") -> SeqBelief:
    ck = torch.load(path, map_location=device, weights_only=True)
    net = SeqBelief(**ck["cfg"])
    net.load_state_dict(state_of(ck))
    return net.to(device).eval()


def obs_inputs(obs: dict):
    """Model inputs for one observation (what the guesser can see): tokens (1, T, TOKEN_DIM), n_tok (1,), state (1, STATE_DIM)."""
    seat = obs["seat"]
    hist = obs["history"][-T_MAX:]
    tok = np.zeros((1, max(1, len(hist)), TOKEN_DIM), np.float32)
    for i, (s, m) in enumerate(hist):
        for c in m.cards:
            tok[0, i, c] = 1
        tok[0, i, N_CARDS + (s - seat) % 4] = 1
        tok[0, i, N_CARDS + 4 + int(m.combo.kind)] = 1
    st = np.zeros((1, STATE_DIM), np.float32)
    for c in obs["hand"]:
        st[0, c] = 1
    seen = np.zeros(N_CARDS, np.float32)
    for c in obs["hand"]:
        seen[c] = 1
    for k in range(3):
        for c in obs["played"][(seat + 1 + k) % 4]:
            st[0, N_CARDS * (2 + k) + c] = 1
    for p in obs["played"]:
        for c in p:
            seen[c] = 1
    st[0, N_CARDS:2 * N_CARDS] = 1 - seen
    for k in range(3):
        st[0, N_CARDS * 5 + k] = obs["counts"][(seat + 1 + k) % 4] / 27.0
    st[0, N_CARDS * 5 + 3 + obs["level"]] = 1
    return torch.from_numpy(tok), torch.tensor([len(hist)]), torch.from_numpy(st)


def belief_from_seq(net: SeqBelief, obs: dict) -> np.ndarray:
    """(3, 54): the chance that the next / partner / previous player holds at least one copy of each card type."""
    tok, n, st = obs_inputs(obs)
    with torch.no_grad():
        return torch.sigmoid(net(tok, n, st))[0].numpy().reshape(3, -1)[:, 0::2]
