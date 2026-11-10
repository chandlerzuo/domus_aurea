# Training techniques for Guandan agents

This note looks at which of the methods from `poker_ai` carry over to Guandan
and which methods have actually produced strong agents for Guandan and its
cousin Dou Dizhu. It ends with the roadmap this repo follows.

## How Guandan differs from No-Limit Hold'em

| | NLHE (poker_ai) | Guandan |
|---|---|---|
| Players | 2-9, everyone for themselves | 4, two fixed partnerships (2 v 2) |
| Hidden information | 2 hole cards per player | 27 cards per player; 81 unknown cards split among 3 players |
| Actions | fold / call / raise sizes (abstracted to ~6) | every legal combination: 100s when leading, varies by state |
| Horizon | ~4-10 decisions per hand | ~60-120 decisions per deal (15-30 per player) |
| Reward | chips, immediately after the hand | levels gained (±1/2/3) at the end of the deal; match won at A |
| Chance | board cards during the hand | only the deal (and tribute) at the start |

Three consequences:

1. **The game is too big for tabular solvers.** Every hand has around
   10^20 possible splits of the unknown cards, and each decision has a big,
   variable action set. Nothing like the 169-class / 32-bucket abstraction in
   `poker_ai/abstraction` keeps enough information to play well.
2. **It is a team game.** Two partners who cannot communicate playing against
   another pair is not a two-player zero-sum game. CFR's convergence guarantees
   don't apply, and the relevant solution concept (TMECor, a team-maxmin
   equilibrium with correlation) is much harder to compute. Partner
   cooperation (yielding, passing the lead to a partner who has gone out,
   choosing whom to block) is a big part of strength.
3. **No betting, long horizon, sparse reward.** There are no bet sizes to
   bluff with. Strength comes from planning how to split the hand into combos
   and from inferring the other hands from the cards already played. Methods
   that assign credit across 20+ of a player's own moves without a
   well-trained value function suffer.

## Do poker_ai's methods transfer?

| poker_ai method | Use for Guandan | Verdict |
|---|---|---|
| Tabular CFR / CFR+ / DCFR (`solvers/cfr.py`) | Only toy variants, e.g. one deck, 3 ranks, 5-card hands, to sanity-check team-game behaviour | Research tool only |
| External-sampling MCCFR with abstraction (`solvers/mccfr.py`, `vector_cfr.py`) | Card abstraction would have to encode a whole hand's structure. Action abstraction at the rank level (suits ignored except for straight flushes) is already what our move generator does, and it is still far too big | Not practical |
| Blueprint + real-time search (Pluribus-style) | Worth adopting as test-time search on top of a learned policy (PIMC, see below) | Yes, as search |
| Deep CFR / DREAM / ESCHER | Neural regret approximation removes the abstraction, but outcome sampling over ~100-step deals with hundreds of actions has very high variance. No strong Guandan results published | Speculative |
| NFSP | Works on large imperfect-information games in principle; DouZero reports DMC beating it clearly on Dou Dizhu | Weak baseline |
| PPO league with snapshots and baselines (`rl/league.py`) | Applies directly. Needs a policy over a *variable* action set: score each legal move with f(s, a) and take a softmax. The opponent mix (current / snapshots / fixed baselines) is reused in `rl/dmc.py` | Yes, as stage 2 |
| Duplicate evaluation (`evaluate_hu.py`) | Same deal played twice with the teams swapped between seat pairs | Implemented (`guandan/evaluate.py`) |

## Methods that work for shedding-type card games

### 1. Deep Monte-Carlo (DMC): implemented

*DouZero* (Zha et al., ICML 2021) for Dou Dizhu, and *DanZero* (Lu et al., 2022)
for Guandan.

- A Q-network scores (state, action) pairs, so the action set can be any size:
  each legal combo is encoded as a card vector plus combo-kind features, and
  the network scores them all in one batch.
- Targets are Monte-Carlo returns: the final result of the deal for the
  acting player's team. There is no bootstrapping, which avoids the
  overestimation problems of Q-learning with huge action sets.
