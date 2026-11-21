import sys
from pathlib import Path

import pytest
import torch

from guandan.rl.compact import pack, unpack
from guandan.rl.policy import Actor, Critic, load_policy, save_policy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compact_models import compact  # noqa: E402


def test_int8_round_trip_is_close_and_small():
    torch.manual_seed(0)
    w = torch.randn(64, 300)
    back = unpack(pack({"w": w, "b": torch.randn(64), "n": torch.arange(5)}, "int8"))
    assert (back["w"] - w).abs().max() <= w.abs().amax(1).max() / 127 / 2 + 1e-6       # within half a quantisation step of its row
    assert back["b"].dtype == torch.float32 and back["n"].dtype == torch.int64             # small and integer tensors are kept exactly
    assert unpack(pack({"w": w}, "fp16"))["w"].allclose(w, atol=1e-2)


def test_compact_policy_loads_and_keeps_its_moves(tmp_path):
    torch.manual_seed(1)
    a, c = Actor(128, 5), Critic(128, 5)
    full, small = tmp_path / "full.pt", tmp_path / "small.pt"
    save_policy(a, c, full)
    before, after = compact(str(full), str(small), "int8")
    assert after < before / 3
    b = load_policy(small)
    s, m = torch.randint(0, 2, (2755,)).float(), torch.randint(0, 2, (9, a.action[0].in_features)).float()
    with torch.no_grad():
        p, q = torch.softmax(a.move_logits(s, m), -1), torch.softmax(b.move_logits(s, m), -1)
    assert (p - q).abs().max() < 0.05
    with pytest.raises(ValueError):                      # a compact policy has no critic: it cannot be trained further
        load_policy(small, critic=True)
