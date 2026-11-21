"""Compact model files: weights stored as 8-bit integers (or 16-bit floats), expanded back to float32 when loaded.

Each weight matrix gets one scale per output row (symmetric, so zero stays zero); biases, norms and other small tensors stay
float32. A loaded model is an ordinary float32 network, so inference code and speed are unchanged; only the file is smaller
(about a quarter of the size for int8, a half for fp16). Training needs the original float32 checkpoints.
"""
from __future__ import annotations

import torch

MIN_ELEMENTS = 1024      # smaller tensors are kept exactly


def pack(state: dict, mode: str = "int8") -> dict:
    """A state dict of tensors -> a dict that torch.save stores compactly."""
    out = {}
    for name, w in state.items():
        w = w.detach().cpu()
        if not w.is_floating_point() or w.numel() < MIN_ELEMENTS or w.dim() < 2:
            out[name] = w
        elif mode == "fp16":
            out[name] = w.half()
        elif mode == "int8":
            flat = w.reshape(w.shape[0], -1).float()
            scale = (flat.abs().amax(1) / 127.0).clamp(min=1e-12)
            q = torch.round(flat / scale[:, None]).clamp(-127, 127).to(torch.int8)
            out[name] = {"q": q.reshape(w.shape), "s": scale}
        else:
            raise ValueError(f"unknown mode {mode!r}")
    return out


def unpack(packed: dict) -> dict:
    """The inverse of `pack`: a float32 state dict."""
    out = {}
    for name, v in packed.items():
        if isinstance(v, dict):
            q, s = v["q"], v["s"]
            out[name] = (q.reshape(q.shape[0], -1).float() * s[:, None]).reshape(q.shape)
        elif v.is_floating_point():
            out[name] = v.float()
        else:
            out[name] = v
    return out


def state_of(ckpt: dict, key: str = "state") -> dict:
    """The (float32) state dict stored under `key` in a checkpoint, whether or not the file is compact."""
    sd = ckpt[key]
    return unpack(sd) if ckpt.get("quant") else sd