- Exploration is epsilon-greedy with a small epsilon (0.01). Many actor
  processes play with lagged weights and one learner does the regression.

In this repo (`guandan/rl/dmc.py`):

- One network is shared by all four seats.
- Opponents are mixed, borrowing from poker_ai's league: 70% current network
  against itself, 15% heuristic baseline, 15% frozen past snapshots.
- Deals start from random positions in a match (random team levels, whose
  level it is, and a random previous finishing order that triggers tribute),
  so the network sees every level rank and wild-card situation.
- The state includes 8 moves of history as flat bits. DouZero uses an LSTM
  over the history; swapping one in is an easy experiment.

Limits: DMC estimates the value of the *current* behaviour policy, and its
greedy policy is deterministic, which makes it exploitable. In this game
mixing matters less than in poker, though. Variance is high because one
reward has to cover a whole deal.

### 2. PPO fine-tuning: implemented

*DanZero+* (2023) starts from a DMC-trained model and fine-tunes it with
PPO, which gives a stochastic policy and better credit assignment through
a learned value baseline (GAE). poker_ai's `rl/ppo.py` carries over almost
unchanged. The policy head becomes "logits = f(s, a) for each legal a", and
the value head takes the state embedding.

In this repo (`guandan/rl/ppo.py`) PPO starts from the imitation model (§6)
rather than from DMC, and uses the oracle critic (§3) and belief head (§4).
After 1M deals it beats the heuristic by +0.57 levels/deal and DMC by +1.29.

### 3. Perfect-information training, imperfect-information execution (PTIE): implemented

*PerfectDou* (Yang et al., NeurIPS 2022) beat DouZero by giving the **critic**
the other players' cards during training (they are known to the simulator),
while the **actor** sees only legal information. It also used hand-designed
"minimum steps to empty the hand" features. For Guandan:

- the centralized critic sees all four hands, which cuts value variance
  dramatically;
- the policy stays decentralized, so it is still a legal player at test time.

This is the same idea as centralized-training / decentralized-execution
multi-agent RL (MAPPO with a central value function, Yu et al. 2021), which
also suits the 2 v 2 team structure. *Suphx* (Mahjong, Li et al. 2020) used a
related "oracle guiding": train with perfect-information features, then fade
them out with dropout.

### 4. Belief modelling (predicting hidden hands): implemented as an auxiliary loss

Add an auxiliary head that predicts, for each other player, how many copies
of each card type they hold (cross-entropy against the true hands, which the
simulator knows). It shapes the shared representation. The predicted beliefs
can also be fed back as features, and they are exactly what search (below)
needs to sample realistic deals. It is cheap to add to DMC or PPO.

### 5. Test-time search: PIMC implemented (`guandan/rl/search.py`)

Measured here: PIMC adds +0.88 ± 0.09 levels/deal over the previous PPO policy (32 sampled
hands, top 4 moves) and +0.32 to +0.44 (±0.11) over the stronger feature-version-2 policy, at 30-50 ms a
decision. The sampled hands ignore what passes imply about a player's hand, so weighting
them by the policy's likelihood of the observed plays is the obvious next step (it helped in
poker_ai's search).

- **PIMC (perfect-information Monte Carlo)**: sample hands for the other
  three players that are consistent with the play so far (and with the
  belief model, if present), play each candidate move out with the learned
  policy as the rollout policy, and average. It works well in bridge (GIB) and
  Skat despite "strategy fusion" (Long et al., 2010 explain when it works).
  It is the closest thing to poker_ai's blueprint plus real-time search.
- **Endgame solving**: once the hidden cards are few, or mostly inferred,
  exact alpha-beta over determinized deals is cheap and plays near-perfect
  endings.
- **IS-MCTS** (information-set MCTS) with the Q-network as prior and leaf
  evaluator, AlphaZero-style. It is more expensive and fiddly in a
  four-player team game, but it is the principled version of PIMC.

