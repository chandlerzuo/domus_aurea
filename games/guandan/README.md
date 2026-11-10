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

The Rust core is optional but recommended: self-play runs about 6× faster per core (training
as a whole is limited by the learner, about 1.5-2× faster), and the search player (`ppo+`) needs it. Without it everything still works on the Python engine.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh      # once, if you have no Rust toolchain
.venv/bin/pip install maturin && (cd rust && ../.venv/bin/maturin develop --release)
```

`rust/` has the rules engine, the legal-move generator and the feature encoders. They are tested
to give exactly the same moves and inputs as the Python code (`tests/test_rust.py`);
`GUANDAN_ENGINE=python` forces the Python engine.

## Play

```bash
.venv/bin/python -m guandan.server          # http://127.0.0.1:8770, 10 tables
```

The web app is in Chinese (掼蛋 terms: 逢人配, 进贡/还贡, 头游…末游); the
Chinese text lives in `guandan/server/zh.py` and the page script, while the
engine and training code stay in English.

- **Tables:** sit at an open table to host it. The host fills empty seats with
  AI players (`ppo+`, `ppo`, `dmc`, `heuristic`, `random`) or waits for friends to take
  them (first come, first served), then starts the match. Partners sit opposite
  (South/North vs East/West).
- **AI suggestions:** each player chooses when sitting down whether to see the
  policy's top three moves with probabilities on their turn. Clicking one
  selects those cards. Deals played with suggestions on are marked in the deal
  list.
- **Watching:** watch any table from one seat's point of view. You only see
  that seat's cards. Watch links look like `#watch-<table>-<seat>`.
- **Replay and review:** every finished deal is saved (`data/games.db`) and can
  be stepped through with all hands shown. "Review with the AI" scores each
  of a player's decisions with the PPO policy, flags the moves it disliked, and
  estimates what they cost by playing the rest of the deal out after the
  player's move and after the policy's preferred move. The rollouts use the real
  hidden hands, so the estimate is a hindsight judgement and is labelled as
  one.
- **Leaving:** an AI takes over a player who leaves, closes the tab for 90 s,
  or doesn't act for 5 minutes, so the others can keep playing.

There are no accounts. The server only listens on loopback by default, and
refuses wildcard and public addresses. To play on a cloud machine with friends,
either reach it over an SSH tunnel or Tailscale/WireGuard, or run the setup with
`--public`. That puts nginx in front, with HTTPS and a shared password, so
anyone with the password can just open the address in a browser.
[docs/SERVER_SPEC.md](docs/SERVER_SPEC.md) has the step-by-step setup. See
[docs/DEPLOY.md](docs/DEPLOY.md), which also has the capacity measurements
behind the 10-table default (`scripts/loadtest.py`). For a Tencent Cloud
Lighthouse server that can't reach GitHub, build an offline bundle with
`deploy/make_bundle.sh`, copy it over, and run `deploy/setup_lighthouse.sh` on
the server.

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
| `ppo` | policy network warm-started by imitating the heuristic, then fine-tuned with PPO using a critic that sees all four hands during training only, plus a hidden-hand prediction head (`guandan/rl/policy.py`, `guandan/rl/ppo.py`). The shipped model uses feature version 2 (below) |
| `ppo+` | the `ppo` policy plus look-ahead search at every decision (`guandan/rl/search.py`, Rust core required): it samples the hidden hands, plays its top moves out to the end of the deal on each sample, and keeps the move that does best. It is the default AI when available |

Duplicate-deal results (levels per deal for the first agent; 1,000 deals each unless noted):

| Matchup | Levels/deal | Deals won |
|---|---|---|
| ppo (v2 features, shipped) vs heuristic | **+1.95 ± 0.06** | 85.0% |
| ppo (v2) vs dmc | **+2.33 ± 0.05** | 91.6% |
| ppo (v2) vs the previous ppo (`runs/ppo/v1.pt`) | **+1.66 ± 0.06** | 81.6% |
| ppo+ (search, 32 worlds, top 4) vs the same ppo, 480 deals | **+0.32 ± 0.11** | 53.5% |
| previous ppo (v1) vs heuristic, 2,000 deals | +0.57 ± 0.05 | 55.5% |
| previous ppo (v1) vs dmc, 2,000 deals | +1.29 ± 0.05 | 71.2% |
| dmc vs heuristic, 2,000 deals | −0.11 ± 0.05 | 45.5% |
| bc (imitation only) vs heuristic, 2,000 deals | −1.26 ± 0.05 | 26.1% |
| heuristic vs random | +2.9 | 99% |

Search helps more on weaker policies: on the previous ppo it added +0.88 ± 0.09 (64% of
deals), on the v2 policy +0.32 ± 0.11. It costs about 30-50 ms per decision on one core
(`scripts/evaluate_search.py`).

Imitation alone matches the heuristic's move 83% of the time but plays much
worse than it, because small mistakes compound over a deal. Its value is as a
starting point: PPO from that start passes the heuristic within 1M deals,
while DMC from scratch did not.

