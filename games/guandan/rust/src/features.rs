//! Binary feature encoding (port of guandan/rl/features.py): state, per-move action
//! vectors, and the oracle target (the other players' hidden hands).

use crate::combos::{ctype, wild_type, BJ, N_KINDS, N_TYPES, SJ};
use crate::deal::Deal;
use crate::combos::Move;
use crate::plan::{Planner, St};

pub const CARD_DIM: usize = 2 * N_TYPES;
pub const HISTORY: usize = 8;
pub const STATE_DIM: usize = CARD_DIM * 5 + 3 * 28 + CARD_DIM + 4 + N_KINDS + 13 * 3 + 3 + 3 + 1
    + HISTORY * (CARD_DIM + 4);
pub const ACTION_DIM: usize = CARD_DIM + N_KINDS + 3 + 1 + 16;
pub const ORACLE_DIM: usize = 3 * CARD_DIM;

// Version 2 appends columns to version 1 (so a v1 network can be widened with zero weights):
// 8 older history slots on the state, and on each action the hand left after the move
// (card bits) plus summary counts.
pub const HISTORY_V2: usize = 16;
pub const STATE_DIM_V2: usize = STATE_DIM + (HISTORY_V2 - HISTORY) * (CARD_DIM + 4);
pub const AGG: usize = 27 + 6 * 4 + 4 + 2 + 14 * 3;
pub const ACTION_DIM_V2: usize = ACTION_DIM + CARD_DIM + AGG;

// Version 3 appends the hand decomposition (see plan.rs): on the state, the fewest sets the hand splits into; on each
// action, that number after the move (unary) and how the move changes it (<= -1, 0, +1, >= +2).
pub const PLAN_CAP: usize = 14;
pub const STATE_DIM_V3: usize = STATE_DIM_V2 + PLAN_CAP;
pub const ACTION_DIM_V3: usize = ACTION_DIM_V2 + PLAN_CAP + 4;

pub fn state_dim(version: u8) -> usize {
    if version >= 3 { STATE_DIM_V3 } else if version >= 2 { STATE_DIM_V2 } else { STATE_DIM }
}

pub fn action_dim(version: u8) -> usize {
    if version >= 3 { ACTION_DIM_V3 } else if version >= 2 { ACTION_DIM_V2 } else { ACTION_DIM }
}

/// The acting player's hand decomposition, shared by all the moves of one decision.
pub struct PlanCtx {
    planner: Planner,
    st: St,
    now: u8,
    level: u8,
}

impl PlanCtx {
    pub fn new(hand: &[u8], level: u8) -> PlanCtx {
        let st = St::from_cards(hand, level);
        let mut planner = Planner::new();
        let now = planner.min_sets(&st);
        PlanCtx { planner, st, now, level }
    }
}

fn thermometer(out: &mut [u8], v: usize, cap: usize) {
    for k in 0..cap {
        out[k] = (k < v) as u8;
    }
}

/// Two bits per card type: "at least one copy" and "both copies".
#[inline]
fn card_vec(cards: &[u8], out: &mut [u8]) {
    for &c in cards {
        let t = 2 * ctype(c) as usize;
        if out[t] != 0 {
            out[t + 1] = 1;
        } else {
            out[t] = 1;
        }
    }
}

pub fn encode_state(d: &Deal, seat: usize, version: u8, out: &mut [u8]) {
    debug_assert_eq!(out.len(), state_dim(version));
    out.fill(0);
    let rel = [(seat + 1) % 4, (seat + 2) % 4, (seat + 3) % 4];
    let mut o = 0;

    card_vec(&d.hands[seat], &mut out[o..o + CARD_DIM]);
    o += CARD_DIM;
    let mut seen = [0u8; CARD_DIM];
    card_vec(&d.hands[seat], &mut seen);
    for p in &d.played {
        card_vec(p, &mut seen);
    }
    for i in 0..CARD_DIM {
        out[o + i] = 1 - seen[i];
    }
    o += CARD_DIM;
    for &s in &rel {
        card_vec(&d.played[s], &mut out[o..o + CARD_DIM]);
        o += CARD_DIM;
    }
    for &s in &rel {
        out[o + d.hands[s].len().min(27)] = 1;
        o += 28;
    }
    match &d.table {
        Some(t) => card_vec(&t.cards, &mut out[o..o + CARD_DIM]),
        None => {}
    }
    o += CARD_DIM;
    let who = match d.table_seat {
        None => 0,
        Some(ts) => (ts + 4 - seat) % 4,
    };
    out[o + who] = 1;
    o += 4;
    out[o + d.table.as_ref().map_or(0, |t| t.combo.kind as usize)] = 1;
    o += N_KINDS;
    let mine = d.team_levels[seat % 2] as usize;
    let theirs = d.team_levels[1 - seat % 2] as usize;
    out[o + d.level as usize] = 1;
    o += 13;
    out[o + mine] = 1;
    o += 13;
    out[o + theirs] = 1;
    o += 13;
    out[o + match d.level_team { None => 2, Some(lt) => (lt as usize != seat % 2) as usize }] = 1;
    o += 3;
    for &s in &rel {
        if d.finished.contains(&s) {
            out[o] = 1;
        }
        o += 1;
    }
    if d.leading() {
        out[o] = 1;
    }
    o += 1;
    let n = d.history.len();
    for k in 0..HISTORY {
        if k < n {
            let (s, m) = &d.history[n - 1 - k];
            card_vec(&m.cards, &mut out[o..o + CARD_DIM]);
            out[o + CARD_DIM + (s + 4 - seat) % 4] = 1;
        }
        o += CARD_DIM + 4;
    }
    debug_assert_eq!(o, STATE_DIM);
    if version >= 2 {
        for k in HISTORY..HISTORY_V2 {
            if k < n {
                let (s, m) = &d.history[n - 1 - k];
                card_vec(&m.cards, &mut out[o..o + CARD_DIM]);
                out[o + CARD_DIM + (s + 4 - seat) % 4] = 1;
            }
            o += CARD_DIM + 4;
        }
    }
    if version >= 3 {
        let sets = Planner::new().min_sets(&St::from_cards(&d.hands[seat], d.level)) as usize;
        thermometer(&mut out[STATE_DIM_V2..STATE_DIM_V3], sets, PLAN_CAP);
    }
}

