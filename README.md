# guandan

Guandan (掼蛋), the four-player partnership shedding game, with:

1. a complete rules engine and a local web app where you log in and play
   with a computer partner against two computer opponents;
2. computer players trained by self-play reinforcement learning (Deep
   Monte-Carlo, as in DouZero / DanZero), plus a survey of the training
   techniques that apply, including the ones from the sibling `poker_ai`
   project ([docs/TECHNIQUES.md](docs/TECHNIQUES.md)).

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

## Play

```bash
.venv/bin/python -m guandan.server          # http://127.0.0.1:8770
```

Register a username and password, pick the partner and opponent agents
(`heuristic`, `random`, and `dmc` once a model exists in `runs/dmc/model.pt`),
and start a match. Click cards to select them, then Play; Hint suggests a move.
You are seat 0, your partner sits opposite, and play passes to your right.

Accounts live in `data/users.db` (scrypt-hashed passwords; sessions are
in-memory HttpOnly, SameSite=Strict cookies, so restarting the server logs
everyone out). The server listens on loopback only and rejects requests whose
Host header isn't loopback. To play from another machine, use an SSH tunnel
(`ssh -L 8770:127.0.0.1:8770 <host>`) instead of widening the bind. Exposing
it more widely would need HTTPS and a proper deployment review first.

## Rules implemented

| | |
|---|---|
| Deck | 2 × 52 cards + 4 jokers, 27 cards each |
| Level rank | ranks above A (below the jokers) for singles/pairs/triples/full houses/bombs; natural place in sequences |
| Wilds | the two hearts of the level rank substitute for any non-joker card |
| Combos | single, pair, triple, full house (3+2), straight (5), tube (3 consecutive pairs), plate (2 consecutive triples) |
| Bombs | 4 < 5 < straight flush < 6 < 7 < 8 < 9 < 10 of a kind < four jokers |
| Sequences | A low (A2345) or high (TJQKA), no wrap-around |
| Trick play | beat with the same kind or a bomb, or pass; if a player goes out and nobody answers, their partner leads |
| Scoring | team of the first finisher goes up 3 / 2 / 1 if the partner finished 2nd / 3rd / 4th |
| Tribute | last → first (both losers pay when they finish 3rd and 4th); return a card ≤ 10; both big jokers among the payers cancel it |
| Match | won by winning a deal at your own level A with your partner not last |

Not implemented: the house rule that resets a team to 2 after three failed
attempts at A. When a set of cards can be read in more than one way
(e.g. `333 + two wilds` = full house or 5-bomb), following plays use the
matching kind, and leads use the strongest reading.

## Agents

| Agent | |
|---|---|
| `random` | uniform over legal moves |
| `heuristic` | rule-based: sheds low, long combos without breaking bombs or pairs, never overtakes its partner, saves bombs and big cards for when an opponent is close to going out |
| `dmc` | Q-network over (state, move) trained by Deep Monte-Carlo self-play (`guandan/rl/dmc.py`) |
| `ppo` | policy network warm-started by imitating the heuristic, then fine-tuned with PPO using a critic that sees all four hands during training only, plus a hidden-hand prediction head (`guandan/rl/policy.py`, `guandan/rl/ppo.py`) |

Duplicate-deal results (2,000 deals each, levels per deal for the first agent):

| Matchup | Levels/deal | Deals won |
|---|---|---|
| ppo vs heuristic | **+0.57 ± 0.05** | 55.5% |
| ppo vs dmc | **+1.29 ± 0.05** | 71.2% |
| dmc vs heuristic | −0.11 ± 0.05 | 45.5% |
| bc (imitation only) vs heuristic | −1.26 ± 0.05 | 26.1% |
| heuristic vs random | +2.9 | 99% |

Imitation alone matches the heuristic's move 83% of the time but plays much
worse than it, because small mistakes compound over a deal. Its value is as a
starting point: PPO from that start passes the heuristic within 1M deals,
while DMC from scratch did not.

```bash
# DMC (actors in parallel processes, learner on Apple GPU/CUDA if available)
.venv/bin/python scripts/train_dmc.py --deals 1000000 --out runs/dmc
.venv/bin/python scripts/train_dmc.py --deals 5000000 --out runs/dmc --resume

# Imitation warm start (200k heuristic deals, ~10 min) then PPO (1M deals, ~1h45 on 12 actors)
.venv/bin/python scripts/train_ppo.py --bc-deals 200000 --ppo-deals 1000000 --out runs/ppo
.venv/bin/python scripts/train_ppo.py --bc-deals 0 --ppo-deals 2000000 --resume

# Duplicate-deal evaluation (same cards played twice, teams swapped)
.venv/bin/python scripts/evaluate.py --a ppo --b heuristic --pairs 1000
```

Both trainers mix opponents the way poker_ai's PPO league does: mostly the
current network against itself, plus the heuristic baseline, frozen past
snapshots and (for PPO) the DMC model. Each deal starts from a random point in a match (random levels and
a previous finishing order, so tribute happens), so the network sees every
level rank. Progress goes to `runs/dmc/metrics.jsonl`; only `model.pt`,
`bc.pt` and `config.json` are tracked in git.

## Layout

| Path | Contents |
|---|---|
| `guandan/cards.py` | card ids, level-aware values, parsing |
| `guandan/combos.py` | combo kinds, comparison, classification with wilds, legal-move generation |
| `guandan/game.py` | `Deal` (one hand of play) and `Match` (levels, tribute, match end) |
| `guandan/agents.py` | random and heuristic agents |
| `guandan/evaluate.py` | duplicate-deal head-to-head |
| `guandan/rl/` | feature encoding; DMC Q-network and trainer; policy/critic networks, imitation and PPO trainer |
| `guandan/server/` | HTTP server, accounts, single-page UI |
| `docs/TECHNIQUES.md` | which model-training techniques fit Guandan, and the roadmap |

## Roadmap

See [docs/TECHNIQUES.md](docs/TECHNIQUES.md#roadmap): PIMC test-time search
on top of the PPO policy, a learned tribute-return choice, longer PPO runs, and
a Rust move generator for faster self-play.