```bash
# DMC (actors in parallel processes, learner on Apple GPU/CUDA if available)
.venv/bin/python scripts/train_dmc.py --deals 1000000 --out runs/dmc
.venv/bin/python scripts/train_dmc.py --deals 5000000 --out runs/dmc --resume

# Imitation warm start (200k heuristic deals) then PPO
.venv/bin/python scripts/train_ppo.py --bc-deals 200000 --ppo-deals 1000000 --out runs/ppo
.venv/bin/python scripts/train_ppo.py --bc-deals 0 --ppo-deals 2000000 --out runs/ppo --resume

# Feature version 2, starting from an older policy: the new input columns start at zero weight,
# so it plays exactly like the old one until training uses them (about 200 deals/s with the Rust core)
.venv/bin/python scripts/train_ppo.py --bc-deals 0 --ppo-deals 3000000 --init runs/ppo/v1.pt --version 2 \
    --lr 1e-4 --workers 10 --out runs/v2

# Shrink a checkpoint for committing (float16, same play), and measure search
.venv/bin/python scripts/export_policy.py runs/v2/model.pt runs/ppo/model.pt
.venv/bin/python scripts/evaluate_search.py --model runs/ppo/model.pt --pairs 240 --worlds 32 --topk 4

# Duplicate-deal evaluation (same cards played twice, teams swapped)
.venv/bin/python scripts/evaluate.py --a ppo --b heuristic --pairs 1000
```

Both trainers mix opponents the way poker_ai's PPO league does: mostly the
current network against itself, plus the heuristic baseline, frozen past
snapshots and (for PPO) the DMC model. Each deal starts from a random point in a match (random levels and
a previous finishing order, so tribute happens), so the network sees every
level rank. Progress goes to `runs/dmc/metrics.jsonl`; only `model.pt`,
`bc.pt`, `v1.pt` (the previous model) and `config.json` are tracked in git.

**Feature version 2** (`guandan/rl/features.py`, mirrored in `rust/src/features.rs`) appends to
version 1: for every candidate move, the hand left after playing it (card bits plus unary-coded
counts of singles, pairs, triples, bombs, jokers, wilds and the longest runs), and the last 16
moves instead of 8. It was the biggest single gain: within 255k PPO deals the policy went from
+0.50 to +1.36 against the heuristic, where a version 1 run over its first 150k deals stayed flat.

**Training notes.** The batched actors (`guandan/rl/fast.py`) play 32 deals at a time and
evaluate the network once per group, so the learner is the bottleneck, not the actors. Keep one task
queued per actor (`--queue 1`): with three, the data was an update old, the policy-shift measure
(KL) rose to 0.02-0.05 with 13% of samples clipped, and the policy got worse; with one, KL is
about 0.002. The training log's "vs" scores are noisy and sampled; judge checkpoints with
`scripts/evaluate.py` instead. The shipped model has 4M PPO deals (1M at lr 3e-5, then 3M at 1e-4); the
last 2.5M added +0.17 ± 0.07 head-to-head against the 1.5M-deal model, so returns are diminishing.

## Layout

| Path | Contents |
|---|---|
| `guandan/cards.py` | card ids, level-aware values, parsing |
| `guandan/combos.py` | combo kinds, comparison, classification with wilds, legal-move generation |
| `guandan/game.py` | `Deal` (one hand of play) and `Match` (levels, tribute, match end) |
| `guandan/agents.py` | random and heuristic agents |
| `guandan/evaluate.py` | duplicate-deal head-to-head |
| `guandan/review.py` | post-game review: policy agreement and rollout impact of a player's moves |
| `guandan/rl/` | feature encoding (versions 1 and 2); DMC Q-network and trainer; policy/critic networks, imitation and PPO trainer; `fast.py` batched self-play on the Rust core; `search.py` look-ahead search |
| `rust/` | Rust core (`guandan_core`, built with maturin): rules engine, legal moves, feature encoders, batch functions |
| `guandan/server/` | HTTP server, tables/host/seat logic, replay storage, Chinese UI text (`zh.py`), single-page UI |
| `docs/TECHNIQUES.md` | which model-training techniques fit Guandan, and the roadmap |
| `docs/SERVER_SPEC.md` | server spec: requirements, architecture, step-by-step setup, acceptance checks, operations |
| `docs/DEPLOY.md` | private cloud setup (SSH tunnel / Tailscale), capacity and table count |
| `deploy/` | `make_bundle.sh` (offline install bundle: code, models, Linux wheels), `setup_lighthouse.sh` (one-step server setup), `public_access.sh` (HTTPS + shared password via nginx) |

## Roadmap

Done since the first version: the Rust core, batched self-play, feature version 2, and
PIMC search (`ppo+`). Tried without gain: training the policy toward the search player's choices
([docs/TECHNIQUES.md](docs/TECHNIQUES.md#5-test-time-search-pimc-implemented-guandanrlsearchpy)). Next:
weighting sampled hands by what the other players' passes and plays imply, public tribute cards as
inputs, and a learned tribute-return choice.