**Training the policy toward the search player's choices (tried, no gain).**
`guandan/rl/distill.py`, `scripts/label_search.py` and `scripts/fit_distill.py` label decisions
with the search (policy shifted toward the better-looking candidates) and fit the policy to the
labels. On the shipped model, 100k labels took 34 minutes on 10 cores. Search overruled the
policy's top move in 9.3% of them. A round of fitting left the policy unchanged
(+0.003 ± 0.062 levels/deal against the original, 1,400 deals). Offline, on 50k labels with 10% held
out: fitting at ordinary step sizes made the training labels easier but the held-out ones slightly
harder (cross-entropy 0.588 → 0.593), i.e. it memorised noise; at very small steps held-out
cross-entropy improved by only 0.001. Search's gain is spread thinly over many decisions
and each label is a noisy estimate, so this needs millions of labels (days of compute here), while
the same compute in PPO gave +0.17 over 2.5M deals. Search at play time (`ppo+`) is the better
use of search. Better-weighted sampling of hidden hands would be a cheaper next step.

### 6. Imitation / warm start: implemented

Supervised pre-training on the heuristic agent (or on human game logs, if any
become available), followed by RL. This speeds up early training; DMC from
scratch loses to the heuristic for the first tens of thousands of deals. The
web app could log human games (with consent) as a source of data.

Measured here: cloning the heuristic on 200k deals reaches 83% move agreement
but plays at −1.26 levels/deal against it, since small mistakes compound
over a deal. It is a starting point for PPO, not a player in its own right.

### 7. Match-level decisions

Currently the reward is the result of a single deal. A match is won by
reaching and winning at A, so the value of +1/+2/+3 depends on the score.
Replace the deal reward with the change in estimated match-win probability,
or condition the policy on the levels (already in the state) with a
match-outcome return. The tribute return card is chosen heuristically; it
could become a learned action too.

## Evaluation

- **Duplicate deals with seat swap** (implemented): the same cards, level and
  leader are played twice with the partnerships swapped. Reports levels per
  deal ± standard error.
- **League table**: round-robin of snapshots and baselines with Elo or
  TrueSkill, as in `poker_ai/scripts/evaluate_league.py`.
- **Variance reduction**: subtract the Q-network's own value estimate at the
  start of the deal (an AIVAT-style control variate) to compare agents with
  fewer deals.
- **Humans**: the web app records wins and losses per user.

## Roadmap

1. ~~Rules engine, heuristic baseline, duplicate evaluation~~ (done)
2. ~~DMC self-play with snapshot/baseline league~~ (done)
3. ~~Imitation warm start, PPO fine-tuning, PTIE critic and belief head~~ (done)
4. Feed the belief head's predictions into the policy, and learn the tribute return
5. PIMC test-time search with the learned policy as rollout policy
6. Speed: port `combos.legal_moves` and the feature encoder to Rust (as in
   poker_ai's `rust/` core). Move generation is about 60% of actor time.

## References

- Zha et al., *DouZero: Mastering DouDizhu with Self-Play Deep Reinforcement Learning*, ICML 2021.
- Lu et al., *DanZero: Mastering GuanDan Game with Reinforcement Learning*, 2022; and the follow-up *DanZero+* (PPO on top of DMC), 2023.
- Yang et al., *PerfectDou: Dominating DouDizhu with Perfect Information Distillation*, NeurIPS 2022.
- Li et al., *Suphx: Mastering Mahjong with Deep Reinforcement Learning*, 2020.
- Brown & Sandholm, *Superhuman AI for multiplayer poker* (Pluribus), Science 2019.
- Brown et al., *Deep Counterfactual Regret Minimization*, ICML 2019; Brown et al., *ReBeL*, NeurIPS 2020.
- Heinrich & Silver, *Deep Reinforcement Learning from Self-Play in Imperfect-Information Games* (NFSP), 2016.
- Yu et al., *The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games* (MAPPO), 2021.
- Celli & Gatti, *Computational Results for Extensive-Form Adversarial Team Games* (TMECor), AAAI 2018.
- Long et al., *Understanding the Success of Perfect Information Monte Carlo Sampling in Game Tree Search*, AAAI 2010.
