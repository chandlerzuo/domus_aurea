"""Write a smaller copy of a policy checkpoint for committing/shipping (weights stored as float16).

  python scripts/export_policy.py runs/v2a/model.pt runs/ppo/model.pt
  python scripts/export_policy.py runs/v2a/model.pt runs/ppo/model.pt --actor-only   # inference only

Loading casts the weights back to float32, so everything (play, search, review, continuing training
from it) works unchanged; the rounding changes action probabilities by well under 1%.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--actor-only", action="store_true", help="drop the critic (training value function)")
    a = ap.parse_args()
    ck = torch.load(a.src, map_location="cpu", weights_only=True)
    half = lambda sd: {k: v.half() if v.is_floating_point() else v for k, v in sd.items()}
    out = {k: v for k, v in ck.items() if k not in ("actor", "critic")}
    out["actor"] = half(ck["actor"])
    if not a.actor_only:
        out["critic"] = half(ck["critic"])
    torch.save(out, a.dst)
    mb = lambda p: Path(p).stat().st_size / 2**20
    print(f"{a.src} ({mb(a.src):.1f} MB) -> {a.dst} ({mb(a.dst):.1f} MB)")
