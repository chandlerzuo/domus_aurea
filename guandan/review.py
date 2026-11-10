"""Post-game reflection on a finished deal.

Replays a recorded deal move by move and, at each decision of the reviewed
seat, asks the trained policy how likely it was to make the same move. Moves
the policy considered clearly worse than its own top choice are flagged, and
the biggest of those are measured by rollouts: the rest of the deal is played
out many times after the player's move and after the policy's preferred move,
with the same random seeds for both, and the average results are compared.

The rollouts use the real hidden hands, so they judge with hindsight: a move
can look costly only because of cards the player could not have known about.
"""
from __future__ import annotations

import copy

import numpy as np

from .cards import card_str, ctype, value
from .combos import PASS, Combo, Kind, Move
from .game import Deal, team
from .rl.features import encode_action, encode_actions, encode_state
from .rl.policy import Actor, PolicyAgent, policy_step


def move_from_record(entry) -> Move:
    _seat, cards, kind, val, size = entry
    return PASS if kind == Kind.PASS else Move(Combo(Kind(kind), val, size), tuple(cards))


def record_move(seat: int, m: Move) -> list:
    return [seat, list(m.cards), int(m.combo.kind), m.combo.value, m.combo.size]


def start_deal(record: dict) -> Deal:
    return Deal([list(h) for h in record["hands"]], record["level"], record["leader"],
                tuple(record["team_levels"]), record["level_team"])


def lead_flags(record: dict) -> list[bool]:
    """For each recorded move, whether it started a new trick (used by the replay viewer)."""
    d = start_deal(record)
    flags = []
    for entry in record["moves"]:
        flags.append(d.leading)
        d.play(move_from_record(entry))
    return flags


def label(m: Move) -> str:
    return "pass" if m.is_pass else f"{m.combo} {' '.join(card_str(c) for c in m.cards)}"


def _signature(m: Move, level: int) -> tuple:
    """Move identity ignoring which physical copy / suit was used (except for straight flushes)."""
    if m.combo.kind == Kind.STRAIGHT_FLUSH:
        return m.combo, tuple(sorted(ctype(c) for c in m.cards))
    return m.combo, tuple(sorted(value(ctype(c), level) for c in m.cards))


def _rollout(deal: Deal, move: Move, actor: Actor, seed: int, seat: int) -> float:
    d = copy.deepcopy(deal)
    d.play(move)
    rng = np.random.default_rng(seed)
    agents = [PolicyAgent(actor, seed=int(rng.integers(2**31)), greedy=False) for _ in range(4)]
    while not d.done:
        obs = d.observation(d.to_act)
        d.play(obs["legal"][agents[d.to_act].act(obs)])
    win, up = d.result()
    return float(up if win == team(seat) else -up)


def review_deal(record: dict, actor: Actor, seat: int = 0, rollouts: int = 24, max_flagged: int = 6,
                seed: int = 0, label_fn=None) -> dict:
    label_fn = label_fn or label
    rng = np.random.default_rng(seed)
    d = start_deal(record)
    level = record["level"]
    decisions = []
    for step, entry in enumerate(record["moves"]):
        mover, played = entry[0], move_from_record(entry)
        if mover == seat:
            obs = d.observation(seat)
            legal = list(obs["legal"])
            if len(legal) > 1:
                sig = _signature(played, level)
                idx = next((i for i, m in enumerate(legal) if _signature(m, level) == sig), None)
                acts = encode_actions(obs, actor.version)
                if idx is None:  # e.g. the player used a wild where the generator would not
                    legal.append(played)
                    acts = np.vstack([acts, encode_action(played, len(obs["hand"]), level)])
                    idx = len(legal) - 1
                _, _, p = policy_step(actor, encode_state(obs, actor.version), acts, rng, greedy=True)
                best = int(p.argmax())
                decisions.append({
                    "step": step, "played": label_fn(played), "p_played": round(float(p[idx]), 3),
                    "best": label_fn(legal[best]), "p_best": round(float(p[best]), 3), "agrees": best == idx,
                    "flag": bool(best != idx and p[idx] < 0.5 * p[best]),
                    "_deal": copy.deepcopy(d), "_moves": (played, legal[best]),
                })
        d.play(played)
    flagged = sorted((x for x in decisions if x["flag"]), key=lambda x: x["p_best"] - x["p_played"], reverse=True)
    for x in flagged[:max_flagged]:
        seeds = [int(s) for s in rng.integers(2**31, size=rollouts)]
        mine = [_rollout(x["_deal"], x["_moves"][0], actor, s, seat) for s in seeds]
        alt = [_rollout(x["_deal"], x["_moves"][1], actor, s, seat) for s in seeds]
        diff = np.subtract(mine, alt)
        x["impact"] = round(float(diff.mean()), 2)          # levels; negative = your move did worse
        x["impact_se"] = round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 2)
    for x in decisions:
        x.pop("_deal"), x.pop("_moves")
    win, up = d.result()
    n = len(decisions)
    return {
        "seat": seat, "decisions": decisions, "flagged": [x["step"] for x in flagged],
        "agreement": round(sum(x["agrees"] for x in decisions) / n, 3) if n else None,
        "result": up if win == team(seat) else -up, "rollouts": rollouts,
        "note": "Rollouts replay the rest of the deal with the real hidden hands (hindsight).",
    }
