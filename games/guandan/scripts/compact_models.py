"""Write smaller copies of model files: int8 (default) or fp16 weights, and no critic.

  python scripts/compact_models.py runs/all3/model.pt runs/ppo/model.pt            # SRC DST
  python scripts/compact_models.py --mode fp16 runs/seq/s1.pt runs/ppo/seq_guesser.pt

Handles the policy files (rl/policy.py), the sequence guesser (rl/seqbelief.py), the MLP guesser (rl/belief.py) and the DMC network
(rl/dmc.py). The compact file loads into an ordinary float32 network (see rl/compact.py). Keep the originals if you want to keep
training: a compact policy has no critic.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402

from guandan.rl.compact import pack, state_of  # noqa: E402


def compact(src: str, dst: str, mode: str) -> tuple[int, int]:
    ck = torch.load(src, map_location="cpu", weights_only=True)
    if ck.get("quant"):
        raise SystemExit(f"{src} is already compact")
    out = {k: v for k, v in ck.items() if k not in ("actor", "critic", "state")}
    if "actor" in ck:                                    # a policy: keep the actor, drop the critic
        out["actor"] = pack(ck["actor"], mode)
    elif "state" in ck:                                  # a guesser or a DMC network
        out["state"] = pack(ck["state"], mode)
    else:
        raise SystemExit(f"{src}: unrecognised checkpoint")
    out["quant"] = mode
    tmp = Path(dst).with_suffix(".tmp")
    torch.save(out, tmp)
    tmp.replace(dst)
    return Path(src).stat().st_size, Path(dst).stat().st_size


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--mode", choices=("int8", "fp16"), default="int8")
    a = ap.parse_args()
    before, after = compact(a.src, a.dst, a.mode)
    print(f"{a.src}: {before / 1e6:.2f} MB -> {a.dst}: {after / 1e6:.2f} MB ({after / before:.0%}, {a.mode})")


if __name__ == "__main__":
    main()
