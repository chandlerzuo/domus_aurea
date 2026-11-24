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


def test_a_guesser_in_front_of_the_policy_changes_nothing_at_first_and_survives_saving(tmp_path):
    from guandan.rl.belief import BeliefNet
    from guandan.rl.policy import add_guesser
    torch.manual_seed(2)
    a, c = Actor(64, 5), Critic(64, 5)
    g = BeliefNet(48, 5, 2)
    a2, _ = add_guesser(a, c, g)
    s = torch.randint(0, 2, (3, 2755)).float()
    m = torch.randint(0, 2, (7, a.action[0].in_features)).float()
    with torch.no_grad():
        assert torch.allclose(a.state(s), a2.state(s), atol=1e-6)                              # the new inputs start at zero weight
        assert all(not p.requires_grad for p in g.parameters())                                 # the guesser stays frozen
    a2.state[0].weight.data[:, 2755:] = 0.05                                                    # pretend training used the guesses
    save_policy(a2, c, tmp_path / "g.pt")
    b = load_policy(tmp_path / "g.pt")
    assert b.state[0].guesser is not None
    with torch.no_grad():
        assert torch.allclose(a2.move_logits(s[0], m), b.move_logits(s[0], m), atol=1e-6)
        assert not torch.allclose(a.move_logits(s[0], m), b.move_logits(s[0], m), atol=1e-4)  # and the guesses now matter