pub fn encode_action(m: &Move, hand: &[u8], level: u8, version: u8, out: &mut [u8], plan: Option<&mut PlanCtx>) {
    debug_assert_eq!(out.len(), action_dim(version));
    out.fill(0);
    let hand_size = hand.len();
    card_vec(&m.cards, &mut out[..CARD_DIM]);
    let mut o = CARD_DIM;
    out[o + m.combo.kind as usize] = 1;
    o += N_KINDS;
    let wt = crate::combos::wild_type(level);
    let wilds = m.cards.iter().filter(|&&c| ctype(c) == wt).count().min(2);
    out[o + wilds] = 1;
    o += 3;
    out[o] = (m.cards.len() == hand_size) as u8;
    o += 1;
    out[o + (m.combo.value.max(0) as usize).min(15)] = 1;
    if version >= 2 {
        encode_remaining(m, hand, level, &mut out[ACTION_DIM..]);
    }
    if version >= 3 {
        let ctx = plan.expect("version 3 needs a PlanCtx");
        let after = ctx.planner.min_sets(&ctx.st.minus(&m.cards, ctx.level)) as i32;
        let at = ACTION_DIM_V2;
        thermometer(&mut out[at..at + PLAN_CAP], after as usize, PLAN_CAP);
        let class = match after - ctx.now as i32 { i32::MIN..=-1 => 0, 0 => 1, 1 => 2, _ => 3 };
        out[at + PLAN_CAP + class] = 1;
    }
}

/// The hand left after `m`: card bits, then AGG thermometer-coded summary counts.
fn encode_remaining(m: &Move, hand: &[u8], level: u8, out: &mut [u8]) {
    let mut rem: Vec<u8> = hand.to_vec();
    for &c in &m.cards {
        if let Some(i) = rem.iter().position(|&x| x == c) {
            rem.remove(i);
        }
    }
    card_vec(&rem, &mut out[..CARD_DIM]);
    let wt = wild_type(level);
    let (mut nr, mut sj, mut bj, mut wild) = ([0usize; 13], 0usize, 0usize, 0usize);
    for &c in &rem {
        let t = ctype(c);
        if t == wt { wild += 1 } else if t == SJ { sj += 1 } else if t == BJ { bj += 1 } else { nr[(t % 13) as usize] += 1 }
    }
    let groups = |lo: usize, hi: usize| nr.iter().filter(|&&x| x >= lo && x <= hi).count();
    // Longest run of consecutive ranks (ace both low and high) with at least `m` natural copies.
    const SEQ: [usize; 14] = [12, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    let run = |m: usize| -> usize {
        let (mut best, mut cur) = (0, 0);
        for &r in &SEQ {
            cur = if nr[r] >= m { cur + 1 } else { 0 };
            best = best.max(cur);
        }
        best
    };
    // Every count is a unary ("thermometer") code, so all inputs stay 0/1.
    let mut at = CARD_DIM;
    let mut put = |v: usize, cap: usize| {
        for k in 0..cap {
            out[at + k] = (k < v) as u8;
        }
        at += cap;
    };
    put(rem.len(), 27);
    put(groups(1, 1), 6);
    put(groups(2, 2), 6);
    put(groups(3, 3), 6);
    put(groups(4, 99), 6);
    put(sj + bj, 4);
    put(wild, 2);
    put(run(1), 14);
    put(run(2), 14);
    put(run(3), 14);
    debug_assert_eq!(at, CARD_DIM + AGG);
}

pub fn encode_oracle(d: &Deal, seat: usize, out: &mut [u8]) {
    out.fill(0);
    for k in 0..3 {
        card_vec(&d.hands[(seat + 1 + k) % 4], &mut out[k * CARD_DIM..(k + 1) * CARD_DIM]);
    }
}
